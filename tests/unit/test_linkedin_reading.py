from contextlib import closing
from dataclasses import replace
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import pytest

from satyaapply.core.clock import utc_now
from satyaapply.core.models import Source
from satyaapply.core.paths import Paths
from satyaapply.core.profile import Settings, WorkPlaces, save
from satyaapply.sources.linkedin_search import search_urls
from satyaapply.store import jobs
from satyaapply.store.db import connect
from satyaapply.tracker import linkedin_reading
from tests.unit import samples


@pytest.fixture
def paths(tmp_path: Path) -> Paths:
    paths = Paths(tmp_path / "home")
    paths.ensure()
    return paths


def saved(paths: Paths, tmp_path: Path, settings: Settings | None = None) -> None:
    resume = tmp_path / "master.tex"
    resume.write_text("resume", encoding="utf-8")
    profile = samples.profile(resume)
    places = WorkPlaces(True, True, False, (), True)
    save(paths, replace(profile, work_places=places, settings=settings or Settings()))


def test_searches_cover_each_role_in_the_country_and_remote_anywhere(tmp_path: Path) -> None:
    profile = replace(
        samples.profile(tmp_path / "m.tex"),
        roles=("Frontend Engineer", "React Developer"),
        work_places=WorkPlaces(True, False, False, (), True),
    )
    found = [parse_qs(urlsplit(url).query) for url in search_urls(profile)]
    assert [(q["keywords"][0], q["location"][0], "f_WT" in q) for q in found] == [
        ("Frontend Engineer", "India", False),
        ("Frontend Engineer", "Worldwide", True),
        ("React Developer", "India", False),
        ("React Developer", "Worldwide", True),
    ]
    assert all(q["f_TPR"] == ["r86400"] and q["f_AL"] == ["true"] for q in found)


def test_without_remote_abroad_there_is_no_worldwide_search(tmp_path: Path) -> None:
    profile = replace(
        samples.profile(tmp_path / "m.tex"), work_places=WorkPlaces(True, True, False, (), False)
    )
    assert all("Worldwide" not in url for url in search_urls(profile))


def test_reading_is_off_until_turned_on(paths: Paths, tmp_path: Path) -> None:
    saved(paths, tmp_path)
    with closing(connect(paths.database)) as db:
        assert linkedin_reading.plan(db, paths) == linkedin_reading.NOTHING


def test_the_plan_counts_down_todays_linkedin_jobs(paths: Paths, tmp_path: Path) -> None:
    saved(paths, tmp_path, Settings(linkedin_reading=True, linkedin_reads_per_day=3))
    linked = [samples.job(source=Source.LINKEDIN, external_id=str(n)) for n in range(2)]
    other = samples.job(external_id="greenhouse/x/1")
    with closing(connect(paths.database)) as db:
        jobs.add_many(db, [*linked, other], utc_now())
        shown = linkedin_reading.plan(db, paths)
        assert (shown["read"], shown["left"]) == (True, 1)
        assert shown["searches"]
        jobs.add_many(db, [samples.job(source=Source.LINKEDIN, external_id="9")], utc_now())
        assert linkedin_reading.plan(db, paths)["read"] is False


def test_no_profile_means_no_reading(paths: Paths) -> None:
    with closing(connect(paths.database)) as db:
        assert linkedin_reading.plan(db, paths) == linkedin_reading.NOTHING
