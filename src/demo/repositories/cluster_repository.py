from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from demo.domain.models import CandidateCluster, MergeDecision
from demo.domain.text_utils import top_keywords
from demo.repositories.database import parse_vector, vector_literal


class ClusterRepository:
    def __init__(self, conn):
        self.conn = conn

    def acquire_bucket_lock(self, bucket_key: int) -> None:
        with self.conn.cursor() as cur:
            cur.execute("SELECT pg_advisory_xact_lock(%s)", (bucket_key,))

    def find_recent_candidates(
        self,
        *,
        embedding: list[float],
        vector_mode: str,
        max_reuse_age_minutes: int,
        limit: int,
        reference_time,
    ) -> list[CandidateCluster]:
        cutoff = reference_time - timedelta(minutes=max_reuse_age_minutes)
        with self.conn.cursor() as cur:
            if vector_mode == "stable_projection":
                cur.execute(
                    """
                    SELECT c.cluster_id::text AS cluster_id, c.status, c.first_seen_at, c.last_seen_at,
                           c.member_count, s.embedding::text AS centroid_embedding,
                           p.embedding::text AS projection_centroid_embedding,
                           c.exemplar_event_ids, c.keywords, c.summary_text,
                           c.candidate_parent_cluster_id::text AS candidate_parent_cluster_id,
                           c.candidate_parent_score
                    FROM clusters c
                    JOIN projection_embeddings p
                      ON p.entity_type = 'cluster' AND p.entity_id = c.cluster_id::text
                    LEFT JOIN semantic_embeddings s
                      ON s.entity_type = 'cluster' AND s.entity_id = c.cluster_id::text
                    WHERE c.last_seen_at >= %s
                    ORDER BY p.embedding <=> %s::vector
                    LIMIT %s
                    """,
                    (cutoff, vector_literal(embedding), limit),
                )
            else:
                cur.execute(
                    """
                    SELECT c.cluster_id::text AS cluster_id, c.status, c.first_seen_at, c.last_seen_at,
                           c.member_count, s.embedding::text AS centroid_embedding,
                           p.embedding::text AS projection_centroid_embedding,
                           c.exemplar_event_ids, c.keywords, c.summary_text,
                           c.candidate_parent_cluster_id::text AS candidate_parent_cluster_id,
                           c.candidate_parent_score
                    FROM clusters c
                    JOIN semantic_embeddings s
                      ON s.entity_type = 'cluster' AND s.entity_id = c.cluster_id::text
                    JOIN projection_embeddings p
                      ON p.entity_type = 'cluster' AND p.entity_id = c.cluster_id::text
                    WHERE c.last_seen_at >= %s
                    ORDER BY s.embedding <=> %s::vector
                    LIMIT %s
                    """,
                    (cutoff, vector_literal(embedding), limit),
                )
            rows = cur.fetchall()
        return [self._candidate_from_row(row) for row in rows]

    def get_cluster(self, cluster_id: str) -> CandidateCluster | None:
        with self.conn.cursor() as cur:
            cur.execute(
                """
                SELECT c.cluster_id::text AS cluster_id, c.status, c.first_seen_at, c.last_seen_at,
                       c.member_count, s.embedding::text AS centroid_embedding,
                       p.embedding::text AS projection_centroid_embedding,
                       c.exemplar_event_ids, c.keywords, c.summary_text,
                       c.candidate_parent_cluster_id::text AS candidate_parent_cluster_id,
                       c.candidate_parent_score
                FROM clusters c
                JOIN projection_embeddings p
                  ON p.entity_type = 'cluster' AND p.entity_id = c.cluster_id::text
                LEFT JOIN semantic_embeddings s
                  ON s.entity_type = 'cluster' AND s.entity_id = c.cluster_id::text
                WHERE c.cluster_id = %s::uuid
                """,
                (cluster_id,),
            )
            row = cur.fetchone()
        return self._candidate_from_row(row) if row else None

    def create_draft_cluster(
        self,
        *,
        event_id: str,
        occurred_at,
        semantic_embedding: list[float] | None,
        projection_embedding: list[float],
        text: str,
        summary_text: str,
        candidate_parent_cluster_id: str | None,
        candidate_parent_score: float | None,
    ) -> str:
        cluster_id = str(uuid.uuid4())
        keywords = top_keywords([text])
        with self.conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO clusters (
                    cluster_id, status, first_seen_at, last_seen_at, member_count,
                    exemplar_event_ids, keywords, summary_text,
                    candidate_parent_cluster_id, candidate_parent_score
                )
                VALUES (
                    %s::uuid, 'draft', %s, %s, 1,
                    %s::jsonb, %s::jsonb, %s,
                    %s::uuid, %s
                )
                """,
                (
                    cluster_id,
                    occurred_at,
                    occurred_at,
                    json.dumps([event_id]),
                    json.dumps(keywords),
                    summary_text,
                    candidate_parent_cluster_id,
                    candidate_parent_score,
                ),
            )
        self._upsert_embedding(
            table="projection_embeddings",
            entity_id=cluster_id,
            embedding=projection_embedding,
        )
        if semantic_embedding is not None:
            self._upsert_embedding(
                table="semantic_embeddings",
                entity_id=cluster_id,
                embedding=semantic_embedding,
            )
        return cluster_id

    def join_cluster(
        self,
        *,
        cluster: CandidateCluster,
        event_id: str,
        semantic_embedding: list[float] | None,
        projection_embedding: list[float],
        occurred_at,
        cluster_texts: list[str],
        event_text: str,
        summary_text: str | None = None,
    ) -> CandidateCluster:
        next_count = cluster.member_count + 1
        averaged_projection = self._average_embedding(
            cluster.projection_centroid_embedding,
            projection_embedding,
            cluster.member_count,
            next_count,
        )
        averaged_semantic = self._average_optional_embedding(
            cluster.centroid_embedding,
            semantic_embedding,
            cluster.member_count,
            next_count,
        )
        exemplars = list(dict.fromkeys((cluster.exemplar_event_ids + [event_id])[-4:]))
        keywords = top_keywords(cluster_texts + [event_text])
        with self.conn.cursor() as cur:
            cur.execute(
                """
                UPDATE clusters
                SET last_seen_at = %s,
                    member_count = %s,
                    exemplar_event_ids = %s::jsonb,
                    keywords = %s::jsonb,
                    summary_text = %s
                WHERE cluster_id = %s::uuid
                """,
                (
                    occurred_at,
                    next_count,
                    json.dumps(exemplars),
                    json.dumps(keywords),
                    summary_text or cluster.summary_text,
                    cluster.cluster_id,
                ),
            )
        self._upsert_embedding(
            table="projection_embeddings",
            entity_id=cluster.cluster_id,
            embedding=averaged_projection,
        )
        if averaged_semantic is not None:
            self._upsert_embedding(
                table="semantic_embeddings",
                entity_id=cluster.cluster_id,
                embedding=averaged_semantic,
            )
        else:
            self._delete_embedding(table="semantic_embeddings", entity_id=cluster.cluster_id)
        return CandidateCluster(
            cluster_id=cluster.cluster_id,
            status=cluster.status,
            first_seen_at=cluster.first_seen_at,
            last_seen_at=occurred_at,
            member_count=next_count,
            centroid_embedding=averaged_semantic,
            projection_centroid_embedding=averaged_projection,
            exemplar_event_ids=exemplars,
            keywords=keywords,
            summary_text=summary_text or cluster.summary_text,
            candidate_parent_cluster_id=cluster.candidate_parent_cluster_id,
            candidate_parent_score=cluster.candidate_parent_score,
        )

    def list_clusters(self, *, status: str | None = None, since=None) -> list[dict[str, Any]]:
        clauses = []
        params: list[Any] = []
        if status:
            clauses.append("status = %s")
            params.append(status)
        if since:
            clauses.append("last_seen_at >= %s")
            params.append(since)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        with self.conn.cursor() as cur:
            cur.execute(
                f"""
                SELECT cluster_id::text AS cluster_id, status, first_seen_at, last_seen_at,
                       member_count, keywords, summary_text,
                       candidate_parent_cluster_id::text AS candidate_parent_cluster_id,
                       candidate_parent_score
                FROM clusters
                {where}
                ORDER BY last_seen_at DESC
                LIMIT 100
                """,
                params,
            )
            return cur.fetchall()

    def get_cluster_details(self, cluster_id: str) -> dict[str, Any] | None:
        with self.conn.cursor() as cur:
            cur.execute(
                """
                SELECT c.cluster_id::text AS cluster_id, c.status, c.first_seen_at, c.last_seen_at,
                       c.member_count, s.embedding::text AS centroid_embedding,
                       p.embedding::text AS projection_centroid_embedding,
                       c.exemplar_event_ids, c.keywords, c.summary_text,
                       c.candidate_parent_cluster_id::text AS candidate_parent_cluster_id,
                       c.candidate_parent_score
                FROM clusters c
                JOIN projection_embeddings p
                  ON p.entity_type = 'cluster' AND p.entity_id = c.cluster_id::text
                LEFT JOIN semantic_embeddings s
                  ON s.entity_type = 'cluster' AND s.entity_id = c.cluster_id::text
                WHERE c.cluster_id = %s::uuid
                """,
                (cluster_id,),
            )
            cluster = cur.fetchone()
            if cluster is None:
                return None
            cur.execute(
                """
                SELECT event_id, source, occurred_at, text, decision, confidence
                FROM events
                WHERE cluster_id = %s::uuid
                ORDER BY occurred_at DESC
                LIMIT 20
                """,
                (cluster_id,),
            )
            members = cur.fetchall()
            cur.execute(
                """
                SELECT winner_cluster_id::text AS winner_cluster_id, loser_cluster_id::text AS loser_cluster_id,
                       evidence_score, evidence_summary, merged_at
                FROM merge_audit
                WHERE winner_cluster_id = %s::uuid OR loser_cluster_id = %s::uuid
                ORDER BY merged_at DESC
                LIMIT 20
                """,
                (cluster_id, cluster_id),
            )
            merges = cur.fetchall()
        cluster["centroid_embedding"] = parse_vector(cluster["centroid_embedding"]) if cluster["centroid_embedding"] else None
        cluster["projection_centroid_embedding"] = parse_vector(cluster["projection_centroid_embedding"])
        cluster["members"] = members
        cluster["merge_history"] = merges
        return cluster

    def list_recent_draft_clusters(self, window_minutes: int) -> list[CandidateCluster]:
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=window_minutes)
        with self.conn.cursor() as cur:
            cur.execute(
                """
                SELECT c.cluster_id::text AS cluster_id, c.status, c.first_seen_at, c.last_seen_at,
                       c.member_count, s.embedding::text AS centroid_embedding,
                       p.embedding::text AS projection_centroid_embedding,
                       c.exemplar_event_ids, c.keywords, c.summary_text,
                       c.candidate_parent_cluster_id::text AS candidate_parent_cluster_id,
                       c.candidate_parent_score
                FROM clusters c
                JOIN projection_embeddings p
                  ON p.entity_type = 'cluster' AND p.entity_id = c.cluster_id::text
                LEFT JOIN semantic_embeddings s
                  ON s.entity_type = 'cluster' AND s.entity_id = c.cluster_id::text
                WHERE c.status = 'draft' AND c.first_seen_at >= %s
                ORDER BY c.first_seen_at ASC
                """,
                (cutoff,),
            )
            rows = cur.fetchall()
        return [self._candidate_from_row(row) for row in rows]

    def merge_clusters(
        self,
        *,
        winner: CandidateCluster,
        loser: CandidateCluster,
        decision: MergeDecision,
        summary_text: str | None = None,
    ) -> CandidateCluster:
        total_members = winner.member_count + loser.member_count
        merged_projection = self._merge_embedding(
            winner.projection_centroid_embedding,
            loser.projection_centroid_embedding,
            winner.member_count,
            loser.member_count,
            total_members,
        )
        merged_semantic = self._merge_optional_embedding(
            winner.centroid_embedding,
            loser.centroid_embedding,
            winner.member_count,
            loser.member_count,
            total_members,
        )
        exemplars = list(dict.fromkeys((winner.exemplar_event_ids + loser.exemplar_event_ids)[-4:]))
        keywords = list(dict.fromkeys((winner.keywords + loser.keywords)))[:5]
        with self.conn.cursor() as cur:
            cur.execute(
                """
                UPDATE events
                SET cluster_id = %s::uuid
                WHERE cluster_id = %s::uuid
                """,
                (winner.cluster_id, loser.cluster_id),
            )
            cur.execute(
                """
                UPDATE clusters
                SET status = 'draft',
                    last_seen_at = GREATEST(last_seen_at, %s),
                    member_count = %s,
                    exemplar_event_ids = %s::jsonb,
                    keywords = %s::jsonb,
                    summary_text = %s,
                    candidate_parent_cluster_id = NULL,
                    candidate_parent_score = NULL
                WHERE cluster_id = %s::uuid
                """,
                (
                    loser.last_seen_at,
                    total_members,
                    json.dumps(exemplars),
                    json.dumps(keywords),
                    summary_text or winner.summary_text or loser.summary_text,
                    winner.cluster_id,
                ),
            )
            cur.execute(
                """
                INSERT INTO merge_audit (merge_id, winner_cluster_id, loser_cluster_id, evidence_score, evidence_summary)
                VALUES (%s::uuid, %s::uuid, %s::uuid, %s, %s::jsonb)
                """,
                (
                    str(uuid.uuid4()),
                    winner.cluster_id,
                    loser.cluster_id,
                    decision.evidence_score,
                    json.dumps(decision.evidence_summary),
                ),
            )
            cur.execute("DELETE FROM clusters WHERE cluster_id = %s::uuid", (loser.cluster_id,))
        self._upsert_embedding(
            table="projection_embeddings",
            entity_id=winner.cluster_id,
            embedding=merged_projection,
        )
        self._delete_embedding(table="projection_embeddings", entity_id=loser.cluster_id)
        if merged_semantic is not None:
            self._upsert_embedding(
                table="semantic_embeddings",
                entity_id=winner.cluster_id,
                embedding=merged_semantic,
            )
        else:
            self._delete_embedding(table="semantic_embeddings", entity_id=winner.cluster_id)
        self._delete_embedding(table="semantic_embeddings", entity_id=loser.cluster_id)
        return CandidateCluster(
            cluster_id=winner.cluster_id,
            status="draft",
            first_seen_at=winner.first_seen_at,
            last_seen_at=max(winner.last_seen_at, loser.last_seen_at),
            member_count=total_members,
            centroid_embedding=merged_semantic,
            projection_centroid_embedding=merged_projection,
            exemplar_event_ids=exemplars,
            keywords=keywords,
            summary_text=summary_text or winner.summary_text or loser.summary_text,
            candidate_parent_cluster_id=None,
            candidate_parent_score=None,
        )

    def promote_old_drafts(self, window_minutes: int) -> int:
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=window_minutes)
        with self.conn.cursor() as cur:
            cur.execute(
                """
                UPDATE clusters
                SET status = 'stable'
                WHERE status = 'draft' AND first_seen_at < %s
                """,
                (cutoff,),
            )
            return cur.rowcount or 0

    def list_clusters_missing_semantic_embeddings(self, limit: int = 50) -> list[str]:
        with self.conn.cursor() as cur:
            cur.execute(
                """
                SELECT c.cluster_id::text AS cluster_id
                FROM clusters c
                LEFT JOIN semantic_embeddings s
                  ON s.entity_type = 'cluster' AND s.entity_id = c.cluster_id::text
                WHERE s.entity_id IS NULL
                ORDER BY c.last_seen_at DESC
                LIMIT %s
                """,
                (limit,),
            )
            return [row["cluster_id"] for row in cur.fetchall()]

    def count_clusters_missing_semantic_embeddings_since(self, cutoff) -> int:
        with self.conn.cursor() as cur:
            cur.execute(
                """
                SELECT COUNT(*) AS count
                FROM clusters c
                LEFT JOIN semantic_embeddings s
                  ON s.entity_type = 'cluster' AND s.entity_id = c.cluster_id::text
                WHERE c.last_seen_at >= %s
                  AND s.entity_id IS NULL
                """,
                (cutoff,),
            )
            return int(cur.fetchone()["count"])

    def upsert_cluster_semantic_embedding(self, cluster_id: str, embedding: list[float]) -> None:
        self._upsert_embedding(table="semantic_embeddings", entity_id=cluster_id, embedding=embedding)

    def _candidate_from_row(self, row: dict[str, Any]) -> CandidateCluster:
        centroid = parse_vector(row["centroid_embedding"]) if row["centroid_embedding"] else None
        return CandidateCluster(
            cluster_id=row["cluster_id"],
            status=row["status"],
            first_seen_at=row["first_seen_at"],
            last_seen_at=row["last_seen_at"],
            member_count=int(row["member_count"]),
            centroid_embedding=centroid,
            projection_centroid_embedding=parse_vector(row["projection_centroid_embedding"]),
            exemplar_event_ids=list(row["exemplar_event_ids"] or []),
            keywords=list(row["keywords"] or []),
            summary_text=row.get("summary_text") or "",
            candidate_parent_cluster_id=row["candidate_parent_cluster_id"],
            candidate_parent_score=row["candidate_parent_score"],
        )

    def _average_embedding(
        self,
        current_embedding: list[float],
        new_embedding: list[float],
        member_count: int,
        next_count: int,
    ) -> list[float]:
        averaged = [
            ((current_embedding[idx] * member_count) + new_embedding[idx]) / next_count
            for idx in range(len(new_embedding))
        ]
        norm = sum(value * value for value in averaged) ** 0.5
        if norm:
            return [value / norm for value in averaged]
        return averaged

    def _average_optional_embedding(
        self,
        current_embedding: list[float] | None,
        new_embedding: list[float] | None,
        member_count: int,
        next_count: int,
    ) -> list[float] | None:
        if current_embedding is None or new_embedding is None:
            return None
        return self._average_embedding(current_embedding, new_embedding, member_count, next_count)

    def _merge_embedding(
        self,
        winner_embedding: list[float],
        loser_embedding: list[float],
        winner_count: int,
        loser_count: int,
        total_members: int,
    ) -> list[float]:
        merged = [
            ((winner_embedding[idx] * winner_count) + (loser_embedding[idx] * loser_count)) / total_members
            for idx in range(len(winner_embedding))
        ]
        norm = sum(value * value for value in merged) ** 0.5
        if norm:
            return [value / norm for value in merged]
        return merged

    def _merge_optional_embedding(
        self,
        winner_embedding: list[float] | None,
        loser_embedding: list[float] | None,
        winner_count: int,
        loser_count: int,
        total_members: int,
    ) -> list[float] | None:
        if winner_embedding is None or loser_embedding is None:
            return None
        return self._merge_embedding(winner_embedding, loser_embedding, winner_count, loser_count, total_members)

    def _upsert_embedding(self, *, table: str, entity_id: str, embedding: list[float]) -> None:
        with self.conn.cursor() as cur:
            cur.execute(
                f"""
                INSERT INTO {table} (entity_type, entity_id, embedding)
                VALUES ('cluster', %s, %s::vector)
                ON CONFLICT (entity_type, entity_id) DO UPDATE
                SET embedding = EXCLUDED.embedding,
                    updated_at = now()
                """,
                (entity_id, vector_literal(embedding)),
            )

    def _delete_embedding(self, *, table: str, entity_id: str) -> None:
        with self.conn.cursor() as cur:
            cur.execute(
                f"""
                DELETE FROM {table}
                WHERE entity_type = 'cluster' AND entity_id = %s
                """,
                (entity_id,),
            )
