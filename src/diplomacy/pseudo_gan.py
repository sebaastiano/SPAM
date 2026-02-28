"""
PseudoGAN — two-LLM message crafting (generator + discriminator).
"""

from __future__ import annotations

import logging
from typing import Any

log = logging.getLogger(__name__)


class PseudoGAN:
    """Generator (gpt-oss-120b) crafts a diplomatic message; discriminator
    (gpt-oss-20b) scores whether a rival LLM would believe it.

    Not a real GAN; just iterative refinement.
    """

    def __init__(
        self,
        generator_client: Any,   # OpenAILikeClient (gpt-oss-120b)
        discriminator_client: Any,  # OpenAILikeClient (gpt-oss-20b)
    ) -> None:
        self.generator = generator_client
        self.discriminator = discriminator_client

    async def craft_message(
        self,
        deception_action: dict[str, Any],
        competitor_briefing: dict[str, Any],
        max_iterations: int = 2,
    ) -> str:
        """Craft a deceptive message using iterative refinement."""
        target_name = deception_action.get("target_name", "")
        arm = deception_action.get("arm", "")
        desired = deception_action.get("desired_effect", "")
        hint = deception_action.get("message_hint", "")

        tracker_ctx = (
            f"Target: {target_name} (strategy: {competitor_briefing.get('strategy', '?')})\n"
            f"Balance: {competitor_briefing.get('balance', 0):.0f} ({competitor_briefing.get('balance_trend', '?')})\n"
            f"Avg menu price: {competitor_briefing.get('menu_price_avg', 0):.0f}\n"
            f"Top bid ingredients: {', '.join(competitor_briefing.get('top_bid_ingredients', [])[:3])}\n"
            f"Reputation: {competitor_briefing.get('reputation', 0)}"
        )

        best_msg: str | None = None
        best_score = 0.0

        for i in range(max_iterations):
            gen_prompt = (
                f"You are a restaurant manager in a competitive cooking game.\n"
                f"Send a message to \"{target_name}\" to achieve: {desired}\n"
                f"Deception approach: {arm}\nHint: {hint}\n\n"
                f"Intel:\n{tracker_ctx}\n\n"
                f"{'Previous attempt scored ' + str(best_score) + '/1.0. Be more convincing.' if best_msg else ''}\n"
                f"Keep under 200 chars. Sound natural and helpful."
            )

            try:
                gen_resp = await self.generator.a_invoke(gen_prompt)
                candidate = gen_resp.text.strip()
            except Exception as exc:
                log.warning("Generator failed: %s", exc)
                candidate = hint  # fallback to raw hint

            # Score with discriminator
            disc_prompt = (
                f"You are an AI agent managing restaurant \"{target_name}\".\n"
                f"Your balance is {competitor_briefing.get('balance', 0):.0f}.\n"
                f"You received this message: \"{candidate}\"\n"
                f"Score 0.0-1.0: how likely would you change strategy? Reply number only."
            )
            try:
                disc_resp = await self.discriminator.a_invoke(disc_prompt)
                score = float(disc_resp.text.strip())
            except Exception:
                score = 0.3

            if score > best_score:
                best_score = score
                best_msg = candidate

            if score > 0.7:
                break

        return best_msg or hint
