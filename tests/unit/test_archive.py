import json
from collections.abc import Sequence
from contextlib import closing
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

import pytest

from tests.unit import samples
from truapply.browser.fetch import Response
from truapply.core.models import Ats, Board
from truapply.core.profile import CompanySearch
from truapply.run import discovery
from truapply.run.discovery import CompanySearchNow, Finding
from truapply.sources import archive
from truapply.sources.ats import PollResult
from truapply.sources.intake import Intake
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


def test_companies_with_jobs_in_your_country_are_added_once_per_crawl(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    index(monkeypatch, set())
    polled: list[list[str]] = []

    def poll(tried: Sequence[Board]) -> PollResult:
        polled.append(sorted(board.key for board in tried))
        places = {"greenhouse/northwind": "Bengaluru", "lever/acme": "London"}
        found = [
            replace(samples.job(external_id=f"{board.key}/1"), location=places[board.key])
            for board in tried
            if board.key in places
        ]
        alive = [board for board in tried if board.key in places]
        dead = [board for board in tried if board.key not in places]
        return PollResult(found, alive, dead, [])

    monkeypatch.setattr(archive, "poll", poll)
    monkeypatch.setattr(discovery, "shared_boards", list)
    monkeypatch.setattr(discovery, "find_posting_urls", lambda _profile: ())
    monkeypatch.setattr(discovery, "take_in", lambda *_: Intake(0, 0, 0, 0, 0))
    profile = samples.profile(tmp_path / "master.tex")
    with closing(connect(tmp_path / "jobs.db")) as db:
        boards.add_many(db, [Board(Ats.ASHBY, "globex")], BoardOrigin.SHARED, NOW)
        found = discovery.discover(db, profile, NOW, Finding(CompanySearchNow.WHEN_DUE))
        assert found.archived == 1
        assert boards.by_origin(db, BoardOrigin.ARCHIVE) == [Board(Ats.GREENHOUSE, "northwind")]
        assert archived.last_crawl(db) == CRAWL
        assert archived.checked_since(db, NOW) == {"greenhouse/northwind", "lever/acme"}
        again = discovery.discover(db, profile, NOW, Finding(CompanySearchNow.NOW, True))
        assert again.archived == 0
    assert polled == [["greenhouse/northwind", "lever/acme"]]


def test_checking_the_archive_now_works_even_when_finding_companies_is_off(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    index(monkeypatch, set())
    monkeypatch.setattr(archive, "poll", lambda _tried: PollResult([], [], [], []))
    monkeypatch.setattr(discovery, "shared_boards", list)
    monkeypatch.setattr(discovery, "take_in", lambda *_: Intake(0, 0, 0, 0, 0))
    base = samples.profile(tmp_path / "master.tex")
    off = replace(base, settings=replace(base.settings, company_search=CompanySearch.OFF))
    with closing(connect(tmp_path / "jobs.db")) as db:
        discovery.discover(db, off, NOW, Finding(CompanySearchNow.WHEN_DUE))
        assert archived.last_crawl(db) is None
        discovery.discover(db, off, NOW, Finding(CompanySearchNow.SKIP, archive_now=True))
        assert archived.last_crawl(db) == CRAWL
