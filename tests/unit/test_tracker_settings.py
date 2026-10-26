import json
from contextlib import closing
from http import HTTPStatus
from pathlib import Path
from typing import Any

import pytest

from satyaapply.core.paths import Paths
from satyaapply.core.profile import load, save
from satyaapply.store.db import connect
from satyaapply.tracker import settings
from satyaapply.tracker.body import Body
from satyaapply.tracker.routes import Route
from tests.unit import samples

VALID: dict[str, object] = {
    "titleKeywords": ["frontend", "react"],
    "titleExclude": ["senior"],
    "skipCompanies": ["Acme Analytics"],
    "relocateCities": [],
    "maxJobAgeDays": 30,
    "minScore": 60,
    "expectedMin": 1_200_000,
    "expectedMax": 1_800_000,
    "noticePeriod": "30 days",
    "dailyCap": 20,
    "onsiteCity": True,
    "remoteCountry": True,
    "relocate": False,
    "remoteAbroad": False,
}


@pytest.fixture
def paths(tmp_path: Path) -> Paths:
    paths = Paths(tmp_path / "home")
    paths.ensure()
    resume = tmp_path / "master.tex"
    resume.write_text("resume", encoding="utf-8")
    save(paths, samples.profile(resume))
    return paths


def call(routes: tuple[Route, ...], paths: Paths, body: Body) -> tuple[HTTPStatus, Any]:
    match = routes[0].pattern.match("/api/settings")
    assert match is not None
    with closing(connect(paths.database)) as db:
        response = routes[0].handler(db, paths, match, body)
    return response.status, json.loads(response.body)


def test_current_values_and_fixed_facts_are_shown(paths: Paths) -> None:
    status, view = call(settings.GET, paths, {})
    assert status == HTTPStatus.OK
    assert view["values"] == VALID
    assert view["fixed"]["city"] == "Bengaluru"
    assert view["fixed"]["currency"] == "INR"
    assert view["fixed"]["maxItems"] == settings.MAX_ITEMS


def test_saving_persists_trimmed_values(paths: Paths) -> None:
    keywords = [" python ", "", "Go", "python ", " go ", "full   stack"]
    body = VALID | {"titleKeywords": keywords, "minScore": 70, "dailyCap": None}
    body = body | {"onsiteCity": False, "remoteAbroad": True}
    status, view = call(settings.POST, paths, body)
    assert status == HTTPStatus.OK
    assert view["values"]["titleKeywords"] == ["python", "Go", "full stack"]
    saved = load(paths)
    assert saved.title_keywords == ("python", "Go", "full stack")
    assert saved.settings.min_score == 70
    assert saved.daily_cap is None
    assert not saved.work_places.onsite_city
    assert saved.work_places.remote_abroad


@pytest.mark.parametrize(
    "change",
    [
        {"minScore": 150},
        {"minScore": "60"},
        {"minScore": -1},
        {"minScore": 60.5},
        {"minScore": None},
        {"expectedMin": 2_000_000},
        {"dailyCap": 0},
        {"skipCompanies": [f"c{n}" for n in range(51)]},
        {"skipCompanies": "Acme"},
        {"titleExclude": ["x" * 201]},
        {"noticePeriod": "x" * 201},
        {"onsiteCity": "yes"},
    ],
)
def test_invalid_input_is_refused(paths: Paths, change: dict[str, object]) -> None:
    before = load(paths)
    status, answer = call(settings.POST, paths, VALID | change)
    assert status == HTTPStatus.BAD_REQUEST
    assert answer["error"] == settings.NOT_SAVED
    assert answer["problems"]
    assert load(paths) == before


def test_every_problem_is_named_at_once(paths: Paths) -> None:
    _, answer = call(settings.POST, paths, VALID | {"minScore": 150, "dailyCap": 0})
    assert len(answer["problems"]) == 2
    assert answer["problems"][0].startswith("Minimum match score")


def test_missing_profile_asks_for_setup(tmp_path: Path) -> None:
    paths = Paths(tmp_path / "empty")
    for routes in (settings.GET, settings.POST):
        status, answer = call(routes, paths, VALID)
        assert status == HTTPStatus.CONFLICT
        assert "satyaapply setup" in answer["error"]
    assert not paths.profile.exists()
