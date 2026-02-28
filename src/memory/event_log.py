"""
SPAM! — Event Log
==================
Append-only JSONL event log for full game replay and debugging.
"""

import json
import logging
from datetime import datetime, timezone

logger = logging.getLogger("spam.memory.event_log")


class EventLog:
    """
    Append-only JSONL event log for full game replay.

    Every SSE event, GET response, and MCP call is logged with
    timestamp and trust level for post-game analysis.
    """

    def __init__(self, filepath: str = "game_events.jsonl"):
        self.filepath = filepath

    def log(self, event_type: str, data: dict, trust_level: str = "server"):
        """Append a single event to the JSONL log."""
        entry = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "type": event_type,
            "trust": trust_level,
            "data": data,
        }
        try:
            with open(self.filepath, "a") as f:
                f.write(json.dumps(entry, default=str) + "\n")
        except Exception as e:
            logger.error(f"EventLog write error: {e}")

    def replay(self, event_type: str | None = None) -> list[dict]:
        """Replay events, optionally filtered by type."""
        events = []
        try:
            with open(self.filepath, "r") as f:
                for line in f:
                    if not line.strip():
                        continue
                    entry = json.loads(line)
                    if event_type is None or entry["type"] == event_type:
                        events.append(entry)
        except FileNotFoundError:
            pass
        return events

    def clear(self):
        """Clear the log (used on game_reset if desired)."""
        try:
            open(self.filepath, "w").close()
        except Exception:
            pass


async def event_log_middleware(event_type: str, data: dict) -> dict:
    """
    EventBus middleware that logs all events to JSONL.
    Attach to ReactiveEventBus via bus.use(event_log_middleware).
    """
    _global_log.log(event_type, data, trust_level="server")
    return data


# Module-level singleton (set by main.py)
_global_log = EventLog()


def set_global_log(log: EventLog):
    global _global_log
    _global_log = log
