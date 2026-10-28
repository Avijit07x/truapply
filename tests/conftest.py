from pathlib import Path

import pytest

from truapply.core import schedule
from truapply.tracker import automatic

HARMLESS = "/usr/bin/true"


@pytest.fixture(autouse=True)
def never_touch_the_real_schedule(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    agents = tmp_path / "LaunchAgents"
    monkeypatch.setattr(schedule, "agents_dir", lambda: agents)
    monkeypatch.setattr(automatic, "agents", lambda: agents)
    monkeypatch.setattr(schedule, "LAUNCHCTL", HARMLESS)
