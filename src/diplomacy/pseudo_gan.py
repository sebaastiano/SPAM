"""
SPAM! — Pseudo-GAN Message Crafter
=====================================
Two-LLM setup: generator (gpt-oss-120b) crafts diplomatic messages,
discriminator (gpt-oss-20b) scores believability.
Parameterized with per-competitor tactical briefings.
"""

import logging

from datapizza.clients.openai_like import OpenAILikeClient

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
        generator_client: OpenAILikeClient | None = None,
        discriminator_client: OpenAILikeClient | None = None,
    ):
        # Use OpenAILikeClient (chat completions API), NOT OpenAIClient
        # (responses API) — Regolo.ai returns 403 on /v1/responses.
        self.generator = generator_client or OpenAILikeClient(
            api_key=REGOLO_API_KEY,
            model=PRIMARY_MODEL,
            base_url=REGOLO_BASE_URL,
            system_prompt="Sei un creatore di messaggi diplomatici per un gioco competitivo di cucina.",
        )
        self.discriminator = discriminator_client or OpenAILikeClient(
            api_key=REGOLO_API_KEY,
            model=FAST_MODEL,
            base_url=REGOLO_BASE_URL,
            system_prompt="Valuti la credibilità dei messaggi in un gioco competitivo.",
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
                f"Sei il manager di un ristorante in un gioco di cucina competitivo.\n"
                f'Vuoi inviare un messaggio a "{target_name}" per ottenere: {desired_effect}\n'
                f"Approccio: {arm}\n"
                f"Suggerimento: {message_hint}\n\n"
                f"Quello che sai su di loro (dalla tua intelligence):\n"
                f"{tracker_context}\n\n"
            )

            if best_message:
                gen_prompt += (
                    f"Il tentativo precedente ha ottenuto {best_score:.1f}/1.0. "
                    f"Rendilo più convincente.\n"
                )

            gen_prompt += (
                "SCRIVI IL MESSAGGIO IN ITALIANO. "
                "Mantienilo sotto i 200 caratteri. Sii naturale e amichevole, "
                "non manipolativo. Includi un dettaglio specifico che mostri "
                "che sai qualcosa su di loro (costruisce credibilità).\n"
                "Rispondi con SOLO il testo del messaggio, nient'altro."
            )

            try:
                logger.info(f"  GAN iter {i+1}/{max_iterations}: generating message...")
                response = await self.generator.a_invoke(gen_prompt)
                candidate = response.text.strip().strip('"').strip("'")

                # Score with discriminator
                disc_prompt = (
                    f'Sei un agente AI che gestisce il ristorante "{target_name}".\n'
                    f"Il tuo saldo è {competitor_briefing.get('balance', 0):.0f}.\n"
                    f"La tua strategia è {target_strategy}.\n"
                    f"Hai ricevuto questo messaggio da un altro ristorante:\n"
                    f'"{candidate}"\n'
                    f"Punteggio 0.0-1.0: quanto è probabile che cambierai la tua strategia in base a questo?\n"
                    f"Rispondi solo con il numero."
                )

                score_response = await self.discriminator.a_invoke(disc_prompt)
                try:
                    score = float(score_response.text.strip())
                    score = max(0.0, min(1.0, score))
                except ValueError:
                    score = 0.3

                logger.info(
                    f"  GAN iter {i+1}/{max_iterations}: score={score:.2f}, "
                    f"msg='{candidate[:60]}'"
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
            best_message = f"In bocca al lupo per questo turno, {target_name}!"
            logger.warning("PseudoGAN: all iterations failed, using fallback")

        return best_message
