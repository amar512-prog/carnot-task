from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from demo.domain.models import EventInput


TOKEN_RE = re.compile(r"[a-z0-9]+")


def normalize_text(text: str) -> str:
    return " ".join(TOKEN_RE.findall(text.lower()))


def tokenize(text: str) -> list[str]:
    normalized = normalize_text(text)
    if not normalized:
        return []
    return normalized.split()


def fingerprint(text: str) -> str:
    normalized = normalize_text(text)
    digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
    return digest


def top_keywords(texts: list[str], limit: int = 5) -> list[str]:
    counter: Counter[str] = Counter()
    for text in texts:
        counter.update(tokenize(text))
    stop_words = {"the", "a", "an", "is", "are", "in", "for", "and", "to", "of", "on"}
    for word in list(counter):
        if word in stop_words or len(word) < 3:
            del counter[word]
    return [word for word, _ in counter.most_common(limit)]


def read_jsonl(path: str | Path) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    with Path(path).open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            items.append(json.loads(line))
    return items


def load_story_events(path: str | Path) -> list[EventInput]:
    events: list[EventInput] = []
    for item in read_jsonl(path):
        events.append(
            EventInput(
                event_id=item["event_id"],
                source=item["source"],
                occurred_at=_parse_datetime(item["occurred_at"]),
                text=item["text"],
                metadata=item.get("metadata", {}),
            )
        )
    return events


def load_labels(path: str | Path) -> dict[str, str]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return data.get("labels", {})


def rebase_story_events(
    events: list[EventInput],
    *,
    end_at: datetime,
    window_minutes: int,
) -> list[EventInput]:
    if not events:
        return []

    ordered = list(events)
    if end_at.tzinfo is None:
        end_at = end_at.replace(tzinfo=timezone.utc)
    else:
        end_at = end_at.astimezone(timezone.utc)

    first_at = ordered[0].occurred_at
    offsets = [(event.occurred_at - first_at).total_seconds() for event in ordered]
    original_span_seconds = max(offsets) if offsets else 0.0
    target_span_seconds = max(0.0, float(window_minutes * 60))
    if original_span_seconds <= 0:
        scale = 0.0
        start_at = end_at
    else:
        scale = min(1.0, target_span_seconds / original_span_seconds)
        start_at = end_at - timedelta(seconds=original_span_seconds * scale)

    rebased: list[EventInput] = []
    for event, offset in zip(ordered, offsets):
        occurred_at = start_at + timedelta(seconds=offset * scale)
        metadata = dict(event.metadata)
        metadata["original_occurred_at"] = event.occurred_at.astimezone(timezone.utc).isoformat()
        metadata["rebased_for_demo"] = True
        rebased.append(
            replace(
                event,
                occurred_at=occurred_at,
                metadata=metadata,
            )
        )
    return rebased


def _parse_datetime(raw: str):
    return datetime.fromisoformat(raw.replace("Z", "+00:00"))
