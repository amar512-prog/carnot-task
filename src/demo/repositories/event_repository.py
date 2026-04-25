from __future__ import annotations

import json
from datetime import datetime, timedelta
from typing import Any

from demo.domain.models import AssignmentResult, EventInput
from demo.repositories.database import parse_vector, vector_literal


class EventRepository:
    def __init__(self, conn):
        self.conn = conn

    def get_event_by_id(self, event_id: str) -> dict[str, Any] | None:
        with self.conn.cursor() as cur:
            cur.execute(
                """
                SELECT e.event_id, e.cluster_id::text AS cluster_id, e.decision, e.confidence,
                       e.gate1_score, e.gate2_score, e.judge_confidence, e.judge_decision,
                       e.semantic_score, e.time_weight, e.final_score, e.metadata,
                       c.status AS cluster_status
                FROM events e
                LEFT JOIN clusters c ON c.cluster_id = e.cluster_id
                WHERE e.event_id = %s
                """,
                (event_id,),
            )
            return cur.fetchone()

    def insert_pending_event(
        self,
        *,
        event: EventInput,
        normalized_text: str,
        fingerprint: str,
        semantic_embedding: list[float] | None,
        projection_embedding: list[float],
    ) -> None:
        with self.conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO events (
                    event_id, source, occurred_at, text, normalized_text, fingerprint, metadata
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb)
                ON CONFLICT (event_id) DO UPDATE
                SET source = EXCLUDED.source,
                    occurred_at = EXCLUDED.occurred_at,
                    text = EXCLUDED.text,
                    normalized_text = EXCLUDED.normalized_text,
                    fingerprint = EXCLUDED.fingerprint,
                    metadata = EXCLUDED.metadata
                """,
                (
                    event.event_id,
                    event.source,
                    event.occurred_at,
                    event.text,
                    normalized_text,
                    fingerprint,
                    json.dumps(event.metadata),
                ),
            )
        self._upsert_embedding(
            table="projection_embeddings",
            entity_type="event",
            entity_id=event.event_id,
            embedding=projection_embedding,
        )
        if semantic_embedding is not None:
            self._upsert_embedding(
                table="semantic_embeddings",
                entity_type="event",
                entity_id=event.event_id,
                embedding=semantic_embedding,
            )

    def finalize_assignment(self, event_id: str, result: AssignmentResult) -> None:
        with self.conn.cursor() as cur:
            cur.execute(
                """
                UPDATE events
                SET cluster_id = %s::uuid,
                    decision = %s,
                    confidence = %s,
                    gate1_score = %s,
                    gate2_score = %s,
                    judge_confidence = %s,
                    judge_decision = %s,
                    semantic_score = %s,
                    time_weight = %s,
                    final_score = %s
                WHERE event_id = %s
                """,
                (
                    result.cluster_id,
                    result.decision,
                    result.confidence,
                    result.gate1_score,
                    result.gate2_score,
                    result.judge_confidence,
                    result.judge_decision,
                    result.semantic_score,
                    result.time_weight,
                    result.final_score,
                    event_id,
                ),
            )

    def result_from_row(self, row: dict[str, Any]) -> AssignmentResult:
        return AssignmentResult(
            cluster_id=row["cluster_id"],
            decision=row["decision"],
            cluster_status=row.get("cluster_status") or "stable",
            confidence=float(row["confidence"] or 0.0),
            gate1_score=row.get("gate1_score"),
            gate2_score=row.get("gate2_score"),
            judge_confidence=row.get("judge_confidence"),
            judge_decision=row.get("judge_decision"),
            semantic_score=row["semantic_score"],
            time_weight=row["time_weight"],
            final_score=row["final_score"],
        )

    def find_recent_fingerprint(
        self,
        *,
        fingerprint: str,
        max_reuse_age_minutes: int,
        exclude_event_id: str,
        reference_time: datetime,
    ) -> dict[str, Any] | None:
        cutoff = reference_time - timedelta(minutes=max_reuse_age_minutes)
        with self.conn.cursor() as cur:
            cur.execute(
                """
                SELECT event_id, cluster_id::text AS cluster_id
                FROM events
                WHERE fingerprint = %s
                  AND event_id <> %s
                  AND cluster_id IS NOT NULL
                  AND occurred_at >= %s
                ORDER BY occurred_at DESC
                LIMIT 1
                """,
                (fingerprint, exclude_event_id, cutoff),
            )
            return cur.fetchone()

    def fetch_event_embeddings(self, event_ids: list[str], *, vector_mode: str = "semantic") -> dict[str, list[float]]:
        if not event_ids:
            return {}
        table = "projection_embeddings" if vector_mode == "stable_projection" else "semantic_embeddings"
        with self.conn.cursor() as cur:
            cur.execute(
                f"""
                SELECT entity_id AS event_id, embedding::text AS embedding
                FROM {table}
                WHERE entity_type = 'event'
                  AND entity_id = ANY(%s)
                """,
                (event_ids,),
            )
            rows = cur.fetchall()
        return {row["event_id"]: parse_vector(row["embedding"]) for row in rows}

    def list_cluster_texts(self, cluster_id: str, limit: int = 20) -> list[str]:
        with self.conn.cursor() as cur:
            cur.execute(
                """
                SELECT text
                FROM events
                WHERE cluster_id = %s::uuid
                ORDER BY occurred_at DESC
                LIMIT %s
                """,
                (cluster_id, limit),
            )
            return [row["text"] for row in cur.fetchall()]

    def load_baseline_story(self) -> list[EventInput]:
        with self.conn.cursor() as cur:
            cur.execute(
                """
                SELECT event_id, source, occurred_at, text, metadata
                FROM baseline_story_events
                ORDER BY seq_id
                """
            )
            rows = cur.fetchall()
        events: list[EventInput] = []
        for row in rows:
            events.append(
                EventInput(
                    event_id=row["event_id"],
                    source=row["source"],
                    occurred_at=row["occurred_at"],
                    text=row["text"],
                    metadata=row["metadata"],
                )
            )
        return events

    def replace_baseline_story(self, events: list[EventInput]) -> int:
        with self.conn.cursor() as cur:
            cur.execute("TRUNCATE TABLE baseline_story_events RESTART IDENTITY")
            for event in events:
                cur.execute(
                    """
                    INSERT INTO baseline_story_events (event_id, source, occurred_at, text, metadata)
                    VALUES (%s, %s, %s, %s, %s::jsonb)
                    """,
                    (
                        event.event_id,
                        event.source,
                        event.occurred_at,
                        event.text,
                        json.dumps(event.metadata),
                    ),
                )
        return len(events)

    def clear_runtime_state(self) -> dict[str, int]:
        with self.conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) AS count FROM events")
            events_count = int(cur.fetchone()["count"])
            cur.execute("SELECT COUNT(*) AS count FROM clusters")
            clusters_count = int(cur.fetchone()["count"])
            cur.execute(
                "TRUNCATE TABLE merge_audit, semantic_embeddings, projection_embeddings, events, clusters RESTART IDENTITY"
            )
            cur.execute("DELETE FROM stream_events")
        return {"events": events_count, "clusters": clusters_count}

    def publish_stream_event(self, event_type: str, payload: dict[str, Any]) -> None:
        with self.conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO stream_events (event_type, payload)
                VALUES (%s, %s::jsonb)
                """,
                (event_type, json.dumps(payload)),
            )

    def fetch_stream_events(self, last_id: int) -> list[dict[str, Any]]:
        with self.conn.cursor() as cur:
            cur.execute(
                """
                SELECT stream_id, event_type, payload, emitted_at
                FROM stream_events
                WHERE stream_id > %s
                ORDER BY stream_id ASC
                LIMIT 100
                """,
                (last_id,),
            )
            return cur.fetchall()

    def list_events_missing_semantic_embeddings(self, limit: int = 100) -> list[dict[str, Any]]:
        with self.conn.cursor() as cur:
            cur.execute(
                """
                SELECT e.event_id, e.text
                FROM events e
                LEFT JOIN semantic_embeddings s
                  ON s.entity_type = 'event' AND s.entity_id = e.event_id
                WHERE s.entity_id IS NULL
                ORDER BY e.occurred_at ASC
                LIMIT %s
                """,
                (limit,),
            )
            return cur.fetchall()

    def count_events_missing_semantic_embeddings_since(self, cutoff: datetime) -> int:
        with self.conn.cursor() as cur:
            cur.execute(
                """
                SELECT COUNT(*) AS count
                FROM events e
                LEFT JOIN semantic_embeddings s
                  ON s.entity_type = 'event' AND s.entity_id = e.event_id
                WHERE e.occurred_at >= %s
                  AND s.entity_id IS NULL
                """,
                (cutoff,),
            )
            return int(cur.fetchone()["count"])

    def list_cluster_event_ids(self, cluster_id: str) -> list[str]:
        with self.conn.cursor() as cur:
            cur.execute(
                """
                SELECT event_id
                FROM events
                WHERE cluster_id = %s::uuid
                ORDER BY occurred_at ASC
                """,
                (cluster_id,),
            )
            return [row["event_id"] for row in cur.fetchall()]

    def upsert_event_semantic_embedding(self, event_id: str, embedding: list[float]) -> None:
        self._upsert_embedding(
            table="semantic_embeddings",
            entity_type="event",
            entity_id=event_id,
            embedding=embedding,
        )

    def _upsert_embedding(
        self,
        *,
        table: str,
        entity_type: str,
        entity_id: str,
        embedding: list[float],
    ) -> None:
        with self.conn.cursor() as cur:
            cur.execute(
                f"""
                INSERT INTO {table} (entity_type, entity_id, embedding)
                VALUES (%s, %s, %s::vector)
                ON CONFLICT (entity_type, entity_id) DO UPDATE
                SET embedding = EXCLUDED.embedding,
                    updated_at = now()
                """,
                (entity_type, entity_id, vector_literal(embedding)),
            )
