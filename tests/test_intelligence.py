from __future__ import annotations

import tempfile
import unittest
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path

from demo.config import load_config
from demo.domain.models import CandidateCluster, RerankedCandidate
from demo.intelligence.judge import HeuristicClusterJudge
from demo.intelligence.reranker import FallbackReranker
from demo.embeddings.model_cache import StableProjectionEmbeddingModel


class IntelligenceTest(unittest.TestCase):
    def setUp(self) -> None:
        self.base_config = load_config("config/demo.yaml")
        self.now = datetime(2026, 4, 25, 10, 0, tzinfo=timezone.utc)

    def _candidate(self, cluster_id: str, summary_text: str) -> CandidateCluster:
        return CandidateCluster(
            cluster_id=cluster_id,
            status="draft",
            first_seen_at=self.now,
            last_seen_at=self.now,
            member_count=1,
            centroid_embedding=None,
            projection_centroid_embedding=[1.0, 0.0, 0.0, 0.0],
            exemplar_event_ids=[],
            keywords=summary_text.split()[:3],
            summary_text=summary_text,
            candidate_parent_cluster_id=None,
            candidate_parent_score=None,
        )

    def test_fallback_reranker_prefers_matching_summary(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            backend = StableProjectionEmbeddingModel(
                model_id="stable-projection-reranker-v1",
                dimension=self.base_config.embedding_dimension,
                cache_dir=Path(tmp_dir),
            )
            reranker = FallbackReranker(model_id="stable-projection-reranker-v1", projection_backend=backend)
            candidates = [
                self._candidate("cluster-a", "auth login failure incident in the sign-in flow"),
                self._candidate("cluster-b", "invoice export problem for finance downloads"),
            ]
            ranked = reranker.rerank(
                event_text="authentication failures are spiking for sign in again",
                candidates=candidates,
                gate1_scores={"cluster-a": 0.61, "cluster-b": 0.58},
            )
        self.assertEqual(ranked[0].candidate.cluster_id, "cluster-a")
        self.assertGreater(ranked[0].gate2_score, ranked[1].gate2_score)

    def test_heuristic_judge_can_request_merge(self) -> None:
        judge = HeuristicClusterJudge(config=self.base_config)
        candidates = [
            RerankedCandidate(candidate=self._candidate("cluster-a", "auth login incident"), gate1_score=0.70, gate2_score=0.85),
            RerankedCandidate(candidate=self._candidate("cluster-b", "authentication outage"), gate1_score=0.69, gate2_score=0.83),
        ]
        decision = judge.decide(event_text="users cannot log in to the auth system", candidates=candidates)
        self.assertEqual(decision.decision, "both")

    def test_heuristic_summary_uses_expected_cluster_theme(self) -> None:
        judge = HeuristicClusterJudge(config=self.base_config)
        summary = judge.generate_summary(
            event_text="Authentication failures are rising in us-east-1 for contoso accounts",
            metadata={"expected_cluster": "auth-login-incident-001", "theme": "auth-login"},
        )
        self.assertIn("auth-login-incident-001", summary)
        self.assertIn("Authentication failures are rising", summary)
