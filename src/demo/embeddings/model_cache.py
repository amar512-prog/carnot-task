from __future__ import annotations

import json
import math
import zlib
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

from demo.config import DemoConfig
from demo.domain.text_utils import tokenize


@dataclass(slots=True)
class EmbeddingSet:
    semantic_embedding: list[float] | None
    projection_embedding: list[float]

    def embedding_for(self, vector_mode: str) -> list[float]:
        if vector_mode == "stable_projection" or self.semantic_embedding is None:
            return self.projection_embedding
        return self.semantic_embedding


class EmbeddingModel(Protocol):
    model_id: str
    dimension: int
    cache_dir: Path
    semantic_available: bool

    def embed(self, text: str) -> EmbeddingSet:
        ...

    def bucket_key(self, embedding: list[float], bits: int = 8) -> int:
        ...

    def resolve_vector_mode(self, configured_mode: str) -> str:
        ...


@dataclass(slots=True)
class BaseEmbeddingModel:
    model_id: str
    dimension: int
    cache_dir: Path
    semantic_available: bool = field(default=False, init=False)

    def bucket_key(self, embedding: list[float], bits: int = 8) -> int:
        bucket = 0
        for idx in range(min(bits, len(embedding))):
            if embedding[idx] >= 0:
                bucket |= 1 << idx
        return bucket

    def resolve_vector_mode(self, configured_mode: str) -> str:
        requested = configured_mode.strip().lower()
        if requested == "stable_projection":
            return "stable_projection"
        if requested == "semantic":
            return "semantic" if self.semantic_available else "stable_projection"
        return "semantic" if self.semantic_available else "stable_projection"


@dataclass(slots=True)
class StableProjectionEmbeddingModel(BaseEmbeddingModel):
    semantic_available: bool = field(default=False, init=False)

    def embed(self, text: str) -> EmbeddingSet:
        projection = self._project(text)
        return EmbeddingSet(
            semantic_embedding=None,
            projection_embedding=projection,
        )

    def _project(self, text: str) -> list[float]:
        vector = [0.0] * self.dimension
        tokens = tokenize(text)
        if not tokens:
            return vector

        features = Counter(tokens)
        features.update(f"bg:{left}|{right}" for left, right in zip(tokens, tokens[1:]))
        for feature, count in features.items():
            index = zlib.crc32(feature.encode("utf-8")) % self.dimension
            sign_seed = zlib.crc32(f"{feature}|sign".encode("utf-8"))
            sign = 1.0 if sign_seed % 2 == 0 else -1.0
            weight = 1.0 + math.log1p(count)
            vector[index] += sign * weight

        norm = sum(value * value for value in vector) ** 0.5
        if norm == 0:
            return vector
        return [value / norm for value in vector]


@dataclass(slots=True)
class SentenceTransformerEmbeddingModel(BaseEmbeddingModel):
    backend: object
    projection_backend: StableProjectionEmbeddingModel
    semantic_available: bool = field(default=True, init=False)

    def embed(self, text: str) -> EmbeddingSet:
        projection = self.projection_backend.embed(text).projection_embedding
        try:
            encoded = self.backend.encode(text, normalize_embeddings=True)
            vector = encoded.tolist() if hasattr(encoded, "tolist") else list(encoded)
            if len(vector) == self.dimension:
                semantic = [float(value) for value in vector]
            else:
                projected = [0.0] * self.dimension
                for index, value in enumerate(vector):
                    slot = index % self.dimension
                    sign = 1.0 if (index // self.dimension) % 2 == 0 else -1.0
                    projected[slot] += float(value) * sign
                norm = sum(component * component for component in projected) ** 0.5
                semantic = projected if norm == 0 else [component / norm for component in projected]
        except Exception:
            semantic = None
        return EmbeddingSet(
            semantic_embedding=semantic,
            projection_embedding=projection,
        )


_MODEL_CACHE = {}

def load_model(config: DemoConfig) -> EmbeddingModel:
    if config.embedding_model_id in _MODEL_CACHE:
        return _MODEL_CACHE[config.embedding_model_id]
    
    cache_dir = Path(config.model_cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = cache_dir / "model_manifest.json"
    semantic_cache_dir = cache_dir / "hf-cache-v2"
    semantic_cache_dir.mkdir(parents=True, exist_ok=True)
    projection_backend = StableProjectionEmbeddingModel(
        model_id="stable-projection-v1",
        dimension=int(config.embedding_dimension),
        cache_dir=cache_dir,
    )
    if config.embedding_backend in {"stable-projection", "hash"}:
        manifest = {
            "backend": "stable-projection",
            "model_id": projection_backend.model_id,
            "target_dimension": config.embedding_dimension,
            "vector_mode": projection_backend.resolve_vector_mode(config.vector_mode),
            "notes": "Deterministic sparse bag-of-words projection used for degraded mode and resource-constrained runs.",
        }
        manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        _MODEL_CACHE[config.embedding_model_id] = projection_backend
        return projection_backend
    try:
        from sentence_transformers import SentenceTransformer

        backend = SentenceTransformer(config.embedding_model_id, cache_folder=str(semantic_cache_dir))
        model = SentenceTransformerEmbeddingModel(
            model_id=config.embedding_model_id,
            dimension=int(config.embedding_dimension),
            cache_dir=semantic_cache_dir,
            backend=backend,
            projection_backend=projection_backend,
        )
        manifest = {
            "backend": "sentence-transformers",
            "model_id": config.embedding_model_id,
            "source_dimension": int(backend.get_sentence_embedding_dimension()),
            "target_dimension": config.embedding_dimension,
            "projection_backend": projection_backend.model_id,
            "vector_mode": model.resolve_vector_mode(config.vector_mode),
            "notes": "Primary semantic model with a deterministic stable-projection companion vector for degraded-mode clustering.",
        }
        manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        _MODEL_CACHE[config.embedding_model_id] = model
        return model
    except Exception:
        manifest = {
            "backend": "stable-projection",
            "model_id": projection_backend.model_id,
            "target_dimension": config.embedding_dimension,
            "vector_mode": projection_backend.resolve_vector_mode(config.vector_mode),
            "notes": "Fallback deterministic projection used because sentence-transformers was unavailable.",
        }
        manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        _MODEL_CACHE[config.embedding_model_id] = projection_backend
        return projection_backend


HashEmbeddingModel = StableProjectionEmbeddingModel
