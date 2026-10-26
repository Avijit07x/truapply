from contextlib import closing
from http import HTTPStatus
from pathlib import Path

import pytest

from satyaapply.core.paths import Paths
from satyaapply.core.profile import load, save
from satyaapply.store.db import connect
from satyaapply.tracker import settings
from satyaapply.tracker.responses import Response
from satyaapply.tracker.routes import Form, Route
from tests.unit import samples

VALID = {
    "title_keywords": "frontend, react",
    "title_exclude": "senior",
    "skip_companies": "Acme Analytics",
    "relocate_cities": "",
    "max_job_age_days": "30",
    "min_score": "60",
    "expected_min": "1200000",
    "expected_max": "1800000",
    "notice_period": "30 days",
    "daily_cap": "20",
    "onsite_city": "on",
    "remote_country": "on",
}


@pytest.fixture
def paths(tmp_path: Path) -> Paths:
    paths = Paths(tmp_path / "home")
    paths.ensure()
    resume = tmp_path / "master.tex"
    resume.write_text("resume", encoding="utf-8")
    save(paths, samples.profile(resume))
    return paths


def _call(routes: tuple[Route, ...], paths: Paths, form: Form) -> Response:
    match = routes[0].pattern.match("/settings")
    assert match is not None
    with closing(connect(paths.database)) as db:
        return routes[0].handler(db, paths, match, form)


def _body(response: Response) -> str:
    return response.body.decode("utf-8")


def test_page_shows_current_values(paths: Paths) -> None:
    body = _body(_call(settings.GET, paths, {}))
    assert 'value="frontend, react"' in body
    assert 'value="60"' in body
    assert 'name="onsite_city" value="on" checked' in body
    assert 'name="relocate" value="on">' in body
    assert "(INR)" in body
    assert "Saved." not in body
    assert "Saved." in _body(_call(settings.GET, paths, {"saved": "1"}))


def test_saving_persists_trimmed_values(paths: Paths) -> None:
    form = VALID | {"title_keywords": " python ,, Go, python , go ", "min_score": "70"}
    form = form | {"daily_cap": "", "remote_abroad": "on"}
    del form["onsite_city"]
    response = _call(settings.POST, paths, form)
    assert response.status == HTTPStatus.SEE_OTHER
    assert response.location == "/settings?saved=1"
    saved = load(paths)
    assert saved.title_keywords == ("python", "Go")
    assert saved.settings.min_score == 70
    assert saved.daily_cap is None
    assert not saved.work_places.onsite_city
    assert saved.work_places.remote_abroad


@pytest.mark.parametrize(
    "change",
    [
        {"min_score": "150"},
        {"min_score": "abc"},
        {"min_score": "-1"},
        {"expected_min": "2000000"},
        {"daily_cap": "0"},
        {"skip_companies": ",".join(f"c{n}" for n in range(51))},
        {"notice_period": "x" * 201},
    ],
)
def test_invalid_input_is_refused(paths: Paths, change: dict[str, str]) -> None:
    before = load(paths)
    response = _call(settings.POST, paths, VALID | change)
    assert response.status == HTTPStatus.BAD_REQUEST
    assert "Nothing was saved" in _body(response)
    assert load(paths) == before


def test_refused_form_keeps_input(paths: Paths) -> None:
    body = _body(_call(settings.POST, paths, VALID | {"min_score": "abc"}))
    assert 'value="abc"' in body
    assert "Minimum match score" in body


def test_script_is_escaped(paths: Paths) -> None:
    script = "<script>alert(1)</script>"
    assert _call(settings.POST, paths, VALID | {"title_keywords": script}).location
    shown = _body(_call(settings.GET, paths, {}))
    refused = _body(
        _call(settings.POST, paths, VALID | {"title_keywords": script, "min_score": "x"})
    )
    for body in (shown, refused):
        assert script not in body
        assert "&lt;script&gt;" in body


def test_missing_profile_asks_for_setup(tmp_path: Path) -> None:
    paths = Paths(tmp_path / "empty")
    assert "satyaapply setup" in _body(_call(settings.GET, paths, {}))
    assert "satyaapply setup" in _body(_call(settings.POST, paths, VALID))
    assert not paths.profile.exists()
