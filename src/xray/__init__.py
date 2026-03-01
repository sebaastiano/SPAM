"""
SPAM! X-Ray — Explainability Framework
========================================
Real-time visual dashboard for understanding agent internals.

Usage (from main.py or anywhere):
    from src.xray import xray

    # Start the dashboard server (call once at startup)
    await xray.start(port=8777)

    # Emit structured trace events from anywhere
    xray.phase("speaking", turn_id=3)
    xray.skill("intelligence_scan", status="running")
    xray.decision("zone_selection", choice="PREMIUM_MONOPOLIST", reason="...")
    xray.event("client_spawned", {...})

    # Context-manager spans for timed operations
    with xray.span("ilp_solver"):
        ...  # automatically records duration

    # Decorator for tracing skill functions
    @xray.traced
    async def my_skill(ctx):
        ...
"""

from src.xray.collector import XRayCollector

# Global singleton — importable from anywhere
xray = XRayCollector()

__all__ = ["xray"]
