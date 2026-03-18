"""Decide send vs connect flow; enforce rate limits; log results."""
import logging

from playwright.async_api import Page

import db.repo as repo
from scraper.rate_limiter import check_message_cap, human_delay
from outreach.send import send_message
from outreach.connect import send_connect_with_note

logger = logging.getLogger(__name__)


_MSG_SELECTORS = [
    "button[aria-label*='Message']",
    "button[aria-label*='訊息']",
    "button[aria-label*='Send message']",
    "button.artdeco-button:has-text('Message')",
    "button.artdeco-button:has-text('訊息')",
]

_CONNECT_SELECTORS = [
    "button[aria-label*='Connect']",
    "button[aria-label*='Invite']",
    "button[aria-label*='連結']",
    "button[aria-label*='邀請']",
    "button.artdeco-button:has-text('Connect')",
    "button.artdeco-button:has-text('連結')",
]


async def _find_button(page: Page, selectors: list[str]):
    for sel in selectors:
        btn = await page.query_selector(sel)
        if btn and await btn.is_visible():
            return btn
    return None


async def _has_message_button(page: Page) -> bool:
    return await _find_button(page, _MSG_SELECTORS) is not None


async def dispatch(
    page: Page,
    prospect_id: int,
    profile_url: str,
    message_text: str,
    message_id: int,
    dry_run: bool = False,
) -> bool:
    """
    Choose the right outreach flow (message vs connect+note),
    enforce daily cap, and record the result.
    """
    try:
        check_message_cap()
    except Exception as e:
        logger.warning(str(e))
        return False

    # Navigate once to check which button is available
    await page.goto(profile_url, wait_until="domcontentloaded")
    # Wait for LinkedIn SPA to render profile action buttons
    try:
        await page.wait_for_selector(
            ".pvs-profile-actions, .pv-top-card-v2-ctas, .artdeco-container-card",
            timeout=6_000,
        )
    except Exception:
        pass  # proceed even if selector not found
    await human_delay(1.5, 3.0)

    if await _has_message_button(page):
        success = await send_message(page, profile_url, message_text, dry_run=dry_run)
        flow = "message"
    else:
        success = await send_connect_with_note(page, profile_url, message_text, dry_run=dry_run)
        flow = "connect+note"

    if success:
        if not dry_run:
            repo.mark_sent(message_id)
            repo.set_prospect_status(prospect_id, "messaged")
            repo.increment_messaged()
        logger.info("[%s] Sent via %s to %s", "DRY" if dry_run else "OK", flow, profile_url)
    else:
        repo.mark_message_failed(message_id)
        repo.set_prospect_status(prospect_id, "failed")
        logger.error("Failed to send to %s via %s", profile_url, flow)

    return success
