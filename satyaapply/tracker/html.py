from collections.abc import Iterable
from datetime import datetime
from html import escape
from urllib.parse import urlsplit

WEB_SCHEMES = frozenset({"http", "https"})


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


def page(title: str, body: str) -> str:
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        f"<title>{e(title)} · SatyaApply</title>"
        '<link rel="stylesheet" href="/style.css"></head><body>'
        '<header class="top"><a class="brand" href="/">SatyaApply</a>'
        '<nav><a href="/">Home</a><a href="/jobs">All jobs</a></nav></header>'
        f"<main>{body}</main></body></html>"
    )
