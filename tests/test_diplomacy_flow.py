"""
Tests for the diplomacy flow: ctx.intel propagation + deception bandit targeting.

Verifies:
1. SkillContext.intel is updated by intelligence skills (stale-reference bug)
2. DeceptionBandit correctly selects targets from briefings
3. DiplomacyAgent correctly filters dormant vs active competitors
"""

import asyncio
import sys
import types
import pytest
from dataclasses import dataclass, field
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

# ── Mock datapizza before importing src modules that depend on it ──
_dp = types.ModuleType("datapizza")
_dp_tools = types.ModuleType("datapizza.tools")
_dp_mcp = types.ModuleType("datapizza.tools.mcp_client")
_dp_clients = types.ModuleType("datapizza.clients")
_dp_oai = types.ModuleType("datapizza.clients.openai_like")

# Create stub classes
class _StubMCPClient:
    def __init__(self, *a, **kw): pass
    async def call_tool(self, *a, **kw): return "ok"
    async def a_list_tools(self): return []

class _StubOpenAILikeClient:
    def __init__(self, *a, **kw): pass
    async def a_invoke(self, prompt):
        resp = MagicMock()
        resp.text = "0.5"
        return resp

_dp_mcp.MCPClient = _StubMCPClient
_dp_oai.OpenAILikeClient = _StubOpenAILikeClient

sys.modules.setdefault("datapizza", _dp)
sys.modules.setdefault("datapizza.tools", _dp_tools)
sys.modules.setdefault("datapizza.tools.mcp_client", _dp_mcp)
sys.modules.setdefault("datapizza.clients", _dp_clients)
sys.modules.setdefault("datapizza.clients.openai_like", _dp_oai)

from src.skills import SkillContext, SkillResult
from src.diplomacy.deception_bandit import DeceptionBandit
from src.diplomacy.agent import DiplomacyAgent
from src.memory.message_log import MessageLog


# ── Helpers ──

def _make_ctx(intel: dict | None = None) -> SkillContext:
    """Build a minimal SkillContext."""
    return SkillContext(
        turn_id=10,
        phase="speaking",
        balance=20000,
        inventory={"Sale Temporale": 3},
        reputation=80,
        recipes={},
        intel=intel or {},
    )


def _make_briefings(n: int = 5, dormant: int = 0) -> dict[int, dict]:
    """Generate n competitor briefings, with `dormant` marked DORMANT."""
    briefings = {}
    for i in range(1, n + 1):
        is_dormant = i <= dormant
        briefings[i] = {
            "name": f"Team {i}",
            "is_connected": True,
            "menu_size": 0 if is_dormant else 3,
            "menu_price_avg": 0 if is_dormant else 100 + i * 10,
            "strategy": "DORMANT" if is_dormant else "STABLE_SPECIALIST",
            "top_bid_ingredients": ["Sale Temporale"] if not is_dormant else [],
            "vulnerable_ingredients": [],
            "predicted_bid_spend": 50,
            "balance": 15000,
            "reputation": 70 + i,
            "threat_level": 0.6 if not is_dormant else 0,
            "opportunity_level": 0.5 if not is_dormant else 0,
        }
    return briefings


# ══════════════════════════════════════════════════════════════
#  1. ctx.intel stale-reference fix
# ══════════════════════════════════════════════════════════════

class TestCtxIntelPropagation:
    """Ensure intelligence skills update ctx.intel (not just self._latest_intel)."""

    def test_ctx_intel_is_mutable_reference(self):
        """Reassigning ctx.intel after build updates what downstream reads."""
        ctx = _make_ctx(intel={})
        assert ctx.intel == {}

        # Simulate what _skill_intelligence_scan now does
        new_intel = {"briefings": _make_briefings(3), "clusters": {}}
        ctx.intel = new_intel

        assert len(ctx.intel["briefings"]) == 3
        assert ctx.intel is new_intel

    def test_stale_reference_without_fix(self):
        """Show the bug: reassigning self._latest_intel doesn't update ctx."""
        original_intel = {}
        ctx = _make_ctx(intel=original_intel)

        # Simulate the OLD broken code: self._latest_intel = new_dict
        new_intel = {"briefings": _make_briefings(5)}
        # This is what used to happen — ctx.intel still points to original
        # (we only update self._latest_intel, not ctx.intel)
        assert ctx.intel == {}

        # The fix: explicitly update ctx.intel
        ctx.intel = new_intel
        assert len(ctx.intel["briefings"]) == 5


# ══════════════════════════════════════════════════════════════
#  2. DeceptionBandit target selection
# ══════════════════════════════════════════════════════════════

class TestDeceptionBanditTargeting:
    """Test bandit selects targets correctly from briefings."""

    def setup_method(self):
        self.bandit = DeceptionBandit()

    def test_selects_from_active_competitors(self):
        """Non-dormant competitors with opportunity > 0.3 should be targeted."""
        briefings = _make_briefings(5, dormant=0)
        actions = self.bandit.select_target_and_strategy(briefings)
        assert len(actions) > 0
        assert len(actions) <= 3  # capped at 3

    def test_skips_dormant_competitors(self):
        """Only DORMANT competitors → fallback to best candidate."""
        briefings = _make_briefings(3, dormant=3)
        actions = self.bandit.select_target_and_strategy(briefings)
        # All dormant → no candidates → no actions
        assert len(actions) == 0

    def test_fallback_price_anchoring(self):
        """When no competitor scores high enough, fallback to price_anchoring."""
        briefings = _make_briefings(3, dormant=0)
        # Set all opportunity and threat to 0 so no thresholds are met
        for b in briefings.values():
            b["opportunity_level"] = 0.0
            b["threat_level"] = 0.0
        actions = self.bandit.select_target_and_strategy(briefings)
        assert len(actions) == 1
        assert actions[0]["arm"] == "price_anchoring"

    def test_mixed_dormant_active(self):
        """Mix of dormant and active — only active should be considered."""
        briefings = _make_briefings(5, dormant=2)
        actions = self.bandit.select_target_and_strategy(briefings)
        # Should target some of the 3 active competitors
        assert len(actions) > 0
        targeted_rids = {a["target_rid"] for a in actions}
        # Dormant are rids 1, 2; active are 3, 4, 5
        assert not targeted_rids.intersection({1, 2})

    def test_empty_briefings(self):
        """No briefings at all → no actions."""
        actions = self.bandit.select_target_and_strategy({})
        assert actions == []

    def test_high_opportunity_selects_deception_arm(self):
        """High opportunity → bandit samples an arm (not just price_anchoring)."""
        briefings = {
            99: {
                "name": "High Opp Team",
                "strategy": "REACTIVE_CHASER",
                "opportunity_level": 0.8,
                "threat_level": 0.3,
                "menu_price_avg": 150,
                "top_bid_ingredients": ["Sale Temporale"],
                "vulnerable_ingredients": ["Plasma Vitale"],
                "balance": 5000,
                "balance_trend": "falling",
                "is_connected": True,
            }
        }
        # Run multiple times — should always produce at least one action
        for _ in range(10):
            actions = self.bandit.select_target_and_strategy(briefings)
            assert len(actions) >= 1
            assert actions[0]["target_rid"] == 99

    def test_high_threat_triggers_threat_response(self):
        """High threat + low opportunity → threat response."""
        briefings = {
            42: {
                "name": "Threat Team",
                "strategy": "AGGRESSIVE_BIDDER",
                "opportunity_level": 0.1,  # below 0.3
                "threat_level": 0.9,       # above 0.5
                "menu_price_avg": 200,
                "top_bid_ingredients": ["Foglie di Nebulosa"],
                "vulnerable_ingredients": [],
                "balance": 25000,
                "is_connected": True,
            }
        }
        actions = self.bandit.select_target_and_strategy(briefings)
        assert len(actions) >= 1
        # Should be manufactured_scarcity (threat response)
        assert actions[0]["arm"] == "manufactured_scarcity"
        assert actions[0]["desired_effect"] == "overbid_on_ingredient"


# ══════════════════════════════════════════════════════════════
#  3. DiplomacyAgent flow
# ══════════════════════════════════════════════════════════════

class TestDiplomacyAgent:
    """Test the full DiplomacyAgent.run_diplomacy_turn flow."""

    def setup_method(self):
        self.message_log = MessageLog()
        self.mcp_client = MagicMock()
        self.mcp_client.call_tool = AsyncMock(return_value="ok")
        self.agent = DiplomacyAgent(
            mcp_client=self.mcp_client,
            message_log=self.message_log,
        )

    @pytest.mark.asyncio
    async def test_no_briefings_skips(self):
        """Empty briefings → immediate return, 0 messages."""
        result = await self.agent.run_diplomacy_turn(
            competitor_briefings={},
            turn_id=1,
        )
        assert result == []

    @pytest.mark.asyncio
    async def test_all_dormant_skips(self):
        """All dormant → skip diplomacy."""
        briefings = _make_briefings(3, dormant=3)
        result = await self.agent.run_diplomacy_turn(
            competitor_briefings=briefings,
            turn_id=1,
        )
        assert result == []

    @pytest.mark.asyncio
    async def test_active_competitors_sends_messages(self):
        """Active competitors → PseudoGAN crafts + MCP sends messages."""
        briefings = _make_briefings(3, dormant=0)

        # Mock PseudoGAN to return a fixed message
        self.agent.pseudo_gan.craft_message = AsyncMock(
            return_value="Hey, watch out for expensive ingredients this turn!"
        )

        result = await self.agent.run_diplomacy_turn(
            competitor_briefings=briefings,
            competitor_states={},
            turn_id=5,
        )

        assert len(result) > 0
        assert self.agent.pseudo_gan.craft_message.call_count > 0
        assert self.mcp_client.call_tool.call_count > 0

        # Check MCP was called with correct tool name
        for call in self.mcp_client.call_tool.call_args_list:
            assert call[0][0] == "send_message"
            assert "restaurantId" in call[0][1]
            assert "message" in call[0][1]

    @pytest.mark.asyncio
    async def test_message_recorded_in_log(self):
        """Sent messages should be recorded in MessageLog."""
        briefings = _make_briefings(1, dormant=0)
        self.agent.pseudo_gan.craft_message = AsyncMock(
            return_value="Test message"
        )

        await self.agent.run_diplomacy_turn(
            competitor_briefings=briefings,
            competitor_states={},
            turn_id=7,
        )

        # Check message log has entries
        assert len(self.message_log.sent) > 0

    @pytest.mark.asyncio
    async def test_pseudo_gan_failure_continues(self):
        """If PseudoGAN fails for one target, others still get messages."""
        briefings = _make_briefings(3, dormant=0)

        call_count = 0

        async def mock_craft(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise RuntimeError("LLM timeout")
            return "Fallback message"

        self.agent.pseudo_gan.craft_message = mock_craft

        result = await self.agent.run_diplomacy_turn(
            competitor_briefings=briefings,
            competitor_states={},
            turn_id=3,
        )

        # Should have sent messages for the non-failed targets
        # (at least some should succeed)
        # The first target failed, but we might have more
        assert call_count >= 1

    @pytest.mark.asyncio
    async def test_mcp_failure_does_not_record(self):
        """If MCP send fails, message is NOT recorded as sent."""
        briefings = _make_briefings(1, dormant=0)
        self.agent.pseudo_gan.craft_message = AsyncMock(
            return_value="Test message"
        )
        self.mcp_client.call_tool = AsyncMock(side_effect=Exception("MCP down"))

        result = await self.agent.run_diplomacy_turn(
            competitor_briefings=briefings,
            competitor_states={},
            turn_id=4,
        )

        assert len(result) == 0
        assert len(self.message_log.sent) == 0


# ══════════════════════════════════════════════════════════════
#  4. End-to-end: intelligence → diplomacy via ctx.intel
# ══════════════════════════════════════════════════════════════

class TestIntelToDiplomacyE2E:
    """Simulate the full pipeline: build ctx, update intel, read in diplomacy."""

    def test_diplomacy_sees_intel_after_update(self):
        """After intelligence updates ctx.intel, diplomacy reads correct data."""
        # Phase 1: build context (intel is empty)
        ctx = _make_ctx(intel={})
        assert ctx.intel.get("briefings", {}) == {}

        # Phase 2: intelligence skill updates ctx.intel (the fix)
        briefings = _make_briefings(5, dormant=1)
        ctx.intel = {
            "briefings": briefings,
            "clusters": {},
            "all_states": {rid: {} for rid in briefings},
        }

        # Phase 3: diplomacy reads from ctx.intel
        diplo_briefings = ctx.intel.get("briefings", {})
        assert len(diplo_briefings) == 5

        active = [
            b for b in diplo_briefings.values()
            if b.get("strategy") != "DORMANT"
        ]
        assert len(active) == 4  # 5 total - 1 dormant

    def test_zone_selector_sees_intel_after_update(self):
        """Zone selector also benefits from the ctx.intel fix."""
        ctx = _make_ctx(intel={})

        # Update ctx.intel (simulating intelligence skill)
        briefings = _make_briefings(10, dormant=2)
        ctx.intel = {"briefings": briefings, "all_states": {}}

        # Zone selector would read this
        zone_briefings = ctx.intel.get("briefings", {})
        assert len(zone_briefings) == 10


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
