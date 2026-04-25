from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from demo.config import load_config


class ConfigTest(unittest.TestCase):
    def test_load_config_reads_thresholds(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            config_path = Path(tmp_dir) / "demo.yaml"
            config_path.write_text(
                "\n".join(
                    [
                        "join_threshold: 0.70",
                        "draft_score_min: 0.60",
                        "draft_score_max: 0.70",
                        "merge_evidence_threshold: 0.85",
                        "semantic_floor: 0.55",
                        "time_decay_half_life_minutes: 60",
                        "max_reuse_age_minutes: 180",
                        "candidate_limit: 30",
                        "gate1_vector_mode: stable_projection",
                        "reranker_model_id: cross-encoder/ms-marco-MiniLM-L6-v2",
                        "reranker_top_k: 2",
                        "judge_model_id: qwen3:4b",
                        "judge_api_url: http://host.docker.internal:11434",
                        "judge_timeout_seconds: 30",
                        "draft_merge_window_minutes: 15",
                        "maintenance_interval_minutes: 5",
                        "embedding_dimension: 64",
                        "embedding_backend: stable-projection",
                        "vector_mode: stable_projection",
                        "embedding_model_id: codefuse-ai/F2LLM-v2-0.6B",
                        "model_cache_dir: .cache/models",
                        "baseline_story_path: data/story.jsonl",
                        "baseline_labels_path: data/story.labels.json",
                        "reports_dir: reports",
                    ]
                ),
                encoding="utf-8",
            )
            config = load_config(str(config_path))
        self.assertEqual(config.join_threshold, 0.70)
        self.assertEqual(config.draft_score_min, 0.60)
        self.assertEqual(config.embedding_dimension, 64)
        self.assertEqual(config.embedding_backend, "stable-projection")
        self.assertEqual(config.vector_mode, "stable_projection")
        self.assertEqual(config.gate1_vector_mode, "stable_projection")
        self.assertEqual(config.reranker_top_k, 2)
        self.assertEqual(config.judge_model_id, "qwen3:4b")
        self.assertEqual(config.baseline_story_path, "data/story.jsonl")
