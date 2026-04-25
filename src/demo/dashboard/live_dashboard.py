from __future__ import annotations

import json
import urllib.request
from typing import Any

from rich.console import Console, Group
from rich.live import Live
from rich.panel import Panel
from rich.table import Table


class LiveDashboard:
    def __init__(self) -> None:
        self.console = Console()
        self.active_clusters: dict[str, dict[str, Any]] = {}
        self.event_to_cluster: dict[str, str] = {}
        self.recent_stream: list[tuple[str, str]] = []
        self.recent_merges: list[str] = []
        self.last_reset_summary = "No resets observed yet."

    def watch(self, stream_url: str) -> None:
        request = urllib.request.Request(stream_url, headers={"Accept": "text/event-stream"})
        with Live(self._render(), console=self.console, refresh_per_second=4) as live:
            with urllib.request.urlopen(request) as response:  # noqa: S310 - local demo URL
                event_type = "message"
                for raw_line in response:
                    line = raw_line.decode("utf-8").strip()
                    if not line:
                        continue
                    if line.startswith("event:"):
                        event_type = line.split(":", 1)[1].strip()
                        continue
                    if not line.startswith("data:"):
                        continue
                    payload = json.loads(line.split(":", 1)[1].strip())
                    self.apply_event(event_type, payload)
                    live.update(self._render())

    def apply_event(self, event_type: str, payload: dict[str, Any]) -> None:
        if event_type == "heartbeat":
            return
        if event_type == "assignment":
            self._apply_assignment(payload)
        elif event_type == "merge":
            self._apply_merge(payload)
        elif event_type == "reset":
            self._apply_reset(payload)
        elif event_type == "maintenance":
            promoted = payload.get("promoted_drafts", 0)
            self._append_stream_entry("maintenance", f"promoted {promoted} draft clusters")
            return
        self._append_stream_entry(event_type, self._summarize_payload(event_type, payload))

    def _apply_assignment(self, payload: dict[str, Any]) -> None:
        event_id = str(payload.get("event_id", "unknown"))
        cluster_id = str(payload.get("cluster_id", "unknown"))
        cluster_status = str(payload.get("cluster_status", "unknown"))
        confidence = float(payload.get("confidence") or 0.0)
        previous_cluster = self.event_to_cluster.get(event_id)

        if previous_cluster and previous_cluster != cluster_id:
            self._decrement_cluster(previous_cluster)

        cluster_state = self.active_clusters.setdefault(
            cluster_id,
            {
                "status": cluster_status,
                "event_count": 0,
                "last_event_id": event_id,
                "last_confidence": confidence,
            },
        )
        if previous_cluster != cluster_id:
            cluster_state["event_count"] = int(cluster_state["event_count"]) + 1
        cluster_state["status"] = cluster_status
        cluster_state["last_event_id"] = event_id
        cluster_state["last_confidence"] = confidence
        self.event_to_cluster[event_id] = cluster_id

    def _apply_merge(self, payload: dict[str, Any]) -> None:
        winner_cluster_id = str(payload.get("winner_cluster_id", "unknown"))
        loser_cluster_id = str(payload.get("loser_cluster_id", "unknown"))
        evidence_score = float(payload.get("evidence_score") or 0.0)

        winner = self.active_clusters.setdefault(
            winner_cluster_id,
            {
                "status": "draft",
                "event_count": 0,
                "last_event_id": "-",
                "last_confidence": evidence_score,
            },
        )
        loser = self.active_clusters.pop(loser_cluster_id, None)
        if loser:
            winner["event_count"] = int(winner["event_count"]) + int(loser.get("event_count", 0))
        winner["last_confidence"] = evidence_score

        for event_id, cluster_id in list(self.event_to_cluster.items()):
            if cluster_id == loser_cluster_id:
                self.event_to_cluster[event_id] = winner_cluster_id

        self.recent_merges.append(
            f"{loser_cluster_id[:8]} -> {winner_cluster_id[:8]} (evidence={evidence_score:.2f})"
        )
        self.recent_merges = self.recent_merges[-5:]

    def _apply_reset(self, payload: dict[str, Any]) -> None:
        phase = payload.get("phase")
        if phase == "started":
            self.active_clusters.clear()
            self.event_to_cluster.clear()
            self.recent_merges.clear()
            self.recent_stream.clear()
            deleted_events = int(payload.get("deleted_events") or 0)
            deleted_clusters = int(payload.get("deleted_clusters") or 0)
            self.last_reset_summary = (
                f"Reset started: cleared {deleted_events} events / {deleted_clusters} clusters."
            )
            return

        restored_events = int(payload.get("restored_runtime_events") or 0)
        restored_clusters = int(payload.get("restored_runtime_clusters") or 0)
        self.last_reset_summary = (
            f"Reset completed: restored {restored_events} runtime events / {restored_clusters} clusters."
        )

    def _decrement_cluster(self, cluster_id: str) -> None:
        cluster_state = self.active_clusters.get(cluster_id)
        if cluster_state is None:
            return
        next_count = int(cluster_state["event_count"]) - 1
        if next_count <= 0:
            self.active_clusters.pop(cluster_id, None)
            return
        cluster_state["event_count"] = next_count

    def _append_stream_entry(self, event_type: str, summary: str) -> None:
        self.recent_stream.append((event_type.upper(), summary))
        self.recent_stream = self.recent_stream[-10:]

    def _summarize_payload(self, event_type: str, payload: dict[str, Any]) -> str:
        if event_type == "assignment":
            return (
                f"{payload.get('decision')} {payload.get('event_id')} -> "
                f"{str(payload.get('cluster_id', ''))[:8]} "
                f"(confidence={float(payload.get('confidence') or 0.0):.2f})"
            )
        if event_type == "merge":
            return (
                f"{str(payload.get('loser_cluster_id', ''))[:8]} -> "
                f"{str(payload.get('winner_cluster_id', ''))[:8]} "
                f"(evidence={float(payload.get('evidence_score') or 0.0):.2f})"
            )
        if event_type == "reset":
            phase = payload.get("phase", "completed")
            return f"phase={phase} rehydrate={payload.get('rehydrate_runtime')}"
        return json.dumps(payload, sort_keys=True)

    def _render(self):
        return Group(
            Panel(self._cluster_table(), title="Active Clusters", border_style="cyan"),
            Panel(self._merge_table(), title="Recent Merges", border_style="yellow"),
            Panel(self._stream_table(), title=f"Stream Log | {self.last_reset_summary}", border_style="green"),
        )

    def _cluster_table(self) -> Table:
        table = Table(expand=True)
        table.add_column("Cluster", style="cyan")
        table.add_column("Status", style="magenta")
        table.add_column("Events", justify="right")
        table.add_column("Last Event")
        table.add_column("Confidence", justify="right")
        if not self.active_clusters:
            table.add_row("-", "-", "0", "No active clusters yet", "-")
            return table
        rows = sorted(
            self.active_clusters.items(),
            key=lambda item: (-int(item[1]["event_count"]), item[0]),
        )
        for cluster_id, state in rows[:10]:
            table.add_row(
                cluster_id[:8],
                str(state.get("status", "unknown")),
                str(state.get("event_count", 0)),
                str(state.get("last_event_id", "-")),
                f"{float(state.get('last_confidence') or 0.0):.2f}",
            )
        return table

    def _merge_table(self) -> Table:
        table = Table(expand=True)
        table.add_column("Merge Summary", style="yellow")
        if not self.recent_merges:
            table.add_row("No merges observed yet")
            return table
        for entry in reversed(self.recent_merges):
            table.add_row(entry)
        return table

    def _stream_table(self) -> Table:
        table = Table(expand=True)
        table.add_column("Type", style="green", width=12)
        table.add_column("Summary")
        if not self.recent_stream:
            table.add_row("-", "Waiting for events...")
            return table
        for event_type, summary in reversed(self.recent_stream):
            table.add_row(event_type, summary)
        return table
