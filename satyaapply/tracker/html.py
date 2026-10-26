from collections.abc import Iterable
from datetime import datetime
from html import escape
from urllib.parse import urlsplit

WEB_SCHEMES = frozenset({"http", "https"})
APP_NAME = "SatyaApply"
SUBTITLE = "Your job search, on your computer"
FOOTER = "Local only · nothing leaves your Mac unless you approve it"

NavItem = tuple[str, str, str]

NAV: tuple[NavItem, ...] = (
    ("/", "🏠", "Home"),
    ("/board", "🗂", "Board"),
    ("/jobs", "📋", "All jobs"),
    ("/runs", "▶️", "Run jobs"),
    ("/learned", "🧠", "What it learned"),
    ("/settings", "⚙️", "Settings"),
)


def e(value: object) -> str:
    return escape(str(value), quote=True)


def when(moment: datetime) -> str:
    return moment.astimezone().strftime("%d %b, %H:%M")


def outside_link(url: str, text: str) -> str:
    if urlsplit(url).scheme not in WEB_SCHEMES:
        return ""
    return f'<a href="{e(url)}" target="_blank" rel="noopener noreferrer">{e(text)}</a>'


def section(title: str, body: str) -> str:
    return f"<section><h2>{e(title)}</h2>{body}</section>"


def empty(text: str) -> str:
    return f'<p class="muted">{e(text)}</p>'


def joined(parts: Iterable[str]) -> str:
    return "".join(parts)


def _nav_link(item: NavItem, active: str) -> str:
    href, icon, label = item
    current = ' class="active" aria-current="page"' if href == active else ""
    return (
        f'<a href="{href}"{current}><span class="icon" aria-hidden="true">{icon}</span>'
        f"<span>{e(label)}</span></a>"
    )


def page(title: str, body: str, active: str = "") -> str:
    nav = joined(_nav_link(item, active) for item in NAV)
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        f"<title>{e(title)} · {APP_NAME}</title>"
        '<link rel="stylesheet" href="/style.css"><link rel="stylesheet" href="/theme.css">'
        '</head><body><a class="skip" href="#content">Skip to content</a>'
        '<div class="app"><aside class="sidebar">'
        f'<a class="workspace" href="/"><span class="mark" aria-hidden="true">S</span>'
        f'<span><strong>{APP_NAME}</strong><span class="sub">{e(SUBTITLE)}</span></span></a>'
        f'<nav class="nav" aria-label="Main">{nav}</nav>'
        f'<p class="sidebar-foot">{e(FOOTER)}</p></aside>'
        f'<main class="content" id="content">{body}</main></div></body></html>'
    )
