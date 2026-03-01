"""Quick integration test for X-Ray."""
import asyncio
from src.xray import xray


async def test():
    # Test emitting events (no server needed)
    xray.phase("speaking", turn_id=3)
    xray.skill("intelligence_scan", status="running")
    xray.skill("intelligence_scan", status="success", duration_ms=1234.5, briefings=5)
    xray.decision("zone_selection", choice="PREMIUM_MONOPOLIST", reason="No competitors detected")
    xray.intelligence("pipeline_complete", briefing_count=4, connected_competitors=2)
    xray.diplomacy("message_sent", target="Team 5", strategy="manufactured_scarcity")
    xray.serving("client_spawned", client_name="Astrobarone_42")
    xray.update_game_state(balance=15000, reputation=72.5, zone="PREMIUM_MONOPOLIST")
    xray.warning("inventory_low", message="Only 3 ingredients left")

    # Test span
    import time
    with xray.span("test_operation", category="test"):
        time.sleep(0.01)

    # Check buffer
    snap = xray.get_snapshot()
    print(f"Turn: {snap['turn_id']}, Phase: {snap['phase']}")
    print(f"Events buffered: {len(snap['recent_events'])}")
    print(f"Game state keys: {list(snap['game_state'].keys())}")
    print(f"Skill states: {list(snap['skill_states'].keys())}")

    history = xray.get_history(limit=5)
    for evt in history:
        print(f"  [{evt['category']}] {evt['name']} ({evt['status']})")

    # Test dashboard server startup
    await xray.start(port=8777)
    print(f"\nDashboard server started on port 8777")

    # Give it a moment, then check it serves the page
    import aiohttp
    async with aiohttp.ClientSession() as session:
        async with session.get("http://localhost:8777/") as resp:
            print(f"Dashboard HTTP status: {resp.status}")
            text = await resp.text()
            assert "X-Ray" in text, "Dashboard HTML should contain X-Ray"
            print(f"Dashboard HTML length: {len(text)} chars")

        async with session.get("http://localhost:8777/api/snapshot") as resp:
            print(f"Snapshot API status: {resp.status}")
            data = await resp.json()
            print(f"Snapshot turn_id: {data['turn_id']}, events: {len(data['recent_events'])}")

    print("\nAll tests passed!")


asyncio.run(test())
