from __future__ import annotations

import itertools
import json
from dataclasses import replace
from datetime import timedelta
from pathlib import Path

from demo.config import DemoConfig
from demo.domain.models import CalibrationRecommendation, CandidateCluster, EventInput
from demo.domain.scoring import cosine_similarity, is_draft_band, merge_decision, score_candidate
from demo.domain.text_utils import fingerprint, load_labels, load_story_events, top_keywords
from demo.embeddings.model_cache import EmbeddingModel


class ThresholdCalibrator:
    def __init__(self, *, config: DemoConfig, model: EmbeddingModel):
        self.config = config
        self.model = model
        self.vector_mode = model.resolve_vector_mode(config.vector_mode)

    def run(self) -> dict[str, object]:
        events = load_story_events(self.config.baseline_story_path)
        labels = load_labels(self.config.baseline_labels_path)
        embedding_sets = {event.event_id: self.model.embed(event.text) for event in events}
        event_fingerprints = {event.event_id: fingerprint(event.text) for event in events}
        recommendations: list[CalibrationRecommendation] = []

        join_values = [0.68, 0.70, 0.72, 0.74]
        draft_min_values = [0.50, 0.56, 0.60, 0.64]
        merge_values = [0.80, 0.85, 0.90]

        for join_threshold, draft_min, merge_threshold in itertools.product(join_values, draft_min_values, merge_values):
            if draft_min >= join_threshold:
                continue
            trial = replace(
                self.config,
                join_threshold=join_threshold,
                draft_score_min=draft_min,
                draft_score_max=join_threshold,
                merge_evidence_threshold=merge_threshold,
            )
            predicted = self._simulate(events, trial, embedding_sets, event_fingerprints)
            precision, recall, f1 = self._pairwise_metrics(predicted, labels)
            recommendations.append(
                CalibrationRecommendation(
                    join_threshold=join_threshold,
                    draft_score_min=draft_min,
                    draft_score_max=join_threshold,
                    merge_evidence_threshold=merge_threshold,
                    pairwise_precision=precision,
                    pairwise_recall=recall,
                    pairwise_f1=f1,
                )
            )

        recommendations.sort(
            key=lambda item: (item.pairwise_f1, item.pairwise_precision, item.join_threshold),
            reverse=True,
        )
        best = recommendations[0]
        search_space = [
            {
                "join_threshold": item.join_threshold,
                "draft_score_min": item.draft_score_min,
                "draft_score_max": item.draft_score_max,
                "merge_evidence_threshold": item.merge_evidence_threshold,
                "pairwise_precision": item.pairwise_precision,
                "pairwise_recall": item.pairwise_recall,
                "pairwise_f1": item.pairwise_f1,
            }
            for item in recommendations
        ]
        report = {
            "recommended_thresholds": {
                "join_threshold": best.join_threshold,
                "draft_score_min": best.draft_score_min,
                "draft_score_max": best.draft_score_max,
                "merge_evidence_threshold": best.merge_evidence_threshold,
            },
            "search_space": search_space,
            "metrics": {
                "pairwise_precision": best.pairwise_precision,
                "pairwise_recall": best.pairwise_recall,
                "pairwise_f1": best.pairwise_f1,
            },
        }
        reports_dir = Path(self.config.reports_dir)
        reports_dir.mkdir(parents=True, exist_ok=True)
        (reports_dir / "calibration-report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        (reports_dir / "calibration-report.md").write_text(self._markdown_report(report), encoding="utf-8")
        return report

    def _simulate(
        self,
        events: list[EventInput],
        config: DemoConfig,
        embedding_sets: dict[str, object],
        event_fingerprints: dict[str, str],
    ) -> dict[str, str]:
        clusters: list[dict[str, object]] = []
        event_cluster: dict[str, str] = {}
        semantic_event_embeddings: dict[str, list[float] | None] = {}
        projection_event_embeddings: dict[str, list[float]] = {}
        cluster_members: dict[str, list[str]] = {}
        aliases: dict[str, str] = {}
        fingerprint_to_cluster: dict[str, str] = {}

        for event in events:
            embedding_set = embedding_sets[event.event_id]
            event_embedding = embedding_set.embedding_for(self.vector_mode)
            semantic_event_embeddings[event.event_id] = embedding_set.semantic_embedding
            projection_event_embeddings[event.event_id] = embedding_set.projection_embedding
            event_fp = event_fingerprints[event.event_id]

            exact = fingerprint_to_cluster.get(event_fp)
            if exact is not None:
                exact = self._resolve_alias(exact, aliases)
                cluster = next((item for item in clusters if item["cluster_id"] == exact), None)
                if cluster is not None:
                    self._add_to_cluster(
                        cluster,
                        event,
                        embedding_set.semantic_embedding,
                        embedding_set.projection_embedding,
                        cluster_members,
                    )
                    event_cluster[event.event_id] = exact
                    self._merge_recent_drafts(
                        clusters,
                        cluster_members,
                        semantic_event_embeddings,
                        projection_event_embeddings,
                        config,
                        event.occurred_at,
                        aliases,
                    )
                    fingerprint_to_cluster[event_fp] = exact
                    continue

            candidates: list[tuple[float, dict[str, object], float]] = []
            for cluster in clusters:
                if event.occurred_at - cluster["last_seen_at"] > timedelta(minutes=config.max_reuse_age_minutes):
                    continue
                candidate = CandidateCluster(
                    cluster_id=cluster["cluster_id"],
                    status=cluster["status"],
                    first_seen_at=cluster["first_seen_at"],
                    last_seen_at=cluster["last_seen_at"],
                    member_count=cluster["member_count"],
                    centroid_embedding=cluster["centroid_embedding"],
                    projection_centroid_embedding=cluster["projection_centroid_embedding"],
                    exemplar_event_ids=cluster["exemplar_event_ids"],
                    keywords=cluster["keywords"],
                    summary_text=cluster.get("summary_text", ""),
                    candidate_parent_cluster_id=cluster.get("candidate_parent_cluster_id"),
                    candidate_parent_score=cluster.get("candidate_parent_score"),
                )
                scored = score_candidate(
                    event_embedding=event_embedding,
                    candidate=candidate,
                    now=event.occurred_at,
                    config=config,
                    vector_mode=self.vector_mode,
                    exemplar_embeddings=[
                        projection_event_embeddings[event_id]
                        if self.vector_mode == "stable_projection"
                        else semantic_event_embeddings[event_id]
                        for event_id in candidate.exemplar_event_ids
                        if (
                            event_id in projection_event_embeddings
                            if self.vector_mode == "stable_projection"
                            else event_id in semantic_event_embeddings and semantic_event_embeddings[event_id] is not None
                        )
                    ],
                )
                if scored.semantic_score >= config.semantic_floor:
                    candidates.append((scored.final_score, cluster, scored.semantic_score))
            candidates.sort(key=lambda item: item[0], reverse=True)

            if candidates and candidates[0][0] >= config.join_threshold:
                cluster = candidates[0][1]
                self._add_to_cluster(
                    cluster,
                    event,
                    embedding_set.semantic_embedding,
                    embedding_set.projection_embedding,
                    cluster_members,
                )
                event_cluster[event.event_id] = cluster["cluster_id"]
            else:
                cluster_id = f"sim-{len(clusters) + 1}"
                parent_hint = None
                parent_score = None
                if candidates and is_draft_band(candidates[0][0], config):
                    parent_hint = candidates[0][1]["cluster_id"]
                    parent_score = candidates[0][0]
                clusters.append(
                    {
                        "cluster_id": cluster_id,
                        "status": "draft",
                        "first_seen_at": event.occurred_at,
                        "last_seen_at": event.occurred_at,
                        "member_count": 1,
                        "centroid_embedding": embedding_set.semantic_embedding,
                        "projection_centroid_embedding": embedding_set.projection_embedding,
                        "exemplar_event_ids": [event.event_id],
                        "keywords": top_keywords([event.text]),
                        "summary_text": event.text,
                        "candidate_parent_cluster_id": parent_hint,
                        "candidate_parent_score": parent_score,
                    }
                )
                cluster_members[cluster_id] = [event.event_id]
                event_cluster[event.event_id] = cluster_id
                fingerprint_to_cluster[event_fp] = cluster_id
            if event.event_id in event_cluster:
                fingerprint_to_cluster[event_fp] = self._resolve_alias(event_cluster[event.event_id], aliases)
            self._merge_recent_drafts(
                clusters,
                cluster_members,
                semantic_event_embeddings,
                projection_event_embeddings,
                config,
                event.occurred_at,
                aliases,
            )

        normalized_mapping = {event_id: self._resolve_alias(cluster_id, aliases) for event_id, cluster_id in event_cluster.items()}
        return normalized_mapping

    def _add_to_cluster(
        self,
        cluster: dict[str, object],
        event: EventInput,
        semantic_embedding: list[float] | None,
        projection_embedding: list[float],
        cluster_members: dict[str, list[str]],
    ) -> None:
        member_count = int(cluster["member_count"])
        next_count = member_count + 1
        centroid = list(cluster["centroid_embedding"]) if cluster["centroid_embedding"] is not None else None
        projection = list(cluster["projection_centroid_embedding"])
        semantic_average = None
        if centroid is not None and semantic_embedding is not None:
            semantic_average = [
                ((centroid[idx] * member_count) + semantic_embedding[idx]) / next_count
                for idx in range(len(semantic_embedding))
            ]
        projection_average = [
            ((projection[idx] * member_count) + projection_embedding[idx]) / next_count
            for idx in range(len(projection_embedding))
        ]
        if semantic_average is not None:
            semantic_norm = sum(value * value for value in semantic_average) ** 0.5
            if semantic_norm:
                semantic_average = [value / semantic_norm for value in semantic_average]
        projection_norm = sum(value * value for value in projection_average) ** 0.5
        if projection_norm:
            projection_average = [value / projection_norm for value in projection_average]
        cluster["centroid_embedding"] = semantic_average
        cluster["projection_centroid_embedding"] = projection_average
        cluster["last_seen_at"] = event.occurred_at
        cluster["member_count"] = next_count
        cluster["exemplar_event_ids"] = list(dict.fromkeys((cluster["exemplar_event_ids"] + [event.event_id])[-4:]))
        cluster_members.setdefault(cluster["cluster_id"], []).append(event.event_id)

    def _merge_recent_drafts(
        self,
        clusters: list[dict[str, object]],
        cluster_members: dict[str, list[str]],
        semantic_event_embeddings: dict[str, list[float] | None],
        projection_event_embeddings: dict[str, list[float]],
        config: DemoConfig,
        current_time,
        aliases: dict[str, str],
    ) -> None:
        changed = True
        while changed:
            changed = False
            cutoff = current_time - timedelta(minutes=config.draft_merge_window_minutes)
            draft_clusters = [
                item
                for item in clusters
                if item["status"] == "draft" and item["first_seen_at"] >= cutoff
            ]
            for idx, left in enumerate(draft_clusters):
                for right in draft_clusters[idx + 1 :]:
                    left_vector = (
                        left["projection_centroid_embedding"]
                        if self.vector_mode == "stable_projection"
                        else (left["centroid_embedding"] or left["projection_centroid_embedding"])
                    )
                    right_vector = (
                        right["projection_centroid_embedding"]
                        if self.vector_mode == "stable_projection"
                        else (right["centroid_embedding"] or right["projection_centroid_embedding"])
                    )
                    exemplar_scores = []
                    for left_id in left["exemplar_event_ids"]:
                        for right_id in right["exemplar_event_ids"]:
                            if self.vector_mode == "stable_projection":
                                left_embedding = projection_event_embeddings.get(left_id)
                                right_embedding = projection_event_embeddings.get(right_id)
                            else:
                                left_embedding = semantic_event_embeddings.get(left_id)
                                right_embedding = semantic_event_embeddings.get(right_id)
                            if left_embedding and right_embedding:
                                exemplar_scores.append(cosine_similarity(left_embedding, right_embedding))
                    similarity = max([cosine_similarity(left_vector, right_vector)] + exemplar_scores, default=0.0)
                    corroborating_links = int(left.get("candidate_parent_cluster_id") == right["cluster_id"]) + int(
                        right.get("candidate_parent_cluster_id") == left["cluster_id"]
                    )
                    keyword_overlap = len(set(left["keywords"]) & set(right["keywords"]))
                    strongest_rejected = max(
                        [score for score in [left.get("candidate_parent_score"), right.get("candidate_parent_score")] if score is not None],
                        default=None,
                    )
                    decision = merge_decision(
                        cluster_similarity=similarity,
                        strongest_rejected_score=strongest_rejected,
                        corroborating_links=corroborating_links,
                        shared_keyword_overlap=keyword_overlap,
                        config=config,
                    )
                    if decision.should_merge:
                        winner = left if left["member_count"] >= right["member_count"] else right
                        loser = right if winner is left else left
                        winner["member_count"] = int(winner["member_count"]) + int(loser["member_count"])
                        if winner["centroid_embedding"] is not None and loser["centroid_embedding"] is not None:
                            winner["centroid_embedding"] = self._merge_embedding(
                                winner["centroid_embedding"],
                                loser["centroid_embedding"],
                            )
                        else:
                            winner["centroid_embedding"] = None
                        winner["projection_centroid_embedding"] = self._merge_embedding(
                            winner["projection_centroid_embedding"],
                            loser["projection_centroid_embedding"],
                        )
                        winner["keywords"] = list(dict.fromkeys((winner["keywords"] + loser["keywords"])))[:5]
                        winner["exemplar_event_ids"] = list(
                            dict.fromkeys(winner["exemplar_event_ids"] + loser["exemplar_event_ids"])
                        )[-4:]
                        cluster_members.setdefault(winner["cluster_id"], []).extend(cluster_members.get(loser["cluster_id"], []))
                        cluster_members.pop(loser["cluster_id"], None)
                        aliases[loser["cluster_id"]] = winner["cluster_id"]
                        clusters.remove(loser)
                        changed = True
                        break
                if changed:
                    break

    def _resolve_alias(self, cluster_id: str, aliases: dict[str, str]) -> str:
        current = cluster_id
        while current in aliases:
            current = aliases[current]
        return current

    def _merge_embedding(self, left: list[float], right: list[float]) -> list[float]:
        merged = [(left[i] + right[i]) / 2.0 for i in range(len(left))]
        norm = sum(value * value for value in merged) ** 0.5
        if norm:
            return [value / norm for value in merged]
        return merged

    def _pairwise_metrics(self, predicted: dict[str, str], labels: dict[str, str]) -> tuple[float, float, float]:
        event_ids = sorted(labels)
        tp = fp = fn = 0
        for idx, left in enumerate(event_ids):
            for right in event_ids[idx + 1 :]:
                expected_same = labels[left] == labels[right]
                predicted_same = predicted.get(left) == predicted.get(right)
                if expected_same and predicted_same:
                    tp += 1
                elif not expected_same and predicted_same:
                    fp += 1
                elif expected_same and not predicted_same:
                    fn += 1
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        f1 = (2 * precision * recall / (precision + recall)) if precision + recall else 0.0
        return precision, recall, f1

    def _markdown_report(self, report: dict[str, object]) -> str:
        recommended = report["recommended_thresholds"]
        metrics = report["metrics"]
        return f"""# Calibration Report

## Recommended Thresholds
- `join_threshold`: {recommended['join_threshold']:.2f}
- `draft_score_min`: {recommended['draft_score_min']:.2f}
- `draft_score_max`: {recommended['draft_score_max']:.2f}
- `merge_evidence_threshold`: {recommended['merge_evidence_threshold']:.2f}

## Metrics
- `pairwise_precision`: {metrics['pairwise_precision']:.3f}
- `pairwise_recall`: {metrics['pairwise_recall']:.3f}
- `pairwise_f1`: {metrics['pairwise_f1']:.3f}
"""
