from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from satyaapply.core.profile import Profile, WorkPlaces
from satyaapply.sources.filters import company_skipped, is_fresh, location_fits, title_fits
from tests.unit import samples

NOW = datetime(2026, 10, 25, tzinfo=UTC)


@pytest.fixture
def profile(tmp_path: Path) -> Profile:
    base = samples.profile(tmp_path / "master.tex")
    return replace(
        base,
        title_keywords=("frontend", "front-end", "react", "ui engineer"),
        title_exclude=("senior", "staff", "sde 2"),
        work_places=WorkPlaces(True, True, True, ("Pune",), True),
    )


@pytest.mark.parametrize(
    ("title", "fits"),
    [
        ("Frontend Engineer", True),
        ("Front-End Developer (React)", True),
        ("UI Engineer II", True),
        ("Senior Frontend Engineer", False),
        ("SDE-2, Frontend", False),
        ("Backend Engineer", False),
        ("Reactor Physicist", False),
    ],
)
def test_titles_match_whole_words_and_skip_excluded_ones(
    profile: Profile, title: str, fits: bool
) -> None:
    assert title_fits(title, profile) is fits


@pytest.mark.parametrize(
    ("location", "fits"),
    [
        ("Bengaluru, Karnataka", True),
        ("Bangalore", True),
        ("Pune, India", True),
        ("Hyderabad, India", False),
        ("Remote - India", True),
        ("Remote", True),
        ("Fully remote", True),
        ("Remote, Worldwide", True),
        ("Remote - APAC", True),
        ("Remote (US or India)", True),
        ("New York, NY (HQ) / San Francisco, CA / Remote", True),
        ("India - Chennai ; India - Pune", True),
        ("Remote - United States", False),
        ("Remote US", False),
        ("Remote Canada; Remote US", False),
        ("Toronto, Vancouver, Canada-Remote", False),
        ("Office Location or Remote - USA", False),
        ("San Francisco, CA, New York, NY, or Remote within Canada or United States", False),
        ("San Francisco, CA", False),
        ("", True),
    ],
)
def test_locations_follow_where_the_user_will_work(
    profile: Profile, location: str, fits: bool
) -> None:
    assert location_fits(location, profile) is fits


def test_without_remote_abroad_foreign_remote_jobs_dont_fit(profile: Profile) -> None:
    home_only = replace(profile, work_places=WorkPlaces(True, True, False, (), False))
    assert location_fits("Remote", home_only)
    assert location_fits("Remote - India", home_only)


def test_remote_within_a_country_fits_people_who_live_there(profile: Profile) -> None:
    american = replace(profile, city="Austin", country="United States")
    assert location_fits("Remote - United States", american)
    assert not location_fits("Remote - India", american)


def test_old_postings_are_stale_but_undated_ones_are_kept() -> None:
    job = samples.job()
    assert is_fresh(job, NOW, 30)
    assert not is_fresh(replace(job, posted_at=NOW - timedelta(days=31)), NOW, 30)


def test_skipped_companies_match_despite_legal_suffixes(profile: Profile) -> None:
    assert company_skipped(samples.job(company="Acme Analytics Pvt. Ltd."), profile)
    assert not company_skipped(samples.job(company="Northwind"), profile)
