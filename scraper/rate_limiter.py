"""Rate limiting: daily cap + exponential back-off."""
import asyncio
import logging
import random

import config
import db.repo as repo

logger = logging.getLogger(__name__)


class DailyCapExceeded(Exception):
    pass


def check_scrape_cap() -> None:
    counts = repo.get_daily_counts()
    if counts["scraped"] >= config.DAILY_SCRAPE_CAP:
        raise DailyCapExceeded(
            f"Daily scrape cap of {config.DAILY_SCRAPE_CAP} reached."
        )


def check_message_cap() -> None:
    counts = repo.get_daily_counts()
    if counts["messaged"] >= config.DAILY_MESSAGE_CAP:
        raise DailyCapExceeded(
            f"Daily message cap of {config.DAILY_MESSAGE_CAP} reached."
        )


async def human_delay(min_s: float = 1.0, max_s: float = 4.0) -> None:
    """Random sleep to mimic human interaction speed."""
    delay = random.uniform(min_s, max_s)
    logger.debug("Sleeping %.2fs", delay)
    await asyncio.sleep(delay)


async def page_delay() -> None:
    """Longer delay between page loads (2-5s)."""
    await human_delay(2.0, 5.0)


async def with_backoff(coro, max_retries: int = 3):
    """Run an async callable with exponential back-off on exception."""
    for attempt in range(max_retries):
        try:
            return await coro()
        except Exception as exc:
            if attempt == max_retries - 1:
                raise
            wait = (2 ** attempt) + random.uniform(0, 1)
            logger.warning("Attempt %d failed (%s). Retrying in %.1fs.", attempt + 1, exc, wait)
            await asyncio.sleep(wait)
