from __future__ import annotations

import unittest

from demo.dashboard.live_dashboard import LiveDashboard


class LiveDashboardTest(unittest.TestCase):
    def test_assignment_events_build_active_cluster_state(self) -> None:
        dashboard = LiveDashboard()
        dashboard.apply_event(
            "assignment",
            {
                "event_id": "evt-1",
                "cluster_id": "cluster-a",
                "cluster_status": "draft",
                "confidence": 0.66,
                "decision": "created_new_cluster",
            },
        )
        dashboard.apply_event(
            "assignment",
            {
                "event_id": "evt-2",
                "cluster_id": "cluster-a",
                "cluster_status": "draft",
                "confidence": 0.78,
                "decision": "joined_existing_cluster",
            },
        )

        self.assertEqual(dashboard.active_clusters["cluster-a"]["event_count"], 2)
        self.assertEqual(dashboard.event_to_cluster["evt-2"], "cluster-a")

    def test_merge_reassigns_cluster_counts(self) -> None:
        dashboard = LiveDashboard()
        dashboard.apply_event(
            "assignment",
            {
                "event_id": "evt-1",
                "cluster_id": "cluster-a",
                "cluster_status": "draft",
                "confidence": 0.61,
                "decision": "created_new_cluster",
            },
        )
        dashboard.apply_event(
            "assignment",
            {
                "event_id": "evt-2",
                "cluster_id": "cluster-b",
                "cluster_status": "draft",
                "confidence": 0.63,
                "decision": "created_new_cluster",
            },
        )

        dashboard.apply_event(
            "merge",
            {
                "winner_cluster_id": "cluster-a",
                "loser_cluster_id": "cluster-b",
                "evidence_score": 0.88,
            },
        )

        self.assertEqual(dashboard.active_clusters["cluster-a"]["event_count"], 2)
        self.assertNotIn("cluster-b", dashboard.active_clusters)
        self.assertEqual(dashboard.event_to_cluster["evt-2"], "cluster-a")

    def test_reset_started_clears_active_state(self) -> None:
        dashboard = LiveDashboard()
        dashboard.apply_event(
            "assignment",
            {
                "event_id": "evt-1",
                "cluster_id": "cluster-a",
                "cluster_status": "draft",
                "confidence": 0.66,
                "decision": "created_new_cluster",
            },
        )

        dashboard.apply_event(
            "reset",
            {
                "phase": "started",
                "deleted_events": 1,
                "deleted_clusters": 1,
                "rehydrate_runtime": True,
            },
        )

        self.assertEqual(dashboard.active_clusters, {})
        self.assertEqual(dashboard.event_to_cluster, {})
