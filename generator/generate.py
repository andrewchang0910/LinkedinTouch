"""Generate personalized LinkedIn messages using OpenAI GPT-4o."""
import logging

import openai

import config
from generator.prompt import SYSTEM_PROMPT, build_user_prompt

logger = logging.getLogger(__name__)

_client = openai.OpenAI(
    api_key=config.OPENAI_API_KEY,
    base_url=config.OPENAI_BASE_URL,
)


def generate_message(profile: dict) -> str:
    """
    Call GPT model via configured base_url to generate a personalized outreach message.
    Retries once on API error. Returns message string ≤300 chars.
    """
    user_prompt = build_user_prompt(profile)

    for attempt in range(2):
        try:
            response = _client.chat.completions.create(
                model=config.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                max_tokens=120,
                temperature=0.7,
            )
            message = response.choices[0].message.content.strip()

            # Hard truncate to 300 chars as safety net
            if len(message) > 300:
                logger.warning(
                    "Generated message exceeds 300 chars (%d). Truncating.", len(message)
                )
                message = message[:297] + "..."

            logger.info(
                "Generated message for %s (%d chars)",
                profile.get("name", "?"),
                len(message),
            )
            return message

        except openai.OpenAIError as exc:
            if attempt == 0:
                logger.warning("OpenAI error (attempt 1): %s. Retrying...", exc)
            else:
                logger.error("OpenAI error (attempt 2): %s. Giving up.", exc)
                raise

    raise RuntimeError("generate_message: unreachable")
