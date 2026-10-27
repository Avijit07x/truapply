import json
from contextlib import closing
from http import HTTPStatus
from pathlib import Path
from typing import Any

import pytest

from satyaapply.core import schedule
from satyaapply.core.paths import Paths
from satyaapply.core.profile import save
from satyaapply.store.db import connect
from satyaapply.tracker import automatic, settings
from satyaapply.tracker.body import Body
from satyaapply.tracker.routes import Route
from tests.unit import samples
from tests.unit.test_tracker_settings import VALID


@pytest.fixture
def paths(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Paths:
    agents = tmp_path / "agents"
    monkeypatch.setattr(automatic, "agents", lambda: agents)
    monkeypatch.setattr(automatic, "runner", lambda _arguments: 0)
    monkeypatch.setattr(automatic, "supported", lambda: True)
    paths = Paths(tmp_path / "home")
    paths.ensure()
    resume = tmp_path / "master.tex"
    resume.write_text("resume", encoding="utf-8")
    save(paths, samples.profile(resume))
    return paths


def call(routes: tuple[Route, ...], paths: Paths, path: str, body: Body) -> tuple[HTTPStatus, Any]:
    match = routes[0].pattern.match(path)
    assert match is not None
    with closing(connect(paths.database)) as db:
        response = routes[0].handler(db, paths, match, body)
    return response.status, json.loads(response.body)


def test_off_until_turned_on(paths: Paths) -> None:
    _, view = call(settings.GET, paths, "/api/settings", {})
    assert view["automatic"] == {"supported": True, "on": False, "everyMinutes": None}


def test_turning_on_and_off(paths: Paths) -> None:
    status, shown = call(automatic.POST, paths, "/api/settings/automatic", {"on": True})
    assert status == HTTPStatus.OK
    assert shown == {"supported": True, "on": True, "everyMinutes": 180}
    assert schedule.plist_path(automatic.agents()).is_file()
    _, shown = call(automatic.POST, paths, "/api/settings/automatic", {"on": False})
    assert shown["on"] is False
    assert not schedule.plist_path(automatic.agents()).exists()


def test_changing_the_hours_moves_a_running_schedule(paths: Paths) -> None:
    call(automatic.POST, paths, "/api/settings/automatic", {"on": True})
    _, view = call(settings.POST, paths, "/api/settings", VALID | {"runEveryMinutes": 360})
    assert view["automatic"]["everyMinutes"] == 360


def test_changing_the_hours_while_off_keeps_it_off(paths: Paths) -> None:
    _, view = call(settings.POST, paths, "/api/settings", VALID | {"runEveryMinutes": 360})
    assert view["automatic"]["on"] is False


def test_needs_a_yes_or_no(paths: Paths) -> None:
    status, _ = call(automatic.POST, paths, "/api/settings/automatic", {"on": "yes"})
    assert status == HTTPStatus.BAD_REQUEST
