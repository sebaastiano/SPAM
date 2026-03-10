"""
SPAM! — Subagent Router
=========================
Routes strategy execution to zone-specific datapizza Agents.
Each zone has its own Agent with tailored system prompt.

Now ACTIVELY integrates agents into the decision flow:
- Strategic planning via StrategyAgent (LLM consultation)
- Zone-specific agents for tool-calling execution
- Agent recommendations influence ALL downstream decisions
"""

import logging

from datapizza.agents import Agent
from datapizza.clients.openai_like import OpenAILikeClient
from datapizza.tools.mcp_client import MCPClient

from src.config import (
    REGOLO_API_KEY,
    REGOLO_BASE_URL,
    PRIMARY_MODEL,
    FAST_MODEL,
    MCP_URL,
    HEADERS,
    ZONES,
    ZONE_SYSTEM_PROMPTS,
)
from src.decision.zone_selector import select_zone
from src.decision.strategy_agent import StrategyAgent, TurnStrategy

logger = logging.getLogger("spam.decision.subagent_router")


class SubagentRouter:
    """
    Routes strategy execution to zone-specific datapizza Agents.

    Each zone maps to a datapizza-ai Agent with zone-specific:
    - System prompt (target archetypes, pricing, risk tolerance)
    - MCP tools (same for all, but prompt constrains usage)

    NEW: Integrates StrategyAgent for LLM-driven strategic planning
    that actively influences zone selection, menu, bids, and pricing.
    """

    def __init__(self, mcp_tools: list | None = None, extra_tools: list | None = None):
        self.zones: dict[str, Agent] = {}
        self.active_zone: str = "DIVERSIFIED"
        self._mcp_tools = mcp_tools or []
        self._extra_tools = extra_tools or []
        self._initialized = False

        # Strategy agent for LLM-driven decisions
        self.strategy_agent: StrategyAgent | None = None
        self._current_strategy: TurnStrategy | None = None

    def initialize(self, mcp_tools: list | None = None):
        """Create agents for all zones AND the strategy agent."""
        if self._initialized:
            return

        if mcp_tools is not None:
            self._mcp_tools = mcp_tools

        all_tools = self._mcp_tools + self._extra_tools

        for zone in ZONES:
            prompt = ZONE_SYSTEM_PROMPTS.get(zone, "")
            client = OpenAILikeClient(
                api_key=REGOLO_API_KEY,
                model=PRIMARY_MODEL,
                base_url=REGOLO_BASE_URL,
                system_prompt=prompt,
            )
            agent = Agent(
                name=zone.lower(),
                client=client,
                tools=all_tools,
                max_steps=5,
                terminate_on_text=True,
                planning_interval=0,
            )
            self.zones[zone] = agent

        # Initialize strategy agent (uses LLM for reasoning, no tools)
        primary_client = OpenAILikeClient(
            api_key=REGOLO_API_KEY,
            model=PRIMARY_MODEL,
            base_url=REGOLO_BASE_URL,
            system_prompt=(
                "You are the strategic brain of restaurant SPAM! (Team 17). "
                "Analyze game state and make optimal strategic decisions. "
                "Always respond with valid JSON."
            ),
        )
        fast_client = OpenAILikeClient(
            api_key=REGOLO_API_KEY,
            model=FAST_MODEL,
            base_url=REGOLO_BASE_URL,
            system_prompt="Fast strategic analysis assistant. Respond with JSON.",
        )
        self.strategy_agent = StrategyAgent(
            llm_client=primary_client,
            fast_client=fast_client,
        )

        self._initialized = True
        logger.info(
            f"Initialized {len(self.zones)} zone agents + strategy agent"
        )

    def route(
        self,
        balance: float,
        inventory: dict,
        reputation: float,
        recipes: list[dict],
        competitor_clusters: dict,
        competitor_briefings: dict,
        all_states: dict | None = None,
        # ── vector-space inputs ──
        embeddings: dict | None = None,
        features: dict | None = None,
        demand_forecast: dict | None = None,
        trajectory_predictor=None,
    ) -> str:
        """
        Select the active zone for this turn.

        Uses algorithmic zone selector as base, then consults
        strategy agent for potential override.
        """
        # Algorithmic zone selection (heuristic baseline)
        algorithmic_zone = select_zone(
            balance=balance,
            inventory=inventory,
            reputation=reputation,
            recipes=recipes,
            competitor_clusters=competitor_clusters,
            competitor_briefings=competitor_briefings,
            all_states=all_states,
            embeddings=embeddings,
            features=features,
            demand_forecast=demand_forecast,
            trajectory_predictor=trajectory_predictor,
        )

        # If strategy agent has a recommendation with sufficient confidence,
        # prefer it over the algorithmic choice
        if self._current_strategy and self._current_strategy.confidence >= 0.5:
            agent_zone = self._current_strategy.recommended_zone
            if agent_zone != algorithmic_zone:
                logger.info(
                    f"Strategy agent overrides zone: "
                    f"{algorithmic_zone} → {agent_zone} "
                    f"(confidence={self._current_strategy.confidence:.2f})"
                )
                self.active_zone = agent_zone
                return agent_zone

        self.active_zone = algorithmic_zone
        logger.info(f"Active zone: {self.active_zone}")
        return self.active_zone

    async def run_strategic_plan(self, **kwargs) -> TurnStrategy:
        """
        Run the strategy agent to produce a turn-level plan.

        This is called early in the speaking phase and influences
        all downstream decisions (zone, menu, bids, pricing, diplomacy).
        """
        if not self.strategy_agent:
            logger.warning("Strategy agent not initialized — using defaults")
            self._current_strategy = TurnStrategy()
            return self._current_strategy

        strategy = await self.strategy_agent.plan_turn(**kwargs)
        self._current_strategy = strategy
        return strategy

    def get_current_strategy(self) -> TurnStrategy | None:
        """Get the current turn's strategy (set by run_strategic_plan)."""
        return self._current_strategy

    def get_active_agent(self) -> Agent | None:
        """Get the active zone's agent."""
        return self.zones.get(self.active_zone)

    def get_agent(self, zone: str) -> Agent | None:
        """Get a specific zone's agent."""
        return self.zones.get(zone)
