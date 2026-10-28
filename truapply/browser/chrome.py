import logging

from playwright.sync_api import Browser, Playwright, sync_playwright
from playwright.sync_api import Error as PlaywrightError

from truapply.core.errors import BrowserUnavailableError

CHROME_CHANNEL = "chrome"

log = logging.getLogger(__name__)


def launch_headless(playwright: Playwright) -> Browser:
    try:
        return playwright.chromium.launch(channel=CHROME_CHANNEL, headless=True)
    except PlaywrightError:
        log.info("Google Chrome not found; trying Playwright's Chromium")
    try:
        return playwright.chromium.launch(headless=True)
    except PlaywrightError as error:
        raise BrowserUnavailableError("Neither Google Chrome nor Chromium could start.") from error


def browser_name() -> str:
    with sync_playwright() as playwright:
        browser = launch_headless(playwright)
        try:
            return f"{browser.browser_type.name} {browser.version}"
        finally:
            browser.close()
