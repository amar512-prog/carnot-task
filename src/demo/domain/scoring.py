from __future__ import annotations

import math
from datetime import datetime

from demo.config import DemoConfig
from demo.domain.models import CandidateCluster, MergeDecision, ScoredCandidate


def cosine_similarity(left: list[float], right: list[float]) -> float:
    if not left or not right or len(left) != len(right):
        return 0.0
    return sum(a * b for a, b in zip(left, right))


def time_weight(age_minutes: float, half_life_minutes: int) -> float:
    return math.exp(-math.log(2) * age_minutes / max(1, half_life_minutes))


def age_minutes(now: datetime, then: datetime) -> float:
    return max(0.0, (now - then).total_seconds() / 60.0)


def score_candidate(
    *,
    event_embedding: list[float],
    candidate: CandidateCluster,
    now: datetime,
    config: DemoConfig,
    vector_mode: str = "semantic",
    exemplar_embeddings: list[list[float]] | None = None,
) -> ScoredCandidate:
    exemplar_scores = [cosine_similarity(event_embedding, exemplar) for exemplar in (exemplar_embeddings or [])]
    semantic = max([cosine_similarity(event_embedding, candidate.embedding_for(vector_mode))] + exemplar_scores, default=0.0)
    age = age_minutes(now, candidate.last_seen_at)
    weight = time_weight(age, config.time_decay_half_life_minutes)
    final = semantic * weight
    return ScoredCandidate(candidate=candidate, semantic_score=semantic, time_weight=weight, final_score=final)


def should_join(scored: ScoredCandidate, config: DemoConfig) -> bool:
    return scored.semantic_score >= config.semantic_floor and scored.final_score >= config.join_threshold


def is_draft_band(score: float, config: DemoConfig) -> bool:
    return config.draft_score_min <= score < config.draft_score_max


def merge_decision(
    *,
    cluster_similarity: float,
    strongest_rejected_score: float | None,
    corroborating_links: int,
    shared_keyword_overlap: int,
    config: DemoConfig,
) -> MergeDecision:
    stronger_than_rejected = strongest_rejected_score is None or cluster_similarity > strongest_rejected_score
    corroborated = corroborating_links > 0 or shared_keyword_overlap >= 2
    should = (
        cluster_similarity >= config.merge_evidence_threshold
        and stronger_than_rejected
        and corroborated
    )
    return MergeDecision(
        should_merge=should,
        evidence_score=cluster_similarity,
        evidence_summary={
            "strongest_rejected_score": strongest_rejected_score,
            "corroborating_links": corroborating_links,
            "shared_keyword_overlap": shared_keyword_overlap,
        },
    )
