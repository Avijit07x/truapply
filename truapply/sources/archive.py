import json
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from time import sleep
from urllib.parse import quote

from truapply.browser.fetch import fetch_json, fetch_pages
from truapply.core.models import Board
from truapply.core.profile import Profile
from truapply.sources.ats import boards_in, poll
from truapply.sources.lookup import with_local_jobs

INDEX = "https://index.commoncrawl.org"
CRAWLS = f"{INDEX}/collinfo.json"
HOSTS = ("job-boards.greenhouse.io", "boards.greenhouse.io", "jobs.lever.co", "jobs.ashbyhq.com")
TRIES = 3
ONE_AT_A_TIME = 1
PAGE_WAIT_MS = 180_000
PAUSE_S = 15


@dataclass(frozen=True)
class Crawl:
    boards: list[Board]
    complete: bool


@dataclass(frozen=True)
class Checked:
    local: list[Board]
    checked: list[Board]


def latest_crawl() -> str | None:
    crawls = fetch_json([CRAWLS])[0].data
    first = crawls[0] if isinstance(crawls, list) and crawls else None
    name = first.get("id") if isinstance(first, dict) else None
    return name if isinstance(name, str) else None


def _query(crawl: str, host: str) -> str:
    return f"{INDEX}/{crawl}-index?url={quote(host)}/*&output=json&fl=url"


def _with_retries(urls: Sequence[str]) -> list[str | None]:
    texts: dict[str, str] = {}
    for attempt in range(TRIES):
        missing = [url for url in urls if url not in texts]
        if not missing:
            break
        if attempt:
            sleep(PAUSE_S * attempt)
        for response in fetch_pages(missing, ONE_AT_A_TIME, PAGE_WAIT_MS):
            if isinstance(response.data, str):
                texts[response.url] = response.data
    return [texts.get(url) for url in urls]


def _pages_in(text: str | None) -> int | None:
    try:
        count = json.loads(text).get("pages") if text else None
    except (json.JSONDecodeError, AttributeError):
        return None
    return count if isinstance(count, int) else None


def _page_counts(crawl: str) -> list[int | None]:
    asked = _with_retries([f"{_query(crawl, host)}&showNumPages=true" for host in HOSTS])
    return [_pages_in(text) for text in asked]


def _urls_in(text: str) -> Iterable[str]:
    for line in text.splitlines():
        try:
            url = json.loads(line).get("url")
        except (json.JSONDecodeError, AttributeError):
            continue
        if isinstance(url, str):
            yield url


def read(crawl: str) -> Crawl:
    counts = _page_counts(crawl)
    pages = [
        f"{_query(crawl, host)}&page={page}"
        for host, count in zip(HOSTS, counts, strict=True)
        if isinstance(count, int)
        for page in range(count)
    ]
    texts = _with_retries(pages)
    urls = (url for text in texts if text for url in _urls_in(text))
    found = {board.key.lower(): board for board in boards_in(urls)}
    boards = [Board(board.ats, board.slug.lower()) for board in found.values()]
    return Crawl(boards, None not in counts and None not in texts)


def check(boards: Sequence[Board], profile: Profile) -> Checked:
    result = poll(boards)
    local = with_local_jobs(result, profile)
    return Checked(
        [board for board in result.alive if board.key in local], [*result.alive, *result.dead]
    )
