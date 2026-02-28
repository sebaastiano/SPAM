"""
SPAM! — Subagent Router
=========================
Routes strategy execution to zone-specific datapizza Agents.
Each zone has its own Agent with tailored system prompt.
"""

import logging

from datapizza.agents import Agent
from datapizza.clients.openai_like import OpenAILikeClient
from datapizza.tools.mcp_client import MCPClient

from src.config import (
    REGOLO_API_KEY,
    REGOLO_BASE_URL,
    PRIMARY_MODEL,
    MCP_URL,
    HEADERS,
    ZONES,
    ZONE_SYSTEM_PROMPTS,
)
from src.decision.zone_selector import select_zone

logger = logging.getLogger("spam.decision.subagent_router")


class SubagentRouter:
    """
    Routes strategy execution to zone-specific datapizza Agents.

    Each zone maps to a datapizza-ai Agent with zone-specific:
    - System prompt (target archetypes, pricing, risk tolerance)
    - MCP tools (same for all, but prompt constrains usage)
    """

    def __init__(self, mcp_tools: list = None, extra_tools: list = None):
        self.zones: dict[str, Agent] = {}
        self.active_zone: str = "SPEED_CONTENDER"
        self._mcp_tools = mcp_tools or []
        self._extra_tools = extra_tools or []
        self._initialized = False

    def initialize(self, mcp_tools: list = None):
        """Create agents for all zones."""
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

        self._initialized = True
        logger.info(f"Initialized {len(self.zones)} zone agents")

    def route(
        self,
        balance: float,
        inventory: dict,
        reputation: float,
        recipes: list[dict],
        competitor_clusters: dict,
        competitor_briefings: dict,
    ) -> str:
        """
        Select the active zone for this turn using ILP zone classification.

        Returns the zone name.
        """
        self.active_zone = select_zone(
            balance=balance,
            inventory=inventory,
            reputation=reputation,
            recipes=recipes,
            competitor_clusters=competitor_clusters,
            competitor_briefings=competitor_briefings,
        )
        logger.info(f"Active zone: {self.active_zone}")
        return self.active_zone

    def get_active_agent(self) -> Agent | None:
        """Get the active zone's agent."""
        return self.zones.get(self.active_zone)

    def get_agent(self, zone: str) -> Agent | None:
        """Get a specific zone's agent."""
        return self.zones.get(zone)
