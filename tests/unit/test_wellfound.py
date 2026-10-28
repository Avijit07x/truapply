import json
from contextlib import closing
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from tests.unit import samples
from truapply.browser.fetch import Response
from truapply.core.models import Source, Status
from truapply.core.notes import DOESNT_FIT_NOTE, WELLFOUND_NOTE
from truapply.core.profile import WorkPlaces
from truapply.sources import wellfound
from truapply.store import jobs
from truapply.store.db import connect

NOW = datetime(2026, 10, 27, 9, 0, tzinfo=UTC)
RESUME = "Skills: React, TypeScript, Node.js"


def listing(job_id: int, title: str, days_old: int, **more: object) -> dict[str, object]:
    return {
        "__typename": wellfound.LISTING,
        "id": str(job_id),
        "title": title,
        "slug": title.lower().replace(" ", "-"),
        "description": "Build React &amp; TypeScript screens.",
        "liveStartAt": int((NOW - timedelta(days=days_old)).timestamp()),
        "locationNames": ["Bengaluru"],
        "remote": False,
        "acceptedRemoteLocationNames": [],
        "yearsExperienceMin": 1,
        **more,
    }


def page(*items: dict[str, object], company: str = "Northwind") -> str:
    state: dict[str, object] = {f"{wellfound.LISTING}:{item['id']}": item for item in items}
    refs = [{"__ref": key} for key in state]
    state["StartupResult:1"] = {
        "__typename": wellfound.COMPANY,
        "name": company,
        "highlightedJobListings": refs,
    }
    data = {"props": {"pageProps": {"apolloState": {"data": state}}}}
    return f'<script id="__NEXT_DATA__" type="application/json">{json.dumps(data)}</script>'


def test_a_page_turns_into_jobs_with_their_company_place_and_posting_time() -> None:
    remote = listing(8, "UI Engineer", 1, remote=True, acceptedRemoteLocationNames=["India"])
    found = list(wellfound.listings(page(listing(7, "Frontend Engineer", 2), remote)))
    first, second = (item.job for item in found)
    assert found[0].min_years == 1
    assert (first.source, first.external_id, first.company) == (Source.WELLFOUND, "7", "Northwind")
    assert first.url == "https://wellfound.com/jobs/7-frontend-engineer"
    assert first.description == "Build React & TypeScript screens."
    assert first.posted_at == NOW - timedelta(days=2)
    assert (first.location, second.location) == ("Bengaluru", "Remote (India), Bengaluru")


def test_a_page_without_job_data_gives_nothing() -> None:
    assert list(wellfound.listings("<html>sign in</html>")) == []
    assert list(wellfound.listings('<script id="__NEXT_DATA__">{broken</script>')) == []


def test_searches_cover_each_role_in_your_country_and_remote_only_when_you_want_abroad(
    tmp_path: Path,
) -> None:
    profile = replace(samples.profile(tmp_path), roles=("Frontend Engineer", "React Developer"))
    slugs = ["frontend-engineer", "react-developer", "react-engineer"]
    assert wellfound.role_slugs(profile) == slugs
    assert wellfound.searches(profile)[0] == "https://wellfound.com/role/l/frontend-engineer/india"
    assert not any("/role/r/" in url for url in wellfound.searches(profile))
    abroad = replace(profile, work_places=WorkPlaces(True, True, False, (), True))
    assert "https://wellfound.com/role/r/react-developer" in wellfound.searches(abroad)


def test_later_pages_are_read_only_for_searches_wellfound_answered(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    profile = replace(samples.profile(tmp_path), roles=("Frontend Engineer", "React Developer"))
    asked: list[str] = []

    def answer(urls: list[str], _at_once: int) -> list[Response]:
        asked.extend(urls)
        shown = page(listing(len(asked), "Frontend Engineer", 1))
        return [Response(url, 200, shown if "frontend" in url else None) for url in urls]

    monkeypatch.setattr(wellfound, "fetch_pages", answer)
    with closing(connect(tmp_path / "jobs.db")) as db:
        wellfound.check(db, profile, RESUME, NOW)
    later = [url for url in asked if not url.endswith("page=1")]
    assert len(asked) == 3 + wellfound.MAX_PAGES - 1
    assert all("frontend-engineer" in url for url in later)


def test_only_recent_jobs_that_fit_are_listed_ready_without_a_score_or_resume(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    profile = samples.profile(tmp_path)
    shown = page(
        listing(1, "Frontend Engineer", 1),
        listing(2, "Frontend Engineer", 400),
        listing(3, "Sales Manager", 1),
    )
    monkeypatch.setattr(
        wellfound, "fetch_pages", lambda urls, _: [Response(url, 200, shown) for url in urls]
    )
    with closing(connect(tmp_path / "jobs.db")) as db:
        assert wellfound.check(db, profile, RESUME, NOW) == wellfound.Checked(1)
        assert wellfound.check(db, profile, RESUME, NOW) == wellfound.Checked(0)
        row = db.execute("select * from jobs").fetchone()
        assert jobs.prepared_since(db, NOW - timedelta(days=1)) == 0
    assert (row["key"], row["status"], row["score"], row["resume_pdf"]) == (
        "wellfound:1",
        Status.READY,
        None,
        None,
    )
    assert row["note"] == WELLFOUND_NOTE


def test_experience_and_skills_must_match_yours_and_old_listings_that_dont_are_skipped(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    profile = replace(samples.profile(tmp_path), title_keywords=("frontend", "software engineer"))
    shown = page(
        listing(1, "Frontend Engineer", 1, yearsExperienceMin=7),
        listing(2, "Software Engineer", 1, description="Java, Spring and Kotlin services."),
        listing(3, "Software Engineer", 1, description="React and Node.js web apps."),
        listing(4, "Frontend Engineer", 1, description="Pixel-perfect screens."),
    )
    monkeypatch.setattr(
        wellfound, "fetch_pages", lambda urls, _: [Response(url, 200, shown) for url in urls]
    )
    with closing(connect(tmp_path / "jobs.db")) as db:
        too_senior = next(wellfound.listings(shown)).job
        jobs.add_ready(db, [too_senior], NOW, WELLFOUND_NOTE)
        assert wellfound.check(db, profile, RESUME, NOW).listed == 1
        found = db.execute("select key, status, note from jobs order by key").fetchall()
    assert [tuple(row) for row in found] == [
        ("wellfound:1", Status.SKIPPED, DOESNT_FIT_NOTE),
        ("wellfound:3", Status.READY, WELLFOUND_NOTE),
    ]


def test_when_wellfound_says_slow_down_it_waits_an_hour_and_keeps_what_is_listed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    profile = samples.profile(tmp_path)
    asked: list[str] = []

    def busy(urls: list[str], _at_once: int) -> list[Response]:
        asked.extend(urls)
        return [Response(url, 429, None) for url in urls]

    monkeypatch.setattr(wellfound, "fetch_pages", busy)
    with closing(connect(tmp_path / "jobs.db")) as db:
        jobs.add_ready(db, [samples.job(Source.WELLFOUND, "9")], NOW, WELLFOUND_NOTE)
        first = wellfound.check(db, profile, RESUME, NOW)
        tried = len(asked)
        later = wellfound.check(db, profile, RESUME, NOW + timedelta(minutes=15))
        status = db.execute("select status from jobs").fetchone()[0]
    assert first == later == wellfound.Checked(0, NOW + wellfound.COOL_DOWN)
    assert tried == len(asked) == len(wellfound.searches(profile))
    assert status == Status.READY


def test_your_own_wellfound_titles_roles_and_skip_words_decide_what_is_pulled(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    base = samples.profile(tmp_path)
    chosen = replace(
        base.settings,
        wellfound_roles=("Full Stack Engineer",),
        wellfound_titles=("full stack", "mern"),
        wellfound_skip=("java",),
    )
    profile = replace(base, settings=chosen)
    shown = page(
        listing(1, "MERN Developer", 1),
        listing(2, "Full Stack Engineer", 1),
        listing(3, "Java Full Stack Engineer", 1),
        listing(4, "Frontend Engineer", 1),
    )
    asked: list[str] = []

    def answer(urls: list[str], _at_once: int) -> list[Response]:
        asked.extend(urls)
        return [Response(url, 200, shown) for url in urls]

    monkeypatch.setattr(wellfound, "fetch_pages", answer)
    with closing(connect(tmp_path / "jobs.db")) as db:
        wellfound.check(db, profile, RESUME, NOW)
        titles = {row[0] for row in db.execute("select title from jobs")}
    assert titles == {"MERN Developer", "Full Stack Engineer"}
    assert {url.split("?")[0] for url in asked} == {
        "https://wellfound.com/role/l/full-stack-engineer/india"
    }
