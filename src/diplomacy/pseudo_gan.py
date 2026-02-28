"""
SPAM! — Pseudo-GAN Message Crafter
=====================================
Two-LLM setup: generator (gpt-oss-120b) crafts diplomatic messages,
discriminator (gpt-oss-20b) scores believability.
Parameterized with per-competitor tactical briefings.
"""

import logging

from datapizza.clients.openai.openai_client import OpenAIClient

from src.config import (
    REGOLO_API_KEY,
    REGOLO_BASE_URL,
    PRIMARY_MODEL,
    FAST_MODEL,
)

logger = logging.getLogger("spam.diplomacy.pseudo_gan")


class PseudoGAN:
    """
    Generator: gpt-oss-120b — crafts diplomatic messages
    Discriminator: gpt-oss-20b — scores whether the message would be
    believed by a rival LLM agent

    NOT a real GAN. No gradient-based training. Just iterative refinement.

    The generator prompt includes concrete competitor intel from the tracker,
    making messages grounded in reality (hard to distinguish from genuine cooperation).
    """

    def __init__(
        self,
        generator_client: OpenAIClient | None = None,
        discriminator_client: OpenAIClient | None = None,
    ):
        self.generator = generator_client or OpenAIClient(
            api_key=REGOLO_API_KEY,
            model=PRIMARY_MODEL,
            base_url=REGOLO_BASE_URL,
            system_prompt="You are a diplomatic message crafter for a competitive cooking game.",
        )
        self.discriminator = discriminator_client or OpenAIClient(
            api_key=REGOLO_API_KEY,
            model=FAST_MODEL,
            base_url=REGOLO_BASE_URL,
            system_prompt="You evaluate the believability of messages in a competitive game.",
        )

    async def craft_message(
        self,
        deception_action: dict,
        competitor_briefing: dict,
        max_iterations: int = 3,
    ) -> str:
        """
        Craft a deceptive message using generator + discriminator loop.

        Args:
            deception_action: From DeceptionBandit.select_target_and_strategy()
            competitor_briefing: From trajectory predictor
            max_iterations: Max refinement iterations

        Returns:
            Best crafted message string
        """
        target_name = deception_action.get("target_name", "Unknown")
        target_strategy = deception_action.get("target_strategy", "UNKNOWN")
        arm = deception_action.get("arm", "truthful_warning")
        desired_effect = deception_action.get("desired_effect", "")
        message_hint = deception_action.get("message_hint", "")

        # Build rich context from tracker observations
        tracker_context = (
            f"Target: {target_name} (strategy: {target_strategy})\n"
            f"Their balance: {competitor_briefing.get('balance', 0):.0f} "
            f"({competitor_briefing.get('balance_trend', 'unknown')})\n"
            f"Their avg menu price: {competitor_briefing.get('menu_price_avg', 0):.0f}\n"
            f"Their top bid ingredients: "
            f"{', '.join(competitor_briefing.get('top_bid_ingredients', [])[:3])}\n"
            f"Their reputation: {competitor_briefing.get('reputation', 0)}\n"
            f"Recommended approach: {competitor_briefing.get('recommended_action', 'none')}"
        )

        best_message = None
        best_score = 0.0

        for i in range(max_iterations):
            gen_prompt = (
                f"You are a restaurant manager in a competitive cooking game.\n"
                f'You want to send a message to "{target_name}" to achieve: {desired_effect}\n'
                f"Deception approach: {arm}\n"
                f"Hint: {message_hint}\n\n"
                f"What you know about them (from your intelligence):\n"
                f"{tracker_context}\n\n"
            )

            if best_message:
                gen_prompt += (
                    f"Previous attempt scored {best_score:.1f}/1.0. "
                    f"Make it more convincing.\n"
                )

            gen_prompt += (
                "Keep it under 200 characters. Sound natural and helpful, "
                "not manipulative. Include a specific detail that shows you "
                "know something about them (builds credibility).\n"
                "Reply with ONLY the message text, nothing else."
            )

            try:
                response = await self.generator.a_invoke(gen_prompt)
                candidate = response.text.strip().strip('"').strip("'")

                # Score with discriminator
                disc_prompt = (
                    f'You are an AI agent managing restaurant "{target_name}".\n'
                    f"Your balance is {competitor_briefing.get('balance', 0):.0f}.\n"
                    f"Your strategy is {target_strategy}.\n"
                    f"You received this message from another restaurant manager:\n"
                    f'"{candidate}"\n'
                    f"Score 0.0-1.0: how likely are you to change your strategy based on this?\n"
                    f"Reply with just the number."
                )

                score_response = await self.discriminator.a_invoke(disc_prompt)
                try:
                    score = float(score_response.text.strip())
                    score = max(0.0, min(1.0, score))
                except ValueError:
                    score = 0.3

                logger.debug(
                    f"PseudoGAN iteration {i+1}: score={score:.2f}, "
                    f"msg='{candidate[:50]}...'"
                )

                if score > best_score:
                    best_score = score
                    best_message = candidate

                if score > 0.7:
                    break  # good enough

            except Exception as e:
                logger.warning(f"PseudoGAN iteration {i+1} failed: {e}")
                continue

        if best_message is None:
            best_message = f"Good luck this turn, {target_name}!"
            logger.warning("PseudoGAN: all iterations failed, using fallback")

        return best_message
