"""Scrape structured data from a LinkedIn profile page."""
import logging
from typing import Optional

from playwright.async_api import Page

from scraper.rate_limiter import human_delay, page_delay

logger = logging.getLogger(__name__)


async def _safe_text(page: Page, selector: str) -> str:
    el = await page.query_selector(selector)
    if el:
        return (await el.inner_text()).strip()
    return ""


async def scrape_profile(page: Page, profile_url: str) -> dict:
    """Visit a profile page and return a structured dict of the prospect's info."""
    logger.info("Scraping profile: %s", profile_url)
    await page.goto(profile_url, wait_until="domcontentloaded")
    await page_delay()

    # Human-like scroll to trigger lazy-loaded sections
    await page.evaluate("window.scrollBy(0, 600)")
    await human_delay(1.0, 2.5)
    await page.evaluate("window.scrollBy(0, 600)")
    await human_delay(0.5, 1.5)

    name = await _safe_text(page, "h1")
    headline = await _safe_text(page, ".text-body-medium.break-words")

    # Location
    location = await _safe_text(page, ".pb2.pv-profile-section__meta-item > span")
    if not location:
        location = await _safe_text(page, ".text-body-small.inline.t-black--light.break-words")

    # About section
    about = ""
    about_el = await page.query_selector("#about ~ div .inline-show-more-text")
    if not about_el:
        about_el = await page.query_selector("section#about .pv-shared-text-with-see-more")
    if about_el:
        about = (await about_el.inner_text()).strip()

    # Current company from experience section (first entry)
    company = ""
    company_el = await page.query_selector(
        "#experience ~ div li:first-child .t-14.t-normal"
    )
    if not company_el:
        company_el = await page.query_selector(
            ".pv-entity__secondary-title"
        )
    if company_el:
        raw = (await company_el.inner_text()).strip().split("\n")[0]
        # Strip LinkedIn job-type suffixes like "· 全职", "· Part-time", etc.
        company = raw.split("·")[0].strip()

    # Top 3 experiences
    experiences: list[dict] = []
    exp_items = await page.query_selector_all(
        "#experience ~ div li"
    )
    for item in exp_items[:3]:
        title_el = await item.query_selector(".t-bold span[aria-hidden='true']")
        comp_el = await item.query_selector(".t-14.t-normal span[aria-hidden='true']")
        date_el = await item.query_selector(".t-14.t-normal.t-black--light span[aria-hidden='true']")
        experiences.append(
            {
                "title": (await title_el.inner_text()).strip() if title_el else "",
                "company": (await comp_el.inner_text()).strip() if comp_el else "",
                "dates": (await date_el.inner_text()).strip() if date_el else "",
            }
        )

    return {
        "profile_url": profile_url,
        "name": name,
        "headline": headline,
        "company": company,
        "location": location,
        "about": about[:500],  # cap to avoid DB bloat
        "experiences": experiences,
    }
