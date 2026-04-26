import argparse
import sys
import os
import json
import logging
from datetime import datetime
import numpy as np

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# Ensure src is in path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), 'src'))

from demo.config import load_config
from demo.domain.text_utils import load_story_events
from demo.embeddings.model_cache import load_model
from demo.intelligence import load_reranker, load_judge
from demo.domain.models import CandidateCluster
from evaluate import evaluate_clustering

def run_hybrid_evaluation(data_json_path: str):
    config = load_config()
    from demo.services.reset_service import ResetService
    reset_service = ResetService(config)
    reset_service.reset_to_baseline(rehydrate_runtime=False)
    
    story_events = load_story_events(data_json_path)
    
    # Extract true labels
    true_labels = [event.metadata.get("expected_cluster", "unknown") for event in story_events]

    # Load Components
    logging.info("Loading Embedder, Reranker, and Judge...")
    embedder = load_model(config)
    reranker = load_reranker(config)
    judge = load_judge(config)
    
    # Generate Embeddings
    embeddings = []
    for evt in story_events:
        embs = embedder.embed(evt.text)
        vec = embs.semantic_embedding if embs.semantic_embedding else embs.projection_embedding
        embeddings.append(vec)
        
    X = np.array(embeddings)
    norms = np.linalg.norm(X, axis=1, keepdims=True)
    X = np.where(norms > 0, X / norms, X)
    
    # Initial HDBSCAN pass
    from sklearn.cluster import HDBSCAN
    logging.info("Running HDBSCAN...")
    hdbscan = HDBSCAN(min_cluster_size=2, min_samples=1, metric='euclidean')
    initial_labels = hdbscan.fit_predict(X)
    
    clusters = {}
    noise_idx = 0
    for i, (evt, label) in enumerate(zip(story_events, initial_labels)):
        if label == -1:
            cid = f"noise_{noise_idx}"
            noise_idx += 1
            clusters[cid] = {'events': [evt], 'text': evt.text}
        else:
            cid = f"cluster_{label}"
            if cid not in clusters:
                clusters[cid] = {'events': [], 'text': evt.text}
            clusters[cid]['events'].append(evt)
            
    # Initial Summarization
    for cid, cdata in clusters.items():
        if len(cdata['events']) > 1:
            concat_text = " ".join([e.text for e in cdata['events']])[:400]
            cdata['text'] = judge.generate_summary(event_text=concat_text, metadata={})
            
    logging.info(f"Formed {len(clusters)} initial clusters.")
    
    # Iterative Top-1 Conservative Merging
    changed = True
    iterations = 0
    while changed and iterations < 5:
        changed = False
        iterations += 1
        logging.info(f"--- Strict Merge Iteration {iterations} ---")
        
        cluster_ids = list(clusters.keys())
        for nid in cluster_ids:
            if changed: break
            if nid not in clusters: continue
            ndata = clusters[nid]
            
            candidates = [
                CandidateCluster(
                    cluster_id=cid, status="active", first_seen_at=datetime.now(), last_seen_at=datetime.now(),
                    member_count=len(cdata['events']), centroid_embedding=None, projection_centroid_embedding=[],
                    exemplar_event_ids=[], keywords=[], summary_text=cdata['text'],
                    candidate_parent_cluster_id=None, candidate_parent_score=None
                ) for cid, cdata in clusters.items() if cid != nid
            ]
                
            if not candidates: continue
            
            # Use Reranker only to identify the most likely candidate
            gate1_scores = {c.cluster_id: 1.0 for c in candidates}
            ranked = reranker.rerank(event_text=ndata['text'], candidates=candidates, gate1_scores=gate1_scores)
            
            if ranked:
                best_cand = ranked[0]
                cid = best_cand.candidate.cluster_id
                cdata = clusters[cid]
                
                # Conservative LLM Judge Prompt
                prompt = f"""You are an SRE Lead performing incident deduplication. Your goal is to determine if two clusters represent the same operational incident.

### MERGE Criteria (Must meet at least one):
- **Identical Root Cause**: Both summaries describe the exact same error (e.g., "Gateway 502" or "DB Timeout") in the same service.
- **Symptom Progression**: One describes a symptom (e.g., "Login errors") and the other describes the resulting user impact (e.g., "Users cannot sign in").
- **Systemic Failure**: Both describe a total service outage (e.g., "Auth service is down") rather than specific feature bugs.

### SEPARATE Criteria (Priority over Merge):
- **Distinct Functional Flows**: Even if the service is the same, separate "Login" from "Password Reset" or "Checkout" from "Card Validation" unless a systemic error code (like 502/504) links them.
- **Different Error Signatures**: Separate a "UI palette/style issue" from a "Data timeout" even if they occur in the same dashboard.
- **Feature-Specific Logic**: Treat different API endpoints as separate incidents unless they share a documented infrastructure failure.

Cluster 1: {ndata['text']}
Cluster 2: {cdata['text']}

Return ONLY JSON with keys: 
"decision" ("merge" or "separate"), 
"confidence" (0.0 to 1.0), 
"reason" (A technical justification focusing on flow vs. systemic error)."""

                payload = judge._generate_json(prompt) if hasattr(judge, "_generate_json") else {"decision": "separate", "confidence": 1.0}

                if payload:
                    decision = str(payload.get("decision") or "").strip().lower()
                    confidence = float(payload.get("confidence") or 0.0)
                    
                    # Logic: Rerank score is ignored; only Judge decision and high confidence matter
                    logging.info(f"Top-1 Match: {nid} -> {cid} | LLM Decision: {decision} ({confidence:.2f})")
                    
                    if decision == "merge" and confidence >= 0.7:
                        logging.info(f"*** Verified Merge: {nid} into {cid} ***")
                        cdata['events'].extend(ndata['events'])
                        
                        # Refresh summary for the expanded cluster
                        concat_text = " ".join([e.text for e in cdata['events']])[:400]
                        cdata['text'] = judge.generate_summary(event_text=concat_text, metadata={})
                        
                        del clusters[nid]
                        changed = True
                        break

    # Build pred_labels for evaluation
    pred_labels = [None] * len(story_events)
    event_id_to_idx = {e.event_id: i for i, e in enumerate(story_events)}
    for cid, cdata in clusters.items():
        for evt in cdata['events']:
            pred_labels[event_id_to_idx[evt.event_id]] = cid
            
    p, r, f1 = evaluate_clustering(true_labels, pred_labels)
    
    # Display Results
    from rich.console import Console
    from rich.table import Table
    console = Console()
    table = Table(title="Strict Top-1 Hybrid Evaluation Results")
    table.add_column("Approach", style="cyan")
    table.add_column("Precision", justify="right", style="magenta")
    table.add_column("Recall", justify="right", style="green")
    table.add_column("F1 Score", justify="right", style="yellow")
    table.add_row("Strict HDBSCAN+LLM", f"{p:.4f}", f"{r:.4f}", f"{f1:.4f}")
    console.print(table)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("data_json", type=str)
    args = parser.parse_args()
    run_hybrid_evaluation(args.data_json)