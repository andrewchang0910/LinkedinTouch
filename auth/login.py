"""LinkedIn login via Playwright. Saves browser storage state to session.json."""
import asyncio
import logging
from pathlib import Path

from playwright.async_api import async_playwright, Page

import config

logger = logging.getLogger(__name__)


async def _fill_and_submit(page: Page) -> None:
    await page.goto("https://www.linkedin.com/login", wait_until="domcontentloaded")
    await page.fill("#username", config.LINKEDIN_EMAIL)
    await page.fill("#password", config.LINKEDIN_PASSWORD)
    await page.click('button[type="submit"]')
    await page.wait_for_load_state("domcontentloaded")


async def login(headless: bool = False) -> None:
    """
    Launch a browser, log in to LinkedIn, handle 2FA if prompted,
    then save the session to SESSION_FILE.
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless)
        context = await browser.new_context()
        page = await context.new_page()

        await _fill_and_submit(page)

        # Detect 2FA / verification challenge
        if "checkpoint" in page.url or "challenge" in page.url:
            print("\n[!] LinkedIn is asking for verification.")
            print("    Complete it in the browser window, then press ENTER here.")
            input("    Press ENTER when done > ")
            await page.wait_for_load_state("domcontentloaded")

        # Confirm we're logged in
        try:
            await page.wait_for_selector("nav", timeout=10_000)
        except Exception:
            raise RuntimeError(
                "Login failed or timed out — check credentials in .env"
            )

        # Persist session
        Path(config.SESSION_FILE).parent.mkdir(parents=True, exist_ok=True)
        await context.storage_state(path=config.SESSION_FILE)
        logger.info("Session saved to %s", config.SESSION_FILE)
        print(f"[+] Session saved to {config.SESSION_FILE}")

        await browser.close()


if __name__ == "__main__":
    asyncio.run(login())
