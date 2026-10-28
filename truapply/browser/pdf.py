import re
from pathlib import Path

from playwright.sync_api import Route, sync_playwright

from truapply.browser.chrome import launch_headless

PAGE_OBJECT = re.compile(rb"/Type\s*/Page(?![A-Za-z])")


def count_pages(pdf: bytes) -> int:
    return len(PAGE_OBJECT.findall(pdf))


def _block(route: Route) -> None:
    route.abort()


def print_html(html: str, target: Path) -> int:
    target.parent.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as playwright:
        browser = launch_headless(playwright)
        try:
            context = browser.new_context(java_script_enabled=False, offline=True)
            context.route("**/*", _block)
            page = context.new_page()
            page.set_content(html, wait_until="load")
            page.pdf(
                path=str(target), format="A4", print_background=True, prefer_css_page_size=True
            )
        finally:
            browser.close()
    return count_pages(target.read_bytes())
