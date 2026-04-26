from __future__ import annotations

from demo.config import DemoConfig
from demo.domain.models import RerankedCandidate
from demo.intelligence.judge import ClusterJudge, JudgeDecision
from demo.intelligence.reranker import CandidateReranker
from demo.repositories.cluster_repository import ClusterRepository
from demo.domain.scoring import cosine_similarity

import logging

def evaluate_gates(
    *,
    config: DemoConfig,
    cluster_repo: ClusterRepository,
    reranker: CandidateReranker,
    judge: ClusterJudge,
    event_id: int,
    event_text: str,
    event_occurred_at,
    gate1_embedding,
    gate1_vector_mode: str,
) -> tuple[list[RerankedCandidate], JudgeDecision]:
    """
    Gate 1 (Semantic): Uses vector embeddings to narrow down events to the Top-X candidates.
    Gate 2 (Rerank): Uses the cross-encoder to slice candidates to Top-Y.
    Gate 3 (LLM Judge): Asks the LLM to decide on the top reranked clusters.
    """
    
    # Gate 1: Semantic
    candidates = cluster_repo.find_recent_candidates(
        embedding=gate1_embedding,
        vector_mode=gate1_vector_mode,
        max_reuse_age_minutes=config.max_reuse_age_minutes,
        limit=config.candidate_limit,
        reference_time=event_occurred_at,
    )
    gate1_scores = {
        candidate.cluster_id: cosine_similarity(gate1_embedding, candidate.embedding_for(gate1_vector_mode))
        for candidate in candidates
    }

    # Gate 2: Rerank
    logging.info(f"starting rerank for input event id {event_id}, input text: {event_text[:50]}...")
    reranked = reranker.rerank(
        event_text=event_text,
        candidates=candidates,
        gate1_scores=gate1_scores,
    )[: config.reranker_top_k]
    logging.info(f"completed rerank for input event id {event_id}, result: {[(r.candidate.cluster_id, r.gate2_score) for r in reranked]}")

    with open("/app/reports/reranker_log.txt", "a") as f:
        f.write(f"--- RERANKER INPUT ---\nEvent: {event_text}\nCandidates: {[c.cluster_id for c in candidates]}\n")
        f.write(f"--- RERANKER OUTPUT ---\n{[(r.candidate.cluster_id, r.gate2_score) for r in reranked]}\n")

    # Gate 3: LLM Judge
    logging.info(f"llm output - starting")
    judge_decision = judge.decide(event_text=event_text, candidates=reranked)
    logging.info(f"llm output - completed, decision: {judge_decision.decision}, confidence: {judge_decision.confidence}")

    with open("/app/reports/judge_log.txt", "a") as f:
        f.write(f"--- JUDGE INPUT ---\nEvent: {event_text}\nCandidates: {[r.candidate.cluster_id for r in reranked]}\n")
        f.write(f"--- JUDGE OUTPUT ---\nDecision: {judge_decision.decision}, Confidence: {judge_decision.confidence}, Reason: {judge_decision.reason}\n")

    return reranked, judge_decision
