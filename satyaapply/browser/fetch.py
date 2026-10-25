import asyncio
import json
import logging
from collections.abc import Sequence
from dataclasses import dataclass
from http import HTTPStatus

from playwright.async_api import APIRequestContext, async_playwright
from playwright.async_api import Error as PlaywrightError

FETCH_TIMEOUT_MS = 45_000
MAX_CONCURRENT = 8
USER_AGENT = "SatyaApply/0.1 (+https://github.com/satyaapply/satyaapply)"

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class Response:
    url: str
    status: int
    data: object | None

    @property
    def missing(self) -> bool:
        return self.status == HTTPStatus.NOT_FOUND


async def _get_json(context: APIRequestContext, url: str, gate: asyncio.Semaphore) -> Response:
    async with gate:
        try:
            response = await context.get(url, timeout=FETCH_TIMEOUT_MS)
            body = await response.body() if response.ok else b""
        except PlaywrightError as error:
            log.info("couldn't fetch %s: %s", url, str(error).splitlines()[0])
            return Response(url, 0, None)
    if not body:
        return Response(url, response.status, None)
    try:
        return Response(url, response.status, json.loads(body))
    except (json.JSONDecodeError, UnicodeDecodeError):
        log.info("not JSON from %s", url)
        return Response(url, response.status, None)


async def _fetch_all(urls: Sequence[str]) -> list[Response]:
    gate = asyncio.Semaphore(MAX_CONCURRENT)
    async with async_playwright() as playwright:
        context = await playwright.request.new_context(
            extra_http_headers={"User-Agent": USER_AGENT}
        )
        try:
            return list(await asyncio.gather(*(_get_json(context, url, gate) for url in urls)))
        finally:
            await context.dispose()


def fetch_json(urls: Sequence[str]) -> list[Response]:
    if not urls:
        return []
    return asyncio.run(_fetch_all(urls))
