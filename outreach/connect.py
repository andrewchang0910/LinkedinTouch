"""Send a connection request with a personalised note (≤300 chars)."""
import logging
import random

from playwright.async_api import Page

from scraper.rate_limiter import human_delay
from utils import take_error_screenshot

logger = logging.getLogger(__name__)


async def send_connect_with_note(
    page: Page,
    profile_url: str,
    message_text: str,
    dry_run: bool = False,
) -> bool:
    """
    Click 'Connect', choose 'Add a note', paste the message, and send.
    Returns True on success, False on failure.
    Message must be ≤300 chars (LinkedIn hard limit for connection notes).
    """
    if len(message_text) > 300:
        message_text = message_text[:297] + "..."

    try:
        # Only navigate if not already on this profile page
        if not page.url.rstrip("/").endswith(profile_url.rstrip("/").split("/")[-1]):
            await page.goto(profile_url, wait_until="domcontentloaded")
            await human_delay(2.0, 4.0)

        # Scroll a bit
        await page.evaluate(f"window.scrollBy(0, {random.randint(100, 250)})")
        await human_delay(0.5, 1.5)

        # Find 'Connect' button — visible elements only
        _connect_selectors = [
            "button[aria-label*='Connect']",
            "button[aria-label*='Invite']",
            "button[aria-label*='連結']",
            "button[aria-label*='邀請']",
            "button.artdeco-button:has-text('Connect')",
            "button.artdeco-button:has-text('連結')",
        ]
        connect_btn = None
        for sel in _connect_selectors:
            btn = await page.query_selector(sel)
            if btn and await btn.is_visible():
                connect_btn = btn
                break

        if not connect_btn:
            # Try the "More" actions dropdown
            _more_selectors = [
                "button[aria-label*='More actions']",
                "button.artdeco-button:has-text('More')",
                "button.artdeco-button:has-text('更多')",
            ]
            for sel in _more_selectors:
                more_btn = await page.query_selector(sel)
                if more_btn and await more_btn.is_visible():
                    await more_btn.click()
                    await human_delay(0.5, 1.0)
                    for conn_sel in [
                        "div.artdeco-dropdown__content li:has-text('Connect')",
                        "div.artdeco-dropdown__content li:has-text('連結')",
                        "[aria-label*='Connect']",
                    ]:
                        btn = await page.query_selector(conn_sel)
                        if btn and await btn.is_visible():
                            connect_btn = btn
                            break
                    break

        if not connect_btn:
            logger.warning("No 'Connect' button found on %s", profile_url)
            await take_error_screenshot(page, f"no_connect_{profile_url.split('/')[-1]}")
            return False

        await connect_btn.click()
        await human_delay(0.8, 1.5)

        # Click "Add a note"
        add_note_btn = await page.wait_for_selector(
            "button[aria-label='Add a note']", timeout=5_000
        )
        if not add_note_btn:
            logger.warning("'Add a note' button not found for %s", profile_url)
            return False

        await add_note_btn.click()
        await human_delay(0.5, 1.0)

        note_textarea = await page.wait_for_selector(
            "textarea#custom-message", timeout=5_000
        )
        if not note_textarea:
            logger.warning("Note textarea not found for %s", profile_url)
            return False

        if dry_run:
            logger.info("[DRY RUN] Would connect+note to %s: %s", profile_url, message_text)
            close_btn = await page.query_selector("button[aria-label='Dismiss']")
            if close_btn:
                await close_btn.click()
            return True

        await note_textarea.click()
        await note_textarea.type(message_text, delay=random.randint(40, 90))
        await human_delay(0.5, 1.5)

        send_btn = await page.query_selector("button[aria-label='Send now']")
        if not send_btn:
            send_btn = await page.query_selector("button:has-text('Send')")
        if not send_btn:
            logger.warning("Send button not found for %s", profile_url)
            return False

        await send_btn.click()
        await human_delay(1.0, 2.0)

        logger.info("Connection request with note sent to %s", profile_url)
        return True

    except Exception as exc:
        logger.error("send_connect_with_note failed for %s: %s", profile_url, exc)
        await take_error_screenshot(page, f"connect_{profile_url.split('/')[-1]}")
        return False
