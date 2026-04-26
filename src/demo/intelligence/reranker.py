from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from demo.config import DemoConfig
from demo.domain.models import CandidateCluster, RerankedCandidate
from demo.domain.scoring import cosine_similarity
from demo.embeddings.model_cache import StableProjectionEmbeddingModel


class CandidateReranker(Protocol):
    def rerank(
        self,
        *,
        event_text: str,
        candidates: list[CandidateCluster],
        gate1_scores: dict[str, float],
    ) -> list[RerankedCandidate]:
        ...


@dataclass(slots=True)
class FallbackReranker:
    model_id: str
    projection_backend: StableProjectionEmbeddingModel

    def rerank(
        self,
        *,
        event_text: str,
        candidates: list[CandidateCluster],
        gate1_scores: dict[str, float],
    ) -> list[RerankedCandidate]:
        event_embedding = self.projection_backend.embed(event_text).projection_embedding
        ranked: list[RerankedCandidate] = []
        for candidate in candidates:
            summary_text = candidate.summary_text.strip() or " ".join(candidate.keywords)
            summary_embedding = self.projection_backend.embed(summary_text).projection_embedding
            ranked.append(
                RerankedCandidate(
                    candidate=candidate,
                    gate1_score=gate1_scores.get(candidate.cluster_id, 0.0),
                    gate2_score=max(0.0, cosine_similarity(event_embedding, summary_embedding)),
                )
            )
        ranked.sort(key=lambda item: item.gate2_score, reverse=True)
        return ranked


@dataclass(slots=True)
class MiniLMReranker:
    model_id: str
    backend: object
    fallback: FallbackReranker

    def rerank(
        self,
        *,
        event_text: str,
        candidates: list[CandidateCluster],
        gate1_scores: dict[str, float],
    ) -> list[RerankedCandidate]:
        if not candidates:
            return []
        pairs = [(event_text, candidate.summary_text.strip() or " ".join(candidate.keywords)) for candidate in candidates]
        try:
            raw_scores = self.backend.predict(pairs)
        except Exception:
            return self.fallback.rerank(event_text=event_text, candidates=candidates, gate1_scores=gate1_scores)

        ranked: list[RerankedCandidate] = []
        for candidate, raw_score in zip(candidates, raw_scores):
            score = float(raw_score)
            score = 1.0 / (1.0 + math.exp(-score))
            ranked.append(
                RerankedCandidate(
                    candidate=candidate,
                    gate1_score=gate1_scores.get(candidate.cluster_id, 0.0),
                    gate2_score=score,
                )
            )
        ranked.sort(key=lambda item: item.gate2_score, reverse=True)
        return ranked


_RERANKER_CACHE = {}

def load_reranker(config: DemoConfig) -> CandidateReranker:
    if config.reranker_model_id in _RERANKER_CACHE:
        return _RERANKER_CACHE[config.reranker_model_id]
        
    cache_dir = Path(config.model_cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    reranker_cache_dir = cache_dir / "rerankers"
    reranker_cache_dir.mkdir(parents=True, exist_ok=True)
    projection_backend = StableProjectionEmbeddingModel(
        model_id="stable-projection-reranker-v1",
        dimension=int(config.embedding_dimension),
        cache_dir=cache_dir,
    )
    fallback = FallbackReranker(
        model_id="stable-projection-reranker-v1",
        projection_backend=projection_backend,
    )
    manifest_path = cache_dir / "reranker_manifest.json"
    try:
        from sentence_transformers.cross_encoder import CrossEncoder

        backend = CrossEncoder(config.reranker_model_id)
        manifest_path.write_text(
            json.dumps(
                {
                    "backend": "cross-encoder",
                    "model_id": config.reranker_model_id,
                    "top_k": config.reranker_top_k,
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        res = MiniLMReranker(model_id=config.reranker_model_id, backend=backend, fallback=fallback)
        _RERANKER_CACHE[config.reranker_model_id] = res
        return res
    except Exception:
        manifest_path.write_text(
            json.dumps(
                {
                    "backend": "stable-projection",
                    "model_id": fallback.model_id,
                    "top_k": config.reranker_top_k,
                    "notes": "Fallback reranker used because the MiniLM cross-encoder was unavailable.",
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        _RERANKER_CACHE[config.reranker_model_id] = fallback
        return fallback
