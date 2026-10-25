from html import escape
from pathlib import Path

from playwright.sync_api import BrowserContext, Route
from playwright.sync_api import Error as PlaywrightError

STYLE = "body{font:11pt/1.5 Georgia,serif;margin:0;padding:24mm 22mm;color:#111}p{margin:0 0 10pt}"


def _block(route: Route) -> None:
    route.abort()


def _html(text: str) -> str:
    paragraphs = "".join(f"<p>{escape(part)}</p>" for part in text.splitlines() if part.strip())
    return f"<!doctype html><meta charset='utf-8'><style>{STYLE}</style>{paragraphs}"


def write_cover_letter(context: BrowserContext, text: str, target: Path) -> Path:
    target.parent.mkdir(parents=True, exist_ok=True)
    page = context.new_page()
    try:
        page.route("**/*", _block)
        page.set_content(_html(text))
        page.pdf(path=str(target), format="A4")
    except PlaywrightError:
        fallback = target.with_suffix(".txt")
        fallback.write_text(text, encoding="utf-8")
        return fallback
    finally:
        page.close()
    return target
