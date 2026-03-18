"""Load and validate an existing LinkedIn session."""
import logging
from pathlib import Path
from typing import Optional

from playwright.async_api import Browser, BrowserContext, async_playwright

import config
from auth.login import login

logger = logging.getLogger(__name__)


async def load_context(browser: Browser) -> BrowserContext:
    """Return a BrowserContext with a valid LinkedIn session.

    If session.json doesn't exist or the session has expired, triggers re-login.
    """
    session_path = Path(config.SESSION_FILE)

    if session_path.exists():
        context = await browser.new_context(storage_state=str(session_path))
        page = await context.new_page()
        await page.goto("https://www.linkedin.com/feed/", wait_until="domcontentloaded")

        # Quick validity check — nav bar should be present when logged in
        nav = await page.query_selector("nav")
        if nav and "feed" in page.url:
            logger.info("Existing session is valid.")
            await page.close()
            return context

        logger.warning("Session expired — re-logging in.")
        await context.close()

    # Re-login and reload
    await login(headless=False)
    context = await browser.new_context(storage_state=str(session_path))
    return context


async def get_browser_and_context():
    """Helper that returns (playwright, browser, context) for use as a context manager."""
    p = await async_playwright().start()
    browser = await p.chromium.launch(headless=False)
    context = await load_context(browser)
    return p, browser, context
