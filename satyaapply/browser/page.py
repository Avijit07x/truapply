import re
from pathlib import Path

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import Locator, Page
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

QUIET_TIMEOUT_MS = 8_000
NAVIGATION_TIMEOUT_MS = 45_000
TEXT_TIMEOUT_MS = 5_000
SETTLE_MS = 600


def wait_until_quiet(page: Page) -> bool:
    try:
        page.wait_for_load_state("networkidle", timeout=QUIET_TIMEOUT_MS)
    except PlaywrightTimeoutError:
        return False
    page.wait_for_timeout(SETTLE_MS)
    return True


def visible_text(page: Page) -> str:
    try:
        return page.locator("body").inner_text(timeout=TEXT_TIMEOUT_MS)
    except PlaywrightError:
        return ""


def find_button(root: Locator, pattern: re.Pattern[str]) -> Locator | None:
    candidates = root.get_by_role("button", name=pattern).or_(
        root.get_by_role("link", name=pattern)
    )
    for index in range(candidates.count()):
        candidate = candidates.nth(index)
        if candidate.is_visible() and candidate.is_enabled():
            return candidate
    return None


def screenshot(page: Page, target: Path) -> Path | None:
    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        page.evaluate("window.scrollTo(0, 0)")
        page.screenshot(path=str(target), full_page=True)
    except PlaywrightError:
        return None
    return target
