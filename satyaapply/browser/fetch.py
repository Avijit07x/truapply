import asyncio
import json
import logging
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from http import HTTPStatus

from playwright.async_api import APIRequestContext, async_playwright
from playwright.async_api import Error as PlaywrightError

FETCH_TIMEOUT_MS = 45_000
MAX_CONCURRENT = 8
USER_AGENT = "SatyaApply/0.1 (+https://github.com/satyaapply/satyaapply)"
FOLLOW_REDIRECTS = 20

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class Response:
    url: str
    status: int
    data: object | None

    @property
    def missing(self) -> bool:
        return self.status == HTTPStatus.NOT_FOUND


Reader = Callable[[str, int, bytes], Response]


async def _get(
    context: APIRequestContext, url: str, gate: asyncio.Semaphore, redirects: int
) -> tuple[int, bytes]:
    async with gate:
        try:
            response = await context.get(url, timeout=FETCH_TIMEOUT_MS, max_redirects=redirects)
            return response.status, await response.body() if response.ok else b""
        except PlaywrightError as error:
            log.info("couldn't fetch %s: %s", url, str(error).splitlines()[0])
            return 0, b""


def _json(url: str, status: int, body: bytes) -> Response:
    if not body:
        return Response(url, status, None)
    try:
        return Response(url, status, json.loads(body))
    except (json.JSONDecodeError, UnicodeDecodeError):
        log.info("not JSON from %s", url)
        return Response(url, status, None)


def _text(url: str, status: int, body: bytes) -> Response:
    return Response(url, status, body.decode("utf-8", "replace") if body else None)


async def _fetch_all(
    urls: Sequence[str], read: Reader, redirects: int, at_once: int
) -> list[Response]:
    gate = asyncio.Semaphore(at_once)
    async with async_playwright() as playwright:
        context = await playwright.request.new_context(
            extra_http_headers={"User-Agent": USER_AGENT}
        )
        try:
            fetched = await asyncio.gather(*(_get(context, url, gate, redirects) for url in urls))
        finally:
            await context.dispose()
    return [read(url, status, body) for url, (status, body) in zip(urls, fetched, strict=True)]


def fetch_json(urls: Sequence[str]) -> list[Response]:
    if not urls:
        return []
    return asyncio.run(_fetch_all(urls, _json, FOLLOW_REDIRECTS, MAX_CONCURRENT))


def fetch_pages(urls: Sequence[str], at_once: int) -> list[Response]:
    if not urls:
        return []
    return asyncio.run(_fetch_all(urls, _text, 0, at_once))
