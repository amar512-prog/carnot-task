from __future__ import annotations


REPLAY_MAINTENANCE_LOCK_KEY = 442001


class RuntimeStateRepository:
    def __init__(self, conn):
        self.conn = conn

    def acquire_replay_maintenance_lock(self) -> None:
        with self.conn.cursor() as cur:
            cur.execute("SELECT pg_advisory_xact_lock(%s)", (REPLAY_MAINTENANCE_LOCK_KEY,))

    def get_bool_flag(self, key: str, default: bool = False) -> bool:
        with self.conn.cursor() as cur:
            cur.execute(
                """
                SELECT bool_value
                FROM runtime_state
                WHERE key = %s
                """,
                (key,),
            )
            row = cur.fetchone()
        if row is None or row["bool_value"] is None:
            return default
        return bool(row["bool_value"])

    def set_bool_flag(self, key: str, value: bool) -> None:
        with self.conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO runtime_state (key, bool_value)
                VALUES (%s, %s)
                ON CONFLICT (key) DO UPDATE
                SET bool_value = EXCLUDED.bool_value,
                    updated_at = now()
                """,
                (key, value),
            )
