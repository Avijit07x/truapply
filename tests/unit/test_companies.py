import json
from contextlib import closing
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from http import HTTPStatus
from pathlib import Path
from typing import Any

import pytest

from tests.unit import samples
from truapply.core.models import Ats, Board, Status
from truapply.core.paths import Paths
from truapply.core.profile import CompanySearch, Profile, save
from truapply.run import discovery
from truapply.run.discovery import CompanySearchNow
from truapply.run.lock import run_lock
from truapply.sources.intake import Intake
from truapply.store import boards, jobs
from truapply.store.boards import BoardOrigin
from truapply.store.db import connect
from truapply.tracker import companies, runs
from truapply.tracker.routes import Incoming, Route, dispatch

NOW = datetime(2026, 10, 27, 9, 0, tzinfo=UTC)


@pytest.fixture
def paths(tmp_path: Path) -> Paths:
    paths = Paths(tmp_path / "home")
    paths.ensure()
    resume = tmp_path / "master.tex"
    resume.write_text("resume", encoding="utf-8")
    save(paths, samples.profile(resume))
    return paths


def call(paths: Paths, table: tuple[Route, ...], path: str) -> tuple[HTTPStatus, Any]:
    with closing(connect(paths.database)) as db:
        response = dispatch(table, Incoming(db, paths, f"/api{path}", {}))
    assert response is not None
    return response.status, json.loads(response.body)


def test_how_often_companies_are_searched_follows_your_setting(tmp_path: Path) -> None:
    with closing(connect(tmp_path / "jobs.db")) as db:
        assert boards.search_due(db, CompanySearch.WEEKLY, NOW)
        assert not boards.search_due(db, CompanySearch.OFF, NOW)
        boards.searched(db, NOW)
        later = NOW + timedelta(days=3)
        assert boards.search_due(db, CompanySearch.DAILY, later)
        assert not boards.search_due(db, CompanySearch.WEEKLY, later)
        assert boards.search_due(db, CompanySearch.WEEKLY, NOW + timedelta(days=7))
        assert boards.next_search(db, CompanySearch.OFF) is None


def test_searching_now_works_even_when_the_setting_is_off(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    searches: list[Profile] = []

    def search(profile: Profile) -> tuple[str, ...]:
        searches.append(profile)
        return ("https://jobs.lever.co/northwind/1",)

    monkeypatch.setattr(discovery, "find_posting_urls", search)
    monkeypatch.setattr(discovery, "shared_boards", list)
    monkeypatch.setattr(discovery, "take_in", lambda *_: Intake(0, 0, 0, 0, 0))
    base = samples.profile(tmp_path / "master.tex")
    off = replace(base, settings=replace(base.settings, company_search=CompanySearch.OFF))
    with closing(connect(tmp_path / "jobs.db")) as db:
        assert discovery.discover(db, off, NOW, CompanySearchNow.WHEN_DUE).new_boards == 0
        assert discovery.discover(db, off, NOW, CompanySearchNow.NOW).new_boards == 1
        assert boards.last_search(db) == NOW
    assert len(searches) == 1


def test_the_company_list_shows_how_each_was_found_and_its_jobs_for_you(paths: Paths) -> None:
    northwind, globex = Board(Ats.LEVER, "northwind", "Northwind"), Board(Ats.ASHBY, "globex")
    with closing(connect(paths.database)) as db:
        boards.add_many(db, [northwind], BoardOrigin.SEARCH, NOW)
        boards.add_many(db, [globex], BoardOrigin.SHARED, NOW)
        boards.mark_checked(db, [], [globex], NOW)
        listed = [samples.job(external_id=f"lever/northwind/{n}") for n in range(3)]
        listed.append(samples.job(external_id="7"))
        jobs.add_many(db, listed, NOW)
        db.execute("update jobs set status = ? where key like '%/2'", (Status.SKIPPED,))
        db.commit()
    status, answer = call(paths, companies.GET, "/companies")
    assert status == HTTPStatus.OK
    first, second = answer["companies"]
    assert (first["company"], first["origin"], first["jobs"], first["closed"]) == (
        "Northwind",
        "search",
        2,
        False,
    )
    assert first["url"] == "https://jobs.lever.co/northwind"
    assert (second["company"], second["closed"]) == ("globex", True)
    assert answer["search"] == {"every": "weekly", "last": None, "next": None}


def test_finding_companies_starts_a_run_that_searches_now_unless_one_is_going(
    paths: Paths, monkeypatch: pytest.MonkeyPatch
) -> None:
    started: list[runs.Choice] = []
    monkeypatch.setattr(runs, "_launch", lambda _paths, choice: started.append(choice))
    with run_lock(paths):
        status, _ = call(paths, companies.POST, "/companies/find")
    assert status == HTTPStatus.BAD_REQUEST
    assert started == []
    call(paths, companies.POST, "/companies/find")
    assert started[0].companies
    assert "--find-companies" in runs.command(started[0])
