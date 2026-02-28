"""
Regression tests for the three fixes applied 2026-02-28:

Fix 1 — start_serving cancels stale tasks from a previous turn.
Fix 2 — _fetch_meals stops the polling loop on 400 "turn_id too old".
Fix 3 — _build_skill_context no longer uses hardcoded turn_id=1 fallback
         (validated here via the phase_router / pipeline guard).
"""

import asyncio
import collections
from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import pytest

from src.serving.pipeline import ServingPipeline, ServingMetrics


# ── Helpers ──────────────────────────────────────────────────────────────


def make_pipeline() -> ServingPipeline:
    from src.memory.client_profile import IntoleranceDetector, GlobalClientLibrary

    recipes = {
        "Piatto Test": {
            "name": "Piatto Test",
            "ingredients": {"Farina": 1},
            "prestige": 50,
            "preparationTimeMs": 3000,
        }
    }
    intol = IntoleranceDetector()
    lib = GlobalClientLibrary()
    mcp = MagicMock()
    mcp.call_tool = AsyncMock(return_value={"result": "ok"})
    pipeline = ServingPipeline(recipes, intol, lib, mcp_client=mcp)
    pipeline.set_menu([{"name": "Piatto Test", "price": 10}])
    return pipeline


# ── Fix 1: start_serving cancels stale tasks ─────────────────────────────


@pytest.mark.asyncio
async def test_start_serving_cancels_stale_poll_task():
    """
    Calling start_serving a second time (different turn) must cancel the
    poll task that was created during the first call, not leave a ghost loop.
    """
    pipeline = make_pipeline()
    await pipeline.start_serving(turn_id=1)

    old_poll_task = pipeline._poll_task
    assert old_poll_task is not None
    assert not old_poll_task.done()

    # Start a new turn — should cancel the old task
    await pipeline.start_serving(turn_id=2)

    assert old_poll_task.cancelled() or old_poll_task.done(), (
        "Stale poll task from turn 1 should have been cancelled by start_serving(2)"
    )
    assert pipeline.current_turn == 2

    await pipeline.stop_serving()


@pytest.mark.asyncio
async def test_start_serving_cancels_stale_timeout_task():
    """Same guarantee for the timeout watchdog task."""
    pipeline = make_pipeline()
    await pipeline.start_serving(turn_id=3)

    old_timeout_task = pipeline._timeout_task
    assert old_timeout_task is not None

    await pipeline.start_serving(turn_id=4)

    assert old_timeout_task.cancelled() or old_timeout_task.done(), (
        "Stale timeout task from turn 3 should have been cancelled by start_serving(4)"
    )

    await pipeline.stop_serving()


# ── Fix 2: _fetch_meals stops loop on 400 "turn_id too old" ──────────────


@pytest.mark.asyncio
async def test_fetch_meals_stops_loop_on_400_too_old():
    """
    When GET /meals returns 400 with 'turn_id too old', _serving_active must
    be set to False so the polling loop exits gracefully.
    """
    pipeline = make_pipeline()
    pipeline.current_turn = 1

    # Build a fake aiohttp response that returns 400 + the server error body
    fake_response = MagicMock()
    fake_response.status = 400
    fake_response.text = AsyncMock(
        return_value='{"message":"turn_id too old; only current and previous 2 turns are accessible"}'
    )
    fake_response.__aenter__ = AsyncMock(return_value=fake_response)
    fake_response.__aexit__ = AsyncMock(return_value=False)

    fake_session = MagicMock()
    fake_session.closed = False
    fake_session.get = MagicMock(return_value=fake_response)
    pipeline._session = fake_session

    pipeline._serving_active = True  # simulate active serving loop

    result = await pipeline._fetch_meals()

    assert result is None, "Should return None on 400"
    assert pipeline._serving_active is False, (
        "Polling loop must be stopped (_serving_active=False) after 400 'too old'"
    )


@pytest.mark.asyncio
async def test_fetch_meals_does_not_stop_loop_on_other_400():
    """
    A 400 for a reason other than 'too old' (e.g. bad restaurant_id) should
    return None but NOT kill the serving loop.
    """
    pipeline = make_pipeline()
    pipeline.current_turn = 5

    fake_response = MagicMock()
    fake_response.status = 400
    fake_response.text = AsyncMock(return_value='{"message":"invalid restaurant_id"}')
    fake_response.__aenter__ = AsyncMock(return_value=fake_response)
    fake_response.__aexit__ = AsyncMock(return_value=False)

    fake_session = MagicMock()
    fake_session.closed = False
    fake_session.get = MagicMock(return_value=fake_response)
    pipeline._session = fake_session

    pipeline._serving_active = True

    result = await pipeline._fetch_meals()

    assert result is None
    assert pipeline._serving_active is True, (
        "Loop should remain active for non-'too old' 400 errors"
    )


# ── Fix 3: start_serving with turn_id=0 skips polling ────────────────────


@pytest.mark.asyncio
async def test_start_serving_with_zero_turn_id_skips_poll():
    """
    If a bogus turn_id=0 somehow reaches start_serving, _fetch_meals must
    return None immediately (the guard 'if self.current_turn <= 0') instead
    of hitting the server with turn_id=0.
    """
    pipeline = make_pipeline()
    await pipeline.start_serving(turn_id=0)

    # Patch session to detect any real HTTP call
    fake_session = MagicMock()
    fake_session.closed = False
    fake_session.get = MagicMock(side_effect=AssertionError("Should not call GET /meals with turn_id=0"))
    fake_session.close = AsyncMock()
    pipeline._session = fake_session

    result = await pipeline._fetch_meals()

    assert result is None, "_fetch_meals should bail out without hitting the network"

    await pipeline.stop_serving()


@pytest.mark.asyncio
async def test_serving_loop_full_cycle_no_stale_tasks():
    """
    Integration: two consecutive turns must not accumulate ghost tasks.
    After turn 2 starts, only one poll task and one timeout task should exist.
    """
    pipeline = make_pipeline()

    await pipeline.start_serving(turn_id=1)
    t1_poll = pipeline._poll_task
    t1_timeout = pipeline._timeout_task

    await pipeline.start_serving(turn_id=2)
    t2_poll = pipeline._poll_task
    t2_timeout = pipeline._timeout_task

    # Old tasks must be gone
    assert t1_poll is not t2_poll
    assert t1_timeout is not t2_timeout
    assert t1_poll.cancelled() or t1_poll.done()
    assert t1_timeout.cancelled() or t1_timeout.done()

    # New tasks must be alive
    assert not t2_poll.done()
    assert not t2_timeout.done()

    await pipeline.stop_serving()
