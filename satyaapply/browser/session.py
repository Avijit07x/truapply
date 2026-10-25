import logging
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from playwright.sync_api import BrowserContext, Playwright, ViewportSize, sync_playwright
from playwright.sync_api import Error as PlaywrightError

from satyaapply.browser.chrome import CHROME_CHANNEL
from satyaapply.core.errors import BrowserUnavailableError

VIEWPORT: ViewportSize = {"width": 1280, "height": 900}

log = logging.getLogger(__name__)


def _launch(playwright: Playwright, profile_dir: Path, headless: bool) -> BrowserContext:
    profile_dir.mkdir(parents=True, exist_ok=True)
    try:
        return playwright.chromium.launch_persistent_context(
            str(profile_dir), channel=CHROME_CHANNEL, headless=headless, viewport=VIEWPORT
        )
    except PlaywrightError:
        log.info("Google Chrome not usable here; trying Playwright's Chromium")
    try:
        return playwright.chromium.launch_persistent_context(
            str(profile_dir), headless=headless, viewport=VIEWPORT
        )
    except PlaywrightError as error:
        raise BrowserUnavailableError("Couldn't start Chrome or Chromium.") from error


@contextmanager
def browser_session(profile_dir: Path, show: bool = False) -> Iterator[BrowserContext]:
    with sync_playwright() as playwright:
        context = _launch(playwright, profile_dir, headless=not show)
        try:
            yield context
        finally:
            context.close()
