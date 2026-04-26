from __future__ import annotations

from datetime import datetime, timezone

from demo.config import DemoConfig
from demo.domain.text_utils import load_story_events
from demo.embeddings.model_cache import load_model
from demo.intelligence import load_judge, load_reranker
from demo.repositories.database import connect_db, ensure_schema
from demo.repositories.event_repository import EventRepository
from demo.repositories.runtime_state_repository import RuntimeStateRepository
from demo.services.clustering_service import ClusteringService


class ResetService:
    def __init__(self, config: DemoConfig):
        self.config = config

    def ensure_baseline_story_loaded(self) -> int:
        ensure_schema()
        story_events = load_story_events(self.config.baseline_story_path)
        with connect_db() as conn:
            repo = EventRepository(conn)
            count = repo.replace_baseline_story(story_events)
            conn.commit()
            return count

    def reset_to_baseline(self, *, rehydrate_runtime: bool = True, approach: int = 2) -> dict[str, object]:
        ensure_schema()
        story_events = load_story_events(self.config.baseline_story_path)
        return self.reset_with_story(
            story_events,
            rehydrate_runtime=rehydrate_runtime,
            persist_baseline=True,
            approach=approach,
        )

    def reset_with_story(
        self,
        story_events,
        *,
        rehydrate_runtime: bool = True,
        persist_baseline: bool = True,
        approach: int = 2,
    ) -> dict[str, object]:
        ensure_schema()
        restored_clusters: set[str] = set()
        restored_at = datetime.now(timezone.utc).isoformat()
        with connect_db() as conn:
            repo = EventRepository(conn)
            runtime_state = RuntimeStateRepository(conn)
            runtime_state.acquire_replay_maintenance_lock()
            deleted = repo.clear_runtime_state()
            runtime_state.set_bool_flag("semantic_ready_for_active_window", False)
            restored = repo.replace_baseline_story(story_events) if persist_baseline else 0
            repo.publish_stream_event(
                "reset",
                {
                    "phase": "started",
                    "deleted_events": deleted["events"],
                    "deleted_clusters": deleted["clusters"],
                    "rehydrate_runtime": rehydrate_runtime,
                    "restored_at": restored_at,
                },
            )
            if rehydrate_runtime:
                model = load_model(self.config)
                clustering_service = ClusteringService(
                    config=self.config,
                    model=model,
                    reranker=load_reranker(self.config),
                    judge=load_judge(self.config),
                )
                for event in story_events:
                    import logging
                    event.metadata = {**getattr(event, "metadata", {}), "approach": approach}
                    result = clustering_service.assign_event(conn, event)
                    restored_clusters.add(result.cluster_id)
            repo.publish_stream_event(
                "reset",
                {
                    "phase": "completed",
                    "deleted_events": deleted["events"],
                    "deleted_clusters": deleted["clusters"],
                    "restored_baseline_events": restored,
                    "restored_runtime_events": len(story_events) if rehydrate_runtime else 0,
                    "restored_runtime_clusters": len(restored_clusters),
                    "rehydrate_runtime": rehydrate_runtime,
                    "restored_at": restored_at,
                },
            )
            conn.commit()
            import logging
            logging.info("transaction committed, all locks released")
            return {
                "deleted_events": deleted["events"],
                "deleted_clusters": deleted["clusters"],
                "restored_baseline_events": restored,
                "restored_runtime_events": len(story_events) if rehydrate_runtime else 0,
                "restored_runtime_clusters": len(restored_clusters),
                "rehydrate_runtime": rehydrate_runtime,
                "restored_at": restored_at,
            }
