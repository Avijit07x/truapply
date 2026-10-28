from collections.abc import Sequence
from pathlib import Path

import pytest

from truapply.browser.fetch import Response
from truapply.core import schedule, tasks
from truapply.sources import archive
from truapply.tracker import automatic

HARMLESS = "/usr/bin/true"


@pytest.fixture(autouse=True)
def never_touch_the_real_schedule(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    agents = tmp_path / "LaunchAgents"
    monkeypatch.setattr(schedule, "agents_dir", lambda: agents)
    monkeypatch.setattr(automatic, "agents", lambda: agents)
    monkeypatch.setattr(schedule, "LAUNCHCTL", HARMLESS)
    monkeypatch.setattr(tasks, "folder", lambda: tmp_path / "Tasks")
    monkeypatch.setattr(tasks, "schtasks", lambda _arguments: 0)


def unreachable(urls: Sequence[str], *_rest: object) -> list[Response]:
    return [Response(url, 0, None) for url in urls]


@pytest.fixture(autouse=True)
def never_reach_the_web_archive(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(archive, "fetch_json", unreachable)
    monkeypatch.setattr(archive, "fetch_pages", unreachable)
    monkeypatch.setattr(archive, "sleep", lambda _seconds: None)
