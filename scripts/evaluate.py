import argparse
import sys
import os
import json
import logging
from rich.console import Console
from rich.table import Table

# configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# ensure src is in path so demo module can be loaded
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), 'src'))

from demo.config import load_config
from demo.services.reset_service import ResetService
from demo.repositories.event_repository import EventRepository
from demo.repositories.database import connect_db
from demo.domain.text_utils import load_story_events

console = Console()

def evaluate_clustering(true_labels_list, pred_labels_list):
    TP = 0
    FP = 0
    FN = 0
    
    n = len(true_labels_list)
    for i in range(n):
        for j in range(i + 1, n):
            same_true = (true_labels_list[i] == true_labels_list[j])
            same_pred = (pred_labels_list[i] == pred_labels_list[j])
            
            if same_true and same_pred:
                TP += 1
            elif not same_true and same_pred:
                FP += 1
            elif same_true and not same_pred:
                FN += 1
                
    precision = TP / (TP + FP) if (TP + FP) > 0 else 0.0
    recall = TP / (TP + FN) if (TP + FN) > 0 else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
    
    return precision, recall, f1

def run_evaluation(data_json_path: str):
    config = load_config()
    story_events = load_story_events(data_json_path)
    
    # Shift timestamps so that they are recent
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    if story_events:
        time_diff = now - story_events[-1].occurred_at
        for e in story_events:
            e.occurred_at = e.occurred_at + time_diff
    
    # We will assume metadata contains expected_cluster
    true_labels = []
    
    for event in story_events:
        metadata = event.metadata or {}
        true_labels.append(metadata.get("expected_cluster", "unknown"))

    # Results dictionary
    results = {}
    
    approaches = [1, 2, 3]
    approach_names = {
        1: "Score Partition",
        2: "Three Gates",
        3: "HDBSCAN"
    }
    
    reset_svc = ResetService(config)
    
    for approach in approaches:
        console.print(f"Running approach {approach} ({approach_names[approach]})...")
        reset_svc.reset_with_story(story_events, rehydrate_runtime=True, persist_baseline=False, approach=approach)
        
        if approach == 1:
            from demo.workers.maintenance import MaintenanceWorker
            console.print("Running maintenance worker for approach 1...")
            MaintenanceWorker(config).run_once()
        
        # Now fetch from DB
        pred_labels = []
        with connect_db() as conn:
            repo = EventRepository(conn)
            for event in story_events:
                db_event = repo.get_event_by_id(event.event_id)
                cluster_id = db_event.get("cluster_id") if db_event else None
                pred_labels.append(cluster_id)
                
        p, r, f1 = evaluate_clustering(true_labels, pred_labels)
        results[approach] = {"Precision": p, "Recall": r, "F1": f1}
        
    table = Table(title="Clustering Evaluation Results")
    table.add_column("Approach", justify="left", style="cyan")
    table.add_column("Precision", justify="right", style="magenta")
    table.add_column("Recall", justify="right", style="green")
    table.add_column("F1 Score", justify="right", style="yellow")
    
    for approach in approaches:
        res = results[approach]
        table.add_row(
            f"{approach} - {approach_names[approach]}",
            f"{res['Precision']:.4f}",
            f"{res['Recall']:.4f}",
            f"{res['F1']:.4f}"
        )
        
    console.print(table)
    
    reports_dir = os.path.join(os.path.dirname(__file__), 'reports')
    os.makedirs(reports_dir, exist_ok=True)
    out_path = os.path.join(reports_dir, 'evaluation_results.json')
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2)
    console.print(f"Saved results to {out_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Evaluate clustering approaches.")
    parser.add_argument("data_json", type=str, help="Path to the data json(l) file")
    args = parser.parse_args()
    
    run_evaluation(args.data_json)
