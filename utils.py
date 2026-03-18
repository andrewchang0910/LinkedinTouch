"""Shared utilities: logging setup, screenshot helper."""
import logging
import logging.handlers
import os
from datetime import datetime
from pathlib import Path

from playwright.async_api import Page

import config


def setup_logging() -> None:
    """Configure root logger with rotating file + console handlers."""
    Path(config.LOG_FILE).parent.mkdir(parents=True, exist_ok=True)
    Path(config.ERROR_SCREENSHOT_DIR).mkdir(parents=True, exist_ok=True)

    root = logging.getLogger()
    root.setLevel(logging.INFO)

    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s — %(message)s")

    # Rotating file handler (10 MB, keep 5)
    fh = logging.handlers.RotatingFileHandler(
        config.LOG_FILE, maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8"
    )
    fh.setFormatter(fmt)
    root.addHandler(fh)

    # Console handler
    ch = logging.StreamHandler()
    ch.setFormatter(fmt)
    root.addHandler(ch)


async def take_error_screenshot(page: Page, label: str) -> str:
    """Save a screenshot to logs/errors/ and return the file path."""
    Path(config.ERROR_SCREENSHOT_DIR).mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_label = "".join(c if c.isalnum() or c in "-_" else "_" for c in label)
    path = os.path.join(config.ERROR_SCREENSHOT_DIR, f"{ts}_{safe_label}.png")
    try:
        await page.screenshot(path=path)
        logging.getLogger(__name__).info("Screenshot saved: %s", path)
    except Exception as e:
        logging.getLogger(__name__).warning("Could not save screenshot: %s", e)
    return path
