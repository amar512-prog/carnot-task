from __future__ import annotations

from demo.config import DemoConfig
from demo.domain.models import AssignmentResult, EventInput, MergeDecision, RerankedCandidate
from demo.domain.scoring import cosine_similarity, is_draft_band
from demo.domain.text_utils import fingerprint, normalize_text
from demo.embeddings.model_cache import EmbeddingModel
from demo.intelligence.judge import ClusterJudge
from demo.intelligence.reranker import CandidateReranker
from demo.repositories.cluster_repository import ClusterRepository
from demo.repositories.event_repository import EventRepository
from demo.repositories.runtime_state_repository import RuntimeStateRepository


class ClusteringService:
    def __init__(
        self,
        *,
        config: DemoConfig,
        model: EmbeddingModel,
        reranker: CandidateReranker,
        judge: ClusterJudge,
    ):
        self.config = config
        self.model = model
        self.reranker = reranker
        self.judge = judge

    def assign_event(self, conn, event: EventInput) -> AssignmentResult:
        event_repo = EventRepository(conn)
        cluster_repo = ClusterRepository(conn)
        runtime_state = RuntimeStateRepository(conn)

        existing = event_repo.get_event_by_id(event.event_id)
        if existing and existing.get("cluster_id") and existing.get("decision"):
            return event_repo.result_from_row(existing)

        normalized = normalize_text(event.text)
        event_fingerprint = fingerprint(event.text)
        embeddings = self.model.embed(event.text)
        gate1_vector_mode = self._resolve_gate1_vector_mode(runtime_state, embeddings)
        gate1_embedding = embeddings.embedding_for(gate1_vector_mode)
        event_repo.insert_pending_event(
            event=event,
            normalized_text=normalized,
            fingerprint=event_fingerprint,
            semantic_embedding=embeddings.semantic_embedding,
            projection_embedding=embeddings.projection_embedding,
        )

        cluster_repo.acquire_bucket_lock(self.model.bucket_key(gate1_embedding))

        exact_match = event_repo.find_recent_fingerprint(
            fingerprint=event_fingerprint,
            max_reuse_age_minutes=self.config.max_reuse_age_minutes,
            exclude_event_id=event.event_id,
            reference_time=event.occurred_at,
        )
        if exact_match and exact_match.get("cluster_id"):
            matched_cluster = cluster_repo.get_cluster(exact_match["cluster_id"])
            if matched_cluster is not None:
                cluster_texts = event_repo.list_cluster_texts(matched_cluster.cluster_id)
                updated = cluster_repo.join_cluster(
                    cluster=matched_cluster,
                    event_id=event.event_id,
                    semantic_embedding=embeddings.semantic_embedding,
                    projection_embedding=embeddings.projection_embedding,
                    occurred_at=event.occurred_at,
                    cluster_texts=cluster_texts,
                    event_text=event.text,
                )
                result = AssignmentResult(
                    cluster_id=updated.cluster_id,
                    decision="joined_existing_cluster",
                    cluster_status=updated.status,
                    confidence=1.0,
                    gate1_score=1.0,
                    gate2_score=1.0,
                    judge_confidence=1.0,
                    judge_decision="exact_fingerprint_match",
                    semantic_score=1.0,
                    time_weight=None,
                    final_score=1.0,
                )
                event_repo.finalize_assignment(event.event_id, result)
                event_repo.publish_stream_event(
                    "assignment",
                    {
                        "event_id": event.event_id,
                        "cluster_id": result.cluster_id,
                        "decision": result.decision,
                        "confidence": result.confidence,
                        "gate1_score": result.gate1_score,
                        "gate2_score": result.gate2_score,
                        "judge_confidence": result.judge_confidence,
                        "judge_decision": result.judge_decision,
                        "reason": "exact_fingerprint_match",
                    },
                )
                return result

        candidates = cluster_repo.find_recent_candidates(
            embedding=gate1_embedding,
            vector_mode=gate1_vector_mode,
            max_reuse_age_minutes=self.config.max_reuse_age_minutes,
            limit=self.config.candidate_limit,
            reference_time=event.occurred_at,
        )
        gate1_scores = {
            candidate.cluster_id: cosine_similarity(gate1_embedding, candidate.embedding_for(gate1_vector_mode))
            for candidate in candidates
        }
        reranked = self.reranker.rerank(
            event_text=event.text,
            candidates=candidates,
            gate1_scores=gate1_scores,
        )[: self.config.reranker_top_k]
        judge_decision = self.judge.decide(event_text=event.text, candidates=reranked)

        result: AssignmentResult
        if judge_decision.decision == "both" and len(reranked) >= 2:
            winner = reranked[0].candidate
            loser = reranked[1].candidate
            merge_result = MergeDecision(
                should_merge=True,
                evidence_score=min(reranked[0].gate2_score, reranked[1].gate2_score),
                evidence_summary={
                    "judge_reason": judge_decision.reason,
                    "judge_confidence": judge_decision.confidence,
                    "cluster_a_score": reranked[0].gate2_score,
                    "cluster_b_score": reranked[1].gate2_score,
                },
            )
            merged = cluster_repo.merge_clusters(
                winner=winner,
                loser=loser,
                decision=merge_result,
                summary_text=winner.summary_text or loser.summary_text,
            )
            event_repo.publish_stream_event(
                "merge",
                {
                    "winner_cluster_id": merged.cluster_id,
                    "loser_cluster_id": loser.cluster_id,
                    "evidence_score": merge_result.evidence_score,
                    "judge_confidence": judge_decision.confidence,
                    "judge_reason": judge_decision.reason,
                },
            )
            result = self._join_candidate(
                cluster_repo=cluster_repo,
                event_repo=event_repo,
                event=event,
                embeddings=embeddings,
                candidate=RerankedCandidate(
                    candidate=merged,
                    gate1_score=reranked[0].gate1_score,
                    gate2_score=max(reranked[0].gate2_score, reranked[1].gate2_score),
                ),
                judge_decision=judge_decision,
            )
        elif judge_decision.decision in {"cluster_a", "cluster_b"} and reranked:
            selected_index = 0 if judge_decision.decision == "cluster_a" else 1
            if selected_index >= len(reranked):
                selected_index = 0
            result = self._join_candidate(
                cluster_repo=cluster_repo,
                event_repo=event_repo,
                event=event,
                embeddings=embeddings,
                candidate=reranked[selected_index],
                judge_decision=judge_decision,
            )
        else:
            top_candidate = reranked[0] if reranked else None
            candidate_parent_cluster_id = None
            candidate_parent_score = None
            if top_candidate and is_draft_band(top_candidate.gate2_score, self.config):
                candidate_parent_cluster_id = top_candidate.candidate.cluster_id
                candidate_parent_score = top_candidate.gate2_score
            summary_text = self.judge.generate_summary(event_text=event.text, metadata=event.metadata)
            cluster_id = cluster_repo.create_draft_cluster(
                event_id=event.event_id,
                occurred_at=event.occurred_at,
                semantic_embedding=embeddings.semantic_embedding,
                projection_embedding=embeddings.projection_embedding,
                text=event.text,
                summary_text=summary_text,
                candidate_parent_cluster_id=candidate_parent_cluster_id,
                candidate_parent_score=candidate_parent_score,
            )
            result = AssignmentResult(
                cluster_id=cluster_id,
                decision="created_new_cluster",
                cluster_status="draft",
                confidence=judge_decision.confidence or (top_candidate.gate2_score if top_candidate else 0.0),
                gate1_score=top_candidate.gate1_score if top_candidate else None,
                gate2_score=top_candidate.gate2_score if top_candidate else None,
                judge_confidence=judge_decision.confidence,
                judge_decision=judge_decision.decision,
                semantic_score=top_candidate.gate1_score if top_candidate else None,
                time_weight=None,
                final_score=top_candidate.gate2_score if top_candidate else None,
                candidate_parent_cluster_id=candidate_parent_cluster_id,
                candidate_parent_score=candidate_parent_score,
            )

        event_repo.finalize_assignment(event.event_id, result)
        event_repo.publish_stream_event(
            "assignment",
            {
                "event_id": event.event_id,
                "cluster_id": result.cluster_id,
                "decision": result.decision,
                "cluster_status": result.cluster_status,
                "confidence": result.confidence,
                "gate1_score": result.gate1_score,
                "gate2_score": result.gate2_score,
                "judge_confidence": result.judge_confidence,
                "judge_decision": result.judge_decision,
                "semantic_score": result.semantic_score,
                "final_score": result.final_score,
                "candidate_parent_cluster_id": result.candidate_parent_cluster_id,
                "candidate_parent_score": result.candidate_parent_score,
            },
        )
        return result

    def _join_candidate(
        self,
        *,
        cluster_repo: ClusterRepository,
        event_repo: EventRepository,
        event: EventInput,
        embeddings,
        candidate: RerankedCandidate,
        judge_decision,
    ) -> AssignmentResult:
        cluster_texts = event_repo.list_cluster_texts(candidate.candidate.cluster_id)
        updated = cluster_repo.join_cluster(
            cluster=candidate.candidate,
            event_id=event.event_id,
            semantic_embedding=embeddings.semantic_embedding,
            projection_embedding=embeddings.projection_embedding,
            occurred_at=event.occurred_at,
            cluster_texts=cluster_texts,
            event_text=event.text,
        )
        return AssignmentResult(
            cluster_id=updated.cluster_id,
            decision="joined_existing_cluster",
            cluster_status=updated.status,
            confidence=judge_decision.confidence or candidate.gate2_score,
            gate1_score=candidate.gate1_score,
            gate2_score=candidate.gate2_score,
            judge_confidence=judge_decision.confidence,
            judge_decision=judge_decision.decision,
            semantic_score=candidate.gate1_score,
            time_weight=None,
            final_score=candidate.gate2_score,
        )

    def _resolve_gate1_vector_mode(self, runtime_state: RuntimeStateRepository, embeddings) -> str:
        gate1_vector_mode = self.config.gate1_vector_mode
        if gate1_vector_mode == "semantic":
            semantic_ready = runtime_state.get_bool_flag("semantic_ready_for_active_window", default=False)
            if embeddings.semantic_embedding is None:
                runtime_state.set_bool_flag("semantic_ready_for_active_window", False)
            if not semantic_ready or embeddings.semantic_embedding is None:
                return "stable_projection"
        if gate1_vector_mode == "auto":
            resolved = self.model.resolve_vector_mode(self.config.vector_mode)
            if resolved == "semantic":
                semantic_ready = runtime_state.get_bool_flag("semantic_ready_for_active_window", default=False)
                if embeddings.semantic_embedding is None:
                    runtime_state.set_bool_flag("semantic_ready_for_active_window", False)
                return "semantic" if semantic_ready and embeddings.semantic_embedding is not None else "stable_projection"
            return resolved
        return gate1_vector_mode
