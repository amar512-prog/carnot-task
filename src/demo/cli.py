from __future__ import annotations

from dataclasses import replace
import json
import sys
import urllib.error
import urllib.request
import uuid
from datetime import datetime, timezone
from pathlib import Path

import typer
from rich.console import Console

from demo.calibration.threshold_calibrator import ThresholdCalibrator
from demo.config import get_api_url, load_config
from demo.dashboard.live_dashboard import LiveDashboard
from demo.domain.text_utils import load_story_events, rebase_story_events
from demo.embeddings.model_cache import load_model
from demo.repositories.database import connect_db, wait_for_db
from demo.repositories.runtime_state_repository import RuntimeStateRepository
from demo.services.reset_service import ResetService


app = typer.Typer(help="Recent-event clustering demo CLI")
console = Console()


def _post_json(url: str, payload: dict) -> dict:
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request) as response:  # noqa: S310 - demo-local URL
        return json.loads(response.read().decode("utf-8"))


@app.command()
def replay(
    story_path: str | None = typer.Option(None, "--story-path", help="Replay an alternate JSONL story file."),
    rebase_now: bool = typer.Option(
        False,
        "--rebase-now",
        help="Compress the story into the recent draft-merge window while preserving event order.",
    ),
) -> None:
    """Replay the configured story through the API."""
    config = load_config()
    wait_for_db()
    selected_story_path = story_path or config.baseline_story_path
    story = load_story_events(selected_story_path)
    if rebase_now:
        story = rebase_story_events(
            story,
            end_at=datetime.now(timezone.utc),
            window_minutes=config.draft_merge_window_minutes,
        )
    persist_baseline = story_path is None
    _set_replay_flag(True)
    try:
        ResetService(config).reset_with_story(
            story,
            rehydrate_runtime=False,
            persist_baseline=persist_baseline,
        )
        api_url = get_api_url().rstrip("/")
        for event in story:
            payload = {
                "event_id": event.event_id,
                "source": event.source,
                "occurred_at": event.occurred_at.isoformat(),
                "text": event.text,
                "metadata": event.metadata,
            }
            response = _post_json(f"{api_url}/events", payload)
            console.print(
                f"[green]{response['decision']}[/green] "
                f"{event.event_id} -> {response['cluster_id']} "
                f"(confidence={response['confidence']:.2f})"
            )
    finally:
        _set_replay_flag(False)


@app.command()
def send(text: str, source: str = "manual") -> None:
    """Send a single live event through the API."""
    payload = {
        "event_id": f"manual-{uuid.uuid4()}",
        "source": source,
        "occurred_at": datetime.now(timezone.utc).isoformat(),
        "text": text,
        "metadata": {"manual": True},
    }
    response = _post_json(f"{get_api_url().rstrip('/')}/events", payload)
    console.print_json(data=response)


@app.command()
def watch() -> None:
    """Watch the SSE decision stream in the terminal."""
    LiveDashboard().watch(f"{get_api_url().rstrip('/')}/events/stream")


@app.command()
def reset() -> None:
    """Wipe runtime DB state and restore the baseline story."""
    config = load_config()
    wait_for_db()
    summary = ResetService(config).reset_to_baseline()
    console.print_json(data=summary)


@app.command()
def calibrate(
    story_path: str | None = typer.Option(None, "--story-path", help="Override the JSONL story used for calibration."),
    labels_path: str | None = typer.Option(None, "--labels-path", help="Override the truth-label JSON file."),
) -> None:
    """Sweep thresholds against the labeled replay story."""
    config = load_config()
    if story_path:
        config = replace(config, baseline_story_path=story_path)
    if labels_path:
        config = replace(config, baseline_labels_path=labels_path)
    model = load_model(config)
    report = ThresholdCalibrator(config=config, model=model).run()
    console.print_json(data=report)
    console.print(f"[cyan]Wrote reports to[/cyan] {Path(config.reports_dir).resolve()}")


def main() -> None:
    try:
        app()
    except urllib.error.URLError as exc:  # pragma: no cover - operator-facing path
        print(f"Network/API error: {exc}", file=sys.stderr)
        raise typer.Exit(code=1) from exc


def _set_replay_flag(value: bool) -> None:
    with connect_db() as conn:
        RuntimeStateRepository(conn).set_bool_flag("replay_in_progress", value)
        conn.commit()


if __name__ == "__main__":
    main()
