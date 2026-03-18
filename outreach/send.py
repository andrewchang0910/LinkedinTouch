"""Send a message to a prospect via the LinkedIn message dialog."""
import asyncio
import logging
import random

from playwright.async_api import Page

from scraper.rate_limiter import human_delay
from utils import take_error_screenshot

logger = logging.getLogger(__name__)


async def send_message(
    page: Page,
    profile_url: str,
    message_text: str,
    dry_run: bool = False,
) -> bool:
    """
    Navigate to the profile, open the Message dialog, type the message, and send it.
    Returns True on success, False on failure.
    """
    try:
        # Only navigate if not already on this profile page
        if not page.url.rstrip("/").endswith(profile_url.rstrip("/").split("/")[-1]):
            await page.goto(profile_url, wait_until="domcontentloaded")
            await human_delay(2.0, 4.0)

        # Scroll a bit to seem human
        await page.evaluate(f"window.scrollBy(0, {random.randint(100, 300)})")
        await human_delay(0.5, 1.5)

        # Click the "Message" button on the profile (visible only)
        _msg_selectors = [
            "button[aria-label*='Message']",
            "button[aria-label*='訊息']",
            "button[aria-label*='Send message']",
            "button.artdeco-button:has-text('Message')",
            "button.artdeco-button:has-text('訊息')",
            "a[href*='/messaging/thread/new']",
        ]
        message_btn = None
        for sel in _msg_selectors:
            btn = await page.query_selector(sel)
            if btn and await btn.is_visible():
                message_btn = btn
                break
        if not message_btn:
            logger.warning("No 'Message' button found on %s", profile_url)
            return False

        await message_btn.click()
        await human_delay(1.0, 2.0)

        # Wait for message compose box
        compose_box = await page.wait_for_selector(
            ".msg-form__contenteditable", timeout=8_000
        )
        if not compose_box:
            logger.warning("Message compose box not found for %s", profile_url)
            return False

        await compose_box.click()
        await human_delay(0.3, 0.8)

        if dry_run:
            logger.info("[DRY RUN] Would send to %s: %s", profile_url, message_text)
            # Close dialog
            close_btn = await page.query_selector("button[data-control-name='overlay.close']")
            if close_btn:
                await close_btn.click()
            return True

        # Type message character by character with random delays
        for char in message_text:
            await page.keyboard.type(char)
            await asyncio.sleep(random.uniform(0.03, 0.10))

        await human_delay(0.5, 1.5)

        # Click send button
        send_btn = await page.query_selector("button.msg-form__send-button")
        if not send_btn:
            send_btn = await page.query_selector(
                "button[data-control-name='send']"
            )
        if not send_btn:
            logger.warning("Send button not found for %s", profile_url)
            return False

        await send_btn.click()
        await human_delay(1.0, 2.0)

        logger.info("Message sent to %s", profile_url)
        return True

    except Exception as exc:
        logger.error("send_message failed for %s: %s", profile_url, exc)
        await take_error_screenshot(page, f"send_{profile_url.split('/')[-1]}")
        return False
