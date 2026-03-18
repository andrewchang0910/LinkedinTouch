"""Build and paginate LinkedIn People Search to collect profile URLs."""
import logging
import urllib.parse
from typing import AsyncGenerator

from playwright.async_api import Page

import config
from scraper.rate_limiter import page_delay, check_scrape_cap
import db.repo as repo

logger = logging.getLogger(__name__)

# LinkedIn company size facet codes
_SIZE_CODES = {
    "B": "1-10",
    "C": "11-50",
    "D": "51-200",
    "E": "201-500",
    "F": "501-1000",
    "G": "1001-5000",
    "H": "5001-10000",
    "I": "10001+",
}


def _build_search_url(keyword: str, page_num: int = 1) -> str:
    """Construct a LinkedIn People Search URL with campaign filters."""
    filters = config.CAMPAIGN
    params = {
        "keywords": keyword,
        "origin": "GLOBAL_SEARCH_HEADER",
        "page": page_num,
    }

    # Add network filter for 2nd/3rd connections (broader reach)
    facets = ["&facetNetwork=%5B%22S%22%2C%22O%22%5D"]

    if filters.get("company_sizes"):
        size_list = "%2C".join(filters["company_sizes"])
        facets.append(f"&facetCurrentFunction=%5B%5D")
        # company size facet
        sizes_param = urllib.parse.quote(
            "[" + ",".join(f'"{s}"' for s in filters["company_sizes"]) + "]"
        )
        facets.append(f"&facetCompanySize={sizes_param}")

    base = "https://www.linkedin.com/search/results/people/?" + urllib.parse.urlencode(params)
    return base + "".join(facets)


async def collect_profile_urls(
    page: Page,
    limit: int = 40,
) -> list[str]:
    """Iterate search result pages and collect up to `limit` unique profile URLs."""
    campaign = config.CAMPAIGN
    seen: set[str] = repo.get_existing_profile_urls()  # skip already-scraped profiles
    urls: list[str] = []

    keywords = campaign.get("job_titles", [""])

    for keyword in keywords:
        if len(urls) >= limit:
            break

        page_num = 1
        while len(urls) < limit:
            try:
                check_scrape_cap()
            except Exception as e:
                logger.warning(str(e))
                return urls

            search_url = _build_search_url(keyword, page_num)
            logger.info("Fetching search page %d for keyword '%s'", page_num, keyword)
            await page.goto(search_url, wait_until="domcontentloaded")
            await page_delay()

            # Extract profile links from search results
            anchors = await page.query_selector_all(
                "a[href*='/in/']"
            )
            new_found = 0
            for anchor in anchors:
                href = await anchor.get_attribute("href")
                if not href:
                    continue
                # Normalise to /in/slug
                if "/in/" in href:
                    slug_start = href.index("/in/")
                    clean = "https://www.linkedin.com" + href[slug_start:].split("?")[0]
                    if clean not in seen:
                        seen.add(clean)
                        urls.append(clean)
                        new_found += 1
                        if len(urls) >= limit:
                            break

            logger.info("Page %d: found %d new profiles (total %d)", page_num, new_found, len(urls))

            if new_found == 0:
                # No new results — probably hit the last page
                break

            page_num += 1

    return urls[:limit]
