from __future__ import annotations

import time

from demo.config import load_config
from demo.domain.scoring import cosine_similarity, merge_decision
from demo.embeddings.model_cache import load_model
from demo.repositories.cluster_repository import ClusterRepository
from demo.repositories.database import connect_db, wait_for_db
from demo.repositories.event_repository import EventRepository
from demo.repositories.runtime_state_repository import RuntimeStateRepository
from datetime import datetime, timedelta, timezone


class MaintenanceWorker:
    def __init__(self, config):
        self.config = config
        self.model = load_model(config)
        self.vector_mode = self.model.resolve_vector_mode(config.vector_mode)

    def run_once(self) -> dict[str, int]:
        self._refresh_model()
        scanned = 0
        merged = 0
        skipped = 0
        backfilled_events = 0
        backfilled_clusters = 0
        missing_active_event_semantics = 0
        missing_active_cluster_semantics = 0
        semantic_ready = False
        with connect_db() as conn:
            runtime_state = RuntimeStateRepository(conn)
            if runtime_state.get_bool_flag("replay_in_progress", False):
                return {
                    "scanned": 0,
                    "merged": 0,
                    "skipped": 0,
                    "backfilled_events": 0,
                    "backfilled_clusters": 0,
                    "missing_active_event_semantics": 0,
                    "missing_active_cluster_semantics": 0,
                    "semantic_ready_for_active_window": 0,
                    "skipped_for_replay": 1,
                }
            runtime_state.acquire_replay_maintenance_lock()
            if runtime_state.get_bool_flag("replay_in_progress", False):
                return {
                    "scanned": 0,
                    "merged": 0,
                    "skipped": 0,
                    "backfilled_events": 0,
                    "backfilled_clusters": 0,
                    "missing_active_event_semantics": 0,
                    "missing_active_cluster_semantics": 0,
                    "semantic_ready_for_active_window": 0,
                    "skipped_for_replay": 1,
                }
            event_repo = EventRepository(conn)
            cluster_repo = ClusterRepository(conn)
            if self.model.semantic_available:
                backfilled_events = self._backfill_missing_event_semantics(event_repo)
                backfilled_clusters = self._backfill_missing_cluster_semantics(event_repo, cluster_repo)
            active_cutoff = datetime.now(timezone.utc) - timedelta(minutes=self.config.max_reuse_age_minutes)
            if self.model.semantic_available and self.config.vector_mode != "stable_projection":
                missing_active_event_semantics = event_repo.count_events_missing_semantic_embeddings_since(active_cutoff)
                missing_active_cluster_semantics = cluster_repo.count_clusters_missing_semantic_embeddings_since(active_cutoff)
                semantic_ready = (
                    missing_active_event_semantics == 0
                    and missing_active_cluster_semantics == 0
                )
            runtime_state.set_bool_flag("semantic_ready_for_active_window", semantic_ready)
            active_vector_mode = (
                "semantic"
                if self.model.semantic_available
                and semantic_ready
                and self.config.vector_mode != "stable_projection"
                else "stable_projection"
            )
            drafts = cluster_repo.list_recent_draft_clusters(self.config.draft_merge_window_minutes)
            scanned = len(drafts)
            event_embeddings = event_repo.fetch_event_embeddings(
                [event_id for draft in drafts for event_id in draft.exemplar_event_ids],
                vector_mode=active_vector_mode,
            )

            merged_any = True
            while merged_any:
                merged_any = False
                drafts = cluster_repo.list_recent_draft_clusters(self.config.draft_merge_window_minutes)
                for idx, left in enumerate(drafts):
                    for right in drafts[idx + 1 :]:
                        link_count = int(left.candidate_parent_cluster_id == right.cluster_id) + int(
                            right.candidate_parent_cluster_id == left.cluster_id
                        )
                        keyword_overlap = len(set(left.keywords) & set(right.keywords))
                        strongest_rejected = max(
                            [score for score in [left.candidate_parent_score, right.candidate_parent_score] if score is not None],
                            default=None,
                        )
                        exemplar_scores = []
                        for left_id in left.exemplar_event_ids:
                            for right_id in right.exemplar_event_ids:
                                left_embedding = event_embeddings.get(left_id)
                                right_embedding = event_embeddings.get(right_id)
                                if left_embedding and right_embedding:
                                    exemplar_scores.append(cosine_similarity(left_embedding, right_embedding))
                        cluster_similarity = max(
                            [cosine_similarity(left.embedding_for(active_vector_mode), right.embedding_for(active_vector_mode))] + exemplar_scores,
                            default=0.0,
                        )
                        decision = merge_decision(
                            cluster_similarity=cluster_similarity,
                            strongest_rejected_score=strongest_rejected,
                            corroborating_links=link_count,
                            shared_keyword_overlap=keyword_overlap,
                            config=self.config,
                        )
                        if decision.should_merge:
                            winner = left if left.member_count >= right.member_count else right
                            loser = right if winner.cluster_id == left.cluster_id else left
                            updated = cluster_repo.merge_clusters(winner=winner, loser=loser, decision=decision)
                            event_repo.publish_stream_event(
                                "merge",
                                {
                                    "winner_cluster_id": updated.cluster_id,
                                    "loser_cluster_id": loser.cluster_id,
                                    "evidence_score": decision.evidence_score,
                                    "evidence_summary": decision.evidence_summary,
                                },
                            )
                            merged += 1
                            merged_any = True
                            break
                        skipped += 1
                    if merged_any:
                        break
            promoted = cluster_repo.promote_old_drafts(self.config.draft_merge_window_minutes)
            if promoted or backfilled_events or backfilled_clusters:
                event_repo.publish_stream_event(
                    "maintenance",
                    {
                        "promoted_drafts": promoted,
                        "backfilled_semantic_events": backfilled_events,
                        "backfilled_semantic_clusters": backfilled_clusters,
                        "semantic_ready_for_active_window": semantic_ready,
                        "missing_active_event_semantics": missing_active_event_semantics,
                        "missing_active_cluster_semantics": missing_active_cluster_semantics,
                        "active_vector_mode": active_vector_mode,
                    },
                )
            conn.commit()
        return {
            "scanned": scanned,
            "merged": merged,
            "skipped": skipped,
            "backfilled_events": backfilled_events,
            "backfilled_clusters": backfilled_clusters,
            "missing_active_event_semantics": missing_active_event_semantics,
            "missing_active_cluster_semantics": missing_active_cluster_semantics,
            "semantic_ready_for_active_window": int(semantic_ready),
            "skipped_for_replay": 0,
        }

    def run_forever(self) -> None:
        while True:
            self.run_once()
            time.sleep(self.config.maintenance_interval_minutes * 60)

    def _refresh_model(self) -> None:
        if self.config.embedding_backend in {"stable-projection", "hash"}:
            return
        if self.model.semantic_available:
            return
        self.model = load_model(self.config)
        self.vector_mode = self.model.resolve_vector_mode(self.config.vector_mode)

    def _backfill_missing_event_semantics(self, event_repo: EventRepository) -> int:
        filled = 0
        for row in event_repo.list_events_missing_semantic_embeddings(limit=100):
            semantic = self.model.embed(row["text"]).semantic_embedding
            if semantic is None:
                continue
            event_repo.upsert_event_semantic_embedding(row["event_id"], semantic)
            filled += 1
        return filled

    def _backfill_missing_cluster_semantics(
        self,
        event_repo: EventRepository,
        cluster_repo: ClusterRepository,
    ) -> int:
        filled = 0
        for cluster_id in cluster_repo.list_clusters_missing_semantic_embeddings(limit=50):
            event_ids = event_repo.list_cluster_event_ids(cluster_id)
            if not event_ids:
                continue
            semantic_embeddings = event_repo.fetch_event_embeddings(event_ids, vector_mode="semantic")
            if len(semantic_embeddings) != len(event_ids):
                continue
            centroid = self._average_embeddings([semantic_embeddings[event_id] for event_id in event_ids])
            cluster_repo.upsert_cluster_semantic_embedding(cluster_id, centroid)
            filled += 1
        return filled

    def _average_embeddings(self, embeddings: list[list[float]]) -> list[float]:
        dimension = len(embeddings[0])
        averaged = [
            sum(embedding[idx] for embedding in embeddings) / len(embeddings)
            for idx in range(dimension)
        ]
        norm = sum(value * value for value in averaged) ** 0.5
        if norm:
            return [value / norm for value in averaged]
        return averaged


def main() -> None:
    config = load_config()
    wait_for_db()
    worker = MaintenanceWorker(config)
    worker.run_forever()


if __name__ == "__main__":
    main()
