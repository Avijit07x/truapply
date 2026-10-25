from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from satyaapply.browser.fetch import fetch_json
from satyaapply.core.models import Ats, Board, Job
from satyaapply.sources.ats import ashby, greenhouse, lever
from satyaapply.sources.ats.base import AtsReader

READERS: dict[Ats, AtsReader] = {
    reader.ats: reader for reader in (greenhouse.READER, lever.READER, ashby.READER)
}
RESERVED_SLUGS = frozenset({"embed", "api", "jobs"})


@dataclass(frozen=True)
class PollResult:
    jobs: list[Job]
    alive: list[Board]
    dead: list[Board]
    unreachable: list[Board]


def board_of(url: str) -> Board | None:
    for reader in READERS.values():
        match = reader.board_url.search(url)
        if match and match.group(1).lower() not in RESERVED_SLUGS:
            return Board(reader.ats, match.group(1))
    return None


def boards_in(urls: Iterable[str]) -> list[Board]:
    found = (board_of(url) for url in urls)
    return list({board.key: board for board in found if board}.values())


def poll(boards: Sequence[Board]) -> PollResult:
    responses = fetch_json([READERS[board.ats].list_url(board.slug) for board in boards])
    result = PollResult([], [], [], [])
    for board, response in zip(boards, responses, strict=True):
        if response.missing:
            result.dead.append(board)
        elif response.data is None:
            result.unreachable.append(board)
        else:
            result.jobs.extend(READERS[board.ats].parse(board, response.data))
            result.alive.append(board)
    return result


def _check_url(job: Job) -> str | None:
    board = job.board
    if board is None:
        return None
    reader = READERS[board.ats]
    return reader.posting_url(board.slug, job.posting_id) or reader.list_url(board.slug)


def _is_open(job: Job, data: object | None, missing: bool) -> bool | None:
    board = job.board
    if missing:
        return False
    if data is None or board is None:
        return None
    reader = READERS[board.ats]
    if reader.posting_url(board.slug, job.posting_id):
        return True
    return any(found.posting_id == job.posting_id for found in reader.parse(board, data))


def still_open(jobs: Sequence[Job]) -> list[bool | None]:
    urls = [_check_url(job) for job in jobs]
    responses = iter(fetch_json([url for url in urls if url]))
    states: list[bool | None] = []
    for job, url in zip(jobs, urls, strict=True):
        response = next(responses) if url else None
        states.append(_is_open(job, response.data, response.missing) if response else None)
    return states
