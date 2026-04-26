from __future__ import annotations

import time
from pathlib import Path

import psycopg
from psycopg.rows import dict_row

from demo.config import get_db_url


def connect_db():
    return psycopg.connect(get_db_url(), row_factory=dict_row)


def ensure_schema() -> None:
    init_sql = Path("sql/init.sql").read_text(encoding="utf-8")
    with connect_db() as conn:
        from demo.repositories.runtime_state_repository import RuntimeStateRepository
        RuntimeStateRepository(conn).acquire_replay_maintenance_lock()
        with conn.cursor() as cur:
            cur.execute(init_sql)
        conn.commit()


def wait_for_db(retries: int = 30, delay_seconds: float = 1.0) -> None:
    last_error: Exception | None = None
    for _ in range(retries):
        try:
            ensure_schema()
            return
        except Exception as exc:  # pragma: no cover - best effort startup
            last_error = exc
            time.sleep(delay_seconds)
    if last_error is not None:
        raise last_error


def vector_literal(values: list[float]) -> str:
    return "[" + ",".join(f"{value:.8f}" for value in values) + "]"


def parse_vector(raw: str | list[float]) -> list[float]:
    if isinstance(raw, list):
        return [float(item) for item in raw]
    raw = raw.strip().removeprefix("[").removesuffix("]")
    if not raw:
        return []
    return [float(item) for item in raw.split(",")]

