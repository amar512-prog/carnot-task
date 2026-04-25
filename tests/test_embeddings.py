from __future__ import annotations

import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from demo.config import load_config
from demo.domain.scoring import cosine_similarity
from demo.embeddings.model_cache import load_model


class EmbeddingFallbackTest(unittest.TestCase):
    def test_stable_projection_prefers_related_texts(self) -> None:
        base = load_config("config/demo.yaml")
        with tempfile.TemporaryDirectory() as tmp_dir:
            config = replace(
                base,
                embedding_backend="stable-projection",
                vector_mode="stable_projection",
                model_cache_dir=str(Path(tmp_dir) / "models"),
            )
            model = load_model(config)
            a = model.embed("database timeout in login flow").projection_embedding
            b = model.embed("login flow database timeout again").projection_embedding
            c = model.embed("printer toner shipment arrived").projection_embedding

        self.assertGreater(cosine_similarity(a, b), cosine_similarity(a, c))

    def test_auto_mode_falls_back_to_projection_when_semantic_backend_is_projection_only(self) -> None:
        base = load_config("config/demo.yaml")
        with tempfile.TemporaryDirectory() as tmp_dir:
            config = replace(
                base,
                embedding_backend="stable-projection",
                vector_mode="auto",
                model_cache_dir=str(Path(tmp_dir) / "models"),
            )
            model = load_model(config)

        self.assertEqual(model.resolve_vector_mode(config.vector_mode), "stable_projection")

    def test_stable_projection_backend_leaves_semantic_embedding_empty(self) -> None:
        base = load_config("config/demo.yaml")
        with tempfile.TemporaryDirectory() as tmp_dir:
            config = replace(
                base,
                embedding_backend="stable-projection",
                vector_mode="auto",
                model_cache_dir=str(Path(tmp_dir) / "models"),
            )
            model = load_model(config)
            embeddings = model.embed("payments API latency is spiking again")

        self.assertIsNone(embeddings.semantic_embedding)
        self.assertTrue(embeddings.projection_embedding)
