"""
SPAM! — Client Priority Queue
===============================
Priority queue for incoming clients during serving phase.
Astrobaroni first, then Saggi, then Famiglie, then Esploratori.
"""

import heapq
import logging
from dataclasses import dataclass, field
from typing import Any

from src.config import ARCHETYPE_PRIORITY, KNOWN_ARCHETYPES

logger = logging.getLogger("spam.serving.priority_queue")


def classify_archetype(client_name: str) -> str:
    """
    Map clientName to a known archetype.

    IMPORTANT: No source confirms that clientName values map directly
    to the 4 archetype names. We must handle unknown values gracefully.
    """
    if client_name in KNOWN_ARCHETYPES:
        return client_name
    # Fuzzy fallback: check if archetype name is a substring
    client_lower = client_name.lower()
    for arch in KNOWN_ARCHETYPES:
        if arch.lower() in client_lower or client_lower in arch.lower():
            return arch
    return "unknown"


@dataclass(order=True)
class PrioritizedClient:
    """Wrapper for priority queue ordering."""
    priority: int
    sequence: int  # tie-breaker (FIFO within same priority)
    data: dict = field(compare=False)


class ClientPriorityQueue:
    """
    Priority queue for incoming clients during serving phase.

    Priority order (lower = higher priority):
      0: Astrobarone (highest revenue, least time tolerance)
      1: Saggi del Cosmo (quality-focused, patient)
      2: Famiglie Orbitali (balanced)
      3: Esploratore Galattico (budget, fast dishes)
      99: Unknown archetype (lowest priority)
    """

    def __init__(self):
        self._heap: list[PrioritizedClient] = []
        self._sequence = 0
        self._size = 0

    def add_client(self, client_data: dict):
        """
        Add a client to the priority queue.

        client_data should contain at minimum:
          - clientName: str
          - orderText: str
        """
        archetype = classify_archetype(client_data.get("clientName", "unknown"))
        priority = ARCHETYPE_PRIORITY.get(archetype, 99)

        entry = PrioritizedClient(
            priority=priority,
            sequence=self._sequence,
            data={**client_data, "_archetype": archetype},
        )
        heapq.heappush(self._heap, entry)
        self._sequence += 1
        self._size += 1

        logger.debug(
            f"Queued client: {client_data.get('clientName')} "
            f"(archetype={archetype}, priority={priority})"
        )

    def next_client(self) -> dict | None:
        """Pop the highest-priority client."""
        while self._heap:
            entry = heapq.heappop(self._heap)
            self._size -= 1
            return entry.data
        return None

    def peek(self) -> dict | None:
        """Look at the highest-priority client without removing."""
        if self._heap:
            return self._heap[0].data
        return None

    def __len__(self) -> int:
        return self._size

    def is_empty(self) -> bool:
        return self._size == 0

    def clear(self):
        """Clear the queue (e.g., at end of serving phase)."""
        self._heap.clear()
        self._size = 0
        self._sequence = 0
