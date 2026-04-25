from __future__ import annotations

import unittest
from datetime import datetime, timezone

from demo.domain.models import EventInput
from demo.domain.text_utils import rebase_story_events


class StoryRebaseTest(unittest.TestCase):
    def test_rebase_compresses_long_story_into_window(self) -> None:
        events = [
            EventInput(
                event_id="e1",
                source="log",
                occurred_at=datetime(2026, 4, 18, 8, 0, tzinfo=timezone.utc),
                text="first",
            ),
            EventInput(
                event_id="e2",
                source="log",
                occurred_at=datetime(2026, 4, 21, 8, 0, tzinfo=timezone.utc),
                text="second",
            ),
            EventInput(
                event_id="e3",
                source="log",
                occurred_at=datetime(2026, 4, 25, 8, 0, tzinfo=timezone.utc),
                text="third",
            ),
        ]

        rebased = rebase_story_events(
            events,
            end_at=datetime(2026, 4, 25, 12, 0, tzinfo=timezone.utc),
            window_minutes=15,
        )

        self.assertEqual([event.event_id for event in rebased], ["e1", "e2", "e3"])
        self.assertEqual(rebased[-1].occurred_at, datetime(2026, 4, 25, 12, 0, tzinfo=timezone.utc))
        self.assertEqual(rebased[0].occurred_at, datetime(2026, 4, 25, 11, 45, tzinfo=timezone.utc))
        self.assertTrue(
            rebased[0].occurred_at < rebased[1].occurred_at < rebased[2].occurred_at
        )
        self.assertEqual(
            rebased[1].metadata["original_occurred_at"],
            "2026-04-21T08:00:00+00:00",
        )
        self.assertTrue(rebased[1].metadata["rebased_for_demo"])

    def test_rebase_preserves_short_story_span(self) -> None:
        events = [
            EventInput(
                event_id="e1",
                source="query",
                occurred_at=datetime(2026, 4, 25, 11, 50, tzinfo=timezone.utc),
                text="first",
            ),
            EventInput(
                event_id="e2",
                source="query",
                occurred_at=datetime(2026, 4, 25, 11, 55, tzinfo=timezone.utc),
                text="second",
            ),
            EventInput(
                event_id="e3",
                source="query",
                occurred_at=datetime(2026, 4, 25, 12, 0, tzinfo=timezone.utc),
                text="third",
            ),
        ]

        rebased = rebase_story_events(
            events,
            end_at=datetime(2026, 4, 25, 13, 0, tzinfo=timezone.utc),
            window_minutes=15,
        )

        self.assertEqual(rebased[0].occurred_at, datetime(2026, 4, 25, 12, 50, tzinfo=timezone.utc))
        self.assertEqual(rebased[1].occurred_at, datetime(2026, 4, 25, 12, 55, tzinfo=timezone.utc))
        self.assertEqual(rebased[2].occurred_at, datetime(2026, 4, 25, 13, 0, tzinfo=timezone.utc))
