from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(slots=True)
class EventInput:
    event_id: str
    source: str
    occurred_at: datetime
    text: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class CandidateCluster:
    cluster_id: str
    status: str
    first_seen_at: datetime
    last_seen_at: datetime
    member_count: int
    centroid_embedding: list[float] | None
    projection_centroid_embedding: list[float]
    exemplar_event_ids: list[str]
    keywords: list[str]
    summary_text: str
    candidate_parent_cluster_id: str | None
    candidate_parent_score: float | None

    def embedding_for(self, vector_mode: str) -> list[float]:
        if vector_mode == "stable_projection" or self.centroid_embedding is None:
            return self.projection_centroid_embedding
        return self.centroid_embedding


@dataclass(slots=True)
class ScoredCandidate:
    candidate: CandidateCluster
    semantic_score: float
    time_weight: float
    final_score: float


@dataclass(slots=True)
class RerankedCandidate:
    candidate: CandidateCluster
    gate1_score: float
    gate2_score: float


@dataclass(slots=True)
class JudgeDecision:
    decision: str
    confidence: float
    reason: str
    chosen_cluster_id: str | None = None


@dataclass(slots=True)
class AssignmentResult:
    cluster_id: str
    decision: str
    cluster_status: str
    confidence: float
    semantic_score: float | None
    time_weight: float | None
    final_score: float | None
    gate1_score: float | None = None
    gate2_score: float | None = None
    judge_confidence: float | None = None
    judge_decision: str | None = None
    candidate_parent_cluster_id: str | None = None
    candidate_parent_score: float | None = None


@dataclass(slots=True)
class MergeDecision:
    should_merge: bool
    evidence_score: float
    evidence_summary: dict[str, Any]


@dataclass(slots=True)
class CalibrationRecommendation:
    join_threshold: float
    draft_score_min: float
    draft_score_max: float
    merge_evidence_threshold: float
    pairwise_precision: float
    pairwise_recall: float
    pairwise_f1: float
