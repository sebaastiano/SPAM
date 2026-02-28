"""
Client priority queue — archetype-based serving order.

Astrobarone first → Saggi del Cosmo → Famiglie Orbitali → Esploratore Galattico.
"""

from __future__ import annotations

import heapq
from typing import Any

from src.config import ARCHETYPE_PRIORITY, KNOWN_ARCHETYPES


def classify_archetype(client_name: str) -> str:
    """Map ``clientName`` from SSE to a known archetype.

    Falls back gracefully for unexpected values.
    """
    if client_name in KNOWN_ARCHETYPES:
        return client_name
    lower = client_name.lower()
    for arch in KNOWN_ARCHETYPES:
        if arch.lower() in lower or lower in arch.lower():
            return arch
    return "unknown"


class ClientPriorityQueue:
    """Priority queue for incoming clients during serving phase.

    Lower number = higher priority = served first.
    """

    def __init__(self) -> None:
        self._heap: list[tuple[int, int, dict]] = []
        self._counter = 0  # tiebreaker for equal priorities

    def add(self, client_data: dict[str, Any]) -> None:
        archetype = classify_archetype(client_data.get("clientName", ""))
        priority = ARCHETYPE_PRIORITY.get(archetype, 99)
        heapq.heappush(self._heap, (priority, self._counter, client_data))
        self._counter += 1

    def pop(self) -> dict[str, Any] | None:
        if self._heap:
            _, _, data = heapq.heappop(self._heap)
            return data
        return None

    def __len__(self) -> int:
        return len(self._heap)

    def clear(self) -> None:
        self._heap.clear()
        self._counter = 0
