from __future__ import annotations

import unittest
from dataclasses import replace
from datetime import datetime, timedelta, timezone

from demo.config import load_config
from demo.domain.models import CandidateCluster
from demo.domain.scoring import is_draft_band, merge_decision, score_candidate, should_join, time_weight


class ScoringTest(unittest.TestCase):
    def setUp(self) -> None:
        self.config = load_config("config/demo.yaml")
        self.now = datetime(2026, 4, 25, 10, 0, tzinfo=timezone.utc)
        self.cluster = CandidateCluster(
            cluster_id="cluster-1",
            status="draft",
            first_seen_at=self.now - timedelta(minutes=10),
            last_seen_at=self.now - timedelta(minutes=15),
            member_count=2,
            centroid_embedding=[1.0, 0.0, 0.0, 0.0],
            projection_centroid_embedding=[0.8, 0.2, 0.0, 0.0],
            exemplar_event_ids=["evt-1"],
            keywords=["login", "auth"],
            summary_text="auth login failures in the sign-in service",
            candidate_parent_cluster_id=None,
            candidate_parent_score=None,
        )

    def test_time_weight_halves_after_half_life(self) -> None:
        self.assertAlmostEqual(time_weight(60, 60), 0.5, places=3)

    def test_join_threshold_allows_strong_recent_match(self) -> None:
        scored = score_candidate(
            event_embedding=[1.0, 0.0, 0.0, 0.0],
            candidate=self.cluster,
            now=self.now,
            config=self.config,
        )
        self.assertTrue(should_join(scored, self.config))

    def test_draft_band_detects_uncertain_match(self) -> None:
        weak_cluster = replace(self.cluster, centroid_embedding=[0.77, 0.64, 0.0, 0.0])
        scored = score_candidate(
            event_embedding=[1.0, 0.0, 0.0, 0.0],
            candidate=weak_cluster,
            now=self.now,
            config=self.config,
        )
        self.assertTrue(is_draft_band(scored.final_score, self.config))

    def test_merge_requires_stronger_correlated_evidence(self) -> None:
        decision = merge_decision(
            cluster_similarity=0.87,
            strongest_rejected_score=0.66,
            corroborating_links=1,
            shared_keyword_overlap=2,
            config=self.config,
        )
        self.assertTrue(decision.should_merge)

        rejected = merge_decision(
            cluster_similarity=0.69,
            strongest_rejected_score=0.66,
            corroborating_links=0,
            shared_keyword_overlap=1,
            config=self.config,
        )
        self.assertFalse(rejected.should_merge)

    def test_exemplar_similarity_can_outscore_centroid(self) -> None:
        centroid_miss = replace(self.cluster, centroid_embedding=[0.20, 0.98, 0.0, 0.0])
        scored = score_candidate(
            event_embedding=[1.0, 0.0, 0.0, 0.0],
            candidate=centroid_miss,
            now=self.now,
            config=self.config,
            exemplar_embeddings=[[1.0, 0.0, 0.0, 0.0]],
        )
        self.assertGreater(scored.semantic_score, 0.9)

    def test_stable_projection_mode_uses_projection_centroid(self) -> None:
        semantic_miss = replace(
            self.cluster,
            centroid_embedding=[0.0, 1.0, 0.0, 0.0],
            projection_centroid_embedding=[1.0, 0.0, 0.0, 0.0],
        )
        scored = score_candidate(
            event_embedding=[1.0, 0.0, 0.0, 0.0],
            candidate=semantic_miss,
            now=self.now,
            config=self.config,
            vector_mode="stable_projection",
        )
        self.assertGreater(scored.semantic_score, 0.9)
