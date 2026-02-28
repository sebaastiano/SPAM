"""
JSONL append-only event log for full game replay.
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Any


class EventLog:
    """Append-only JSONL event log. Every SSE event, GET response, and
    MCP call is recorded here for debugging and replay."""

    def __init__(self, filepath: str = "game_events.jsonl"):
        self.filepath = filepath
        # Ensure directory exists
        os.makedirs(os.path.dirname(filepath) or ".", exist_ok=True)

    def log(
        self,
        event_type: str,
        data: dict[str, Any],
        trust_level: str = "server",
    ) -> None:
        entry = {
            "ts": datetime.now().isoformat(),
            "type": event_type,
            "trust": trust_level,
            "data": data,
        }
        with open(self.filepath, "a") as f:
            f.write(json.dumps(entry, default=str) + "\n")

    def replay(self, event_type: str | None = None) -> list[dict]:
        """Replay events, optionally filtered by type."""
        events: list[dict] = []
        if not os.path.exists(self.filepath):
            return events
        with open(self.filepath, "r") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                entry = json.loads(line)
                if event_type is None or entry["type"] == event_type:
                    events.append(entry)
        return events

    def clear(self) -> None:
        """Truncate the log (use only on game_reset)."""
        with open(self.filepath, "w"):
            pass
