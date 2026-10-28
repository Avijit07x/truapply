import json
from collections.abc import Sequence
from contextlib import closing
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

import pytest

from tests.unit import samples
from truapply.browser.fetch import Response
from truapply.core import archive_task
from truapply.core.errors import ArchiveCheckGoingError
from truapply.core.locks import held
from truapply.core.models import Ats, Board
from truapply.core.paths import Paths
from truapply.core.profile import CompanySearch, load, save
from truapply.run.archive_check import check_now, due
from truapply.sources import archive
from truapply.sources.ats import PollResult
from truapply.store import archive as archived
from truapply.store import boards
from truapply.store.boards import BoardOrigin
from truapply.store.db import connect

NOW = datetime(2026, 10, 28, 9, 0, tzinfo=UTC)
CRAWL = "CC-MAIN-2026-43"
LINES = {
    "job-boards.greenhouse.io": ["https://job-boards.greenhouse.io/Northwind/jobs/1"],
    "boards.greenhouse.io": ["https://boards.greenhouse.io/northwind", "not json"],
    "jobs.lever.co": ["https://jobs.lever.co/acme/2", "https://jobs.lever.co/api/x"],
    "jobs.ashbyhq.com": ["https://jobs.ashbyhq.com/globex"],
}


def host_of(url: str) -> str:
    return next(host for host in archive.HOSTS if f"url={host}/" in url)


def index(monkeypatch: pytest.MonkeyPatch, failing: set[str]) -> list[str]:
    asked: list[str] = []

    def crawls(urls: Sequence[str]) -> list[Response]:
        return [Response(urls[0], 200, [{"id": CRAWL}, {"id": "CC-MAIN-2026-39"}])]

    def answer(url: str) -> Response:
        host = host_of(url)
        if "showNumPages" in url:
            return Response(url, 200, json.dumps({"pages": 1}))
        if host in failing:
            return Response(url, 503, None)
        lines = [json.dumps({"url": u}) if u.startswith("http") else u for u in LINES[host]]
        return Response(url, 200, "\n".join(lines))

    def pages(urls: Sequence[str], _at_once: int, _wait_ms: int) -> list[Response]:
        asked.extend(urls)
        return [answer(url) for url in urls]

    monkeypatch.setattr(archive, "fetch_json", crawls)
    monkeypatch.setattr(archive, "fetch_pages", pages)
    return asked


def test_the_latest_crawl_lists_each_company_once(monkeypatch: pytest.MonkeyPatch) -> None:
    index(monkeypatch, set())
    assert archive.latest_crawl() == CRAWL
    read = archive.read(CRAWL)
    assert sorted(board.key for board in read.boards) == [
        "ashby/globex",
        "greenhouse/northwind",
        "lever/acme",
    ]
    assert read.complete


def test_a_page_that_keeps_failing_is_retried_then_left_for_next_time(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    asked = index(monkeypatch, {"jobs.lever.co"})
    read = archive.read(CRAWL)
    assert not read.complete
    assert sum("jobs.lever.co" in url and "&page=" in url for url in asked) == archive.TRIES
    assert "lever/acme" not in {board.key for board in read.boards}


def polled(tried: Sequence[Board]) -> PollResult:
    places = {"greenhouse/northwind": "Bengaluru", "lever/acme": "London"}
    found = [
        replace(samples.job(external_id=f"{board.key}/1"), location=places[board.key])
        for board in tried
        if board.key in places
    ]
    alive = [board for board in tried if board.key in places]
    return PollResult(found, alive, [board for board in tried if board not in alive], [])


@pytest.fixture
def home(tmp_path: Path) -> Paths:
    paths = Paths(tmp_path / "home")
    paths.ensure()
    resume = tmp_path / "master.tex"
    resume.write_text("resume", encoding="utf-8")
    save(paths, samples.profile(resume))
    return paths


def test_companies_with_jobs_in_your_country_are_added_once_per_crawl(
    home: Paths, monkeypatch: pytest.MonkeyPatch
) -> None:
    index(monkeypatch, set())
    asked: list[list[str]] = []

    def poll(tried: Sequence[Board]) -> PollResult:
        asked.append(sorted(board.key for board in tried))
        return polled(tried)

    monkeypatch.setattr(archive, "poll", poll)
    with closing(connect(home.database)) as db:
        boards.add_many(db, [Board(Ats.ASHBY, "globex")], BoardOrigin.SHARED, NOW)
    assert check_now(home, lambda: NOW) == 1
    assert check_now(home, lambda: NOW) == 0
    with closing(connect(home.database)) as db:
        assert boards.by_origin(db, BoardOrigin.ARCHIVE) == [Board(Ats.GREENHOUSE, "northwind")]
        assert archived.last_crawl(db) == CRAWL
        assert archived.checked_since(db, NOW) == {"greenhouse/northwind", "lever/acme"}
    assert asked == [["greenhouse/northwind", "lever/acme"]]


def test_only_one_archive_check_goes_at_a_time(home: Paths) -> None:
    with held(home.archive_lock, ArchiveCheckGoingError("busy")):
        assert archive_task.is_going(home)
        assert not archive_task.start_in_background(home)
        with pytest.raises(ArchiveCheckGoingError):
            check_now(home)
    assert archive_task.start_in_background(home)


def test_a_run_starts_the_weekly_check_in_the_background_and_goes_on(
    home: Paths, monkeypatch: pytest.MonkeyPatch
) -> None:
    started: list[Path] = []
    monkeypatch.setattr(archive_task, "_spawn", started.append)
    profile = load(home)
    off = replace(profile, settings=replace(profile.settings, company_search=CompanySearch.OFF))
    with closing(connect(home.database)) as db:
        assert due(db, profile, NOW)
        assert not due(db, off, NOW)
        archived.checked(db, NOW)
        assert not due(db, profile, NOW)
    assert archive_task.start_in_background(home)
    assert started == [home.archive_log]
