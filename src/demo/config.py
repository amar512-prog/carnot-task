from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class DemoConfig:
    join_threshold: float
    draft_score_min: float
    draft_score_max: float
    merge_evidence_threshold: float
    semantic_floor: float
    time_decay_half_life_minutes: int
    max_reuse_age_minutes: int
    candidate_limit: int
    gate1_vector_mode: str
    reranker_model_id: str
    reranker_top_k: int
    judge_model_id: str
    judge_api_url: str
    judge_timeout_seconds: int
    draft_merge_window_minutes: int
    maintenance_interval_minutes: int
    embedding_dimension: int
    embedding_backend: str
    vector_mode: str
    embedding_model_id: str
    model_cache_dir: str
    baseline_story_path: str
    baseline_labels_path: str
    reports_dir: str

    @property
    def config_path(self) -> str:
        return os.environ.get("DEMO_CONFIG_PATH", "config/demo.yaml")


def _coerce_scalar(raw: str) -> Any:
    value = raw.strip()
    if not value:
        return ""
    if value.lower() in {"true", "false"}:
        return value.lower() == "true"
    try:
        if "." in value:
            return float(value)
        return int(value)
    except ValueError:
        return value.strip("'\"")


def _parse_simple_yaml(text: str) -> dict[str, Any]:
    data: dict[str, Any] = {}
    for raw_line in text.splitlines():
        line = raw_line.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        if ":" not in line:
            raise ValueError(f"Unsupported config line: {raw_line}")
        key, raw_value = line.split(":", 1)
        data[key.strip()] = _coerce_scalar(raw_value)
    return data


def load_config(path: str | None = None) -> DemoConfig:
    config_path = Path(path or os.environ.get("DEMO_CONFIG_PATH", "config/demo.yaml"))
    parsed = _parse_simple_yaml(config_path.read_text(encoding="utf-8"))
    return DemoConfig(**parsed)


def get_db_url() -> str:
    return os.environ.get("DEMO_DB_URL", "postgresql://demo:demo@127.0.0.1:5432/demo")


def get_api_url() -> str:
    return os.environ.get("DEMO_API_URL", "http://127.0.0.1:8000")
