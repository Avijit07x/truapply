import plistlib
import shlex
import sys
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path

import pytest

from satyaapply.core.errors import ScheduleError
from satyaapply.core.paths import HOME_ENV, Paths
from satyaapply.core.schedule import (
    Installed,
    Plan,
    cron_line,
    every,
    install,
    installed,
    launch_agent,
    next_run,
    plist_path,
    remove,
)

SCHEDULED_RUN = [sys.executable, "-m", "satyaapply", "run", "--scheduled"]


class Launchctl:
    def __init__(self, refuse: bool = False) -> None:
        self.calls: list[list[str]] = []
        self.refuse = refuse

    def __call__(self, arguments: Sequence[str]) -> int:
        self.calls.append(list(arguments))
        return 5 if self.refuse and arguments[0] == "bootstrap" else 0


def test_the_schedule_runs_every_few_hours_and_logs_them(tmp_path: Path) -> None:
    paths = Paths(tmp_path)
    agent = launch_agent(paths, Plan(15))
    assert agent["ProgramArguments"] == SCHEDULED_RUN
    times = agent["StartCalendarInterval"]
    assert isinstance(times, list) and len(times) == 96
    assert times[:2] == [{"Hour": 0, "Minute": 0}, {"Hour": 0, "Minute": 15}]
    environment = agent["EnvironmentVariables"]
    assert isinstance(environment, dict)
    assert environment[HOME_ENV] == str(tmp_path)
    assert agent["StandardOutPath"] == agent["StandardErrorPath"] == str(paths.log)


def test_installing_writes_the_file_and_loads_it(tmp_path: Path) -> None:
    agents = tmp_path / "LaunchAgents"
    launchctl = Launchctl()
    target = install(Paths(tmp_path), Plan(120), agents, launchctl)
    assert target == plist_path(agents)
    times = plistlib.loads(target.read_bytes())["StartCalendarInterval"]
    assert [time["Hour"] for time in times] == list(range(0, 24, 2))
    assert [call[0] for call in launchctl.calls] == ["bootout", "bootstrap"]
    assert launchctl.calls[1][-1] == str(target)
    assert installed(agents) == Installed(120, Path(sys.executable))


def test_a_refused_schedule_is_reported(tmp_path: Path) -> None:
    with pytest.raises(ScheduleError):
        install(Paths(tmp_path), Plan(3), tmp_path, Launchctl(refuse=True))


def test_unscheduling_removes_it(tmp_path: Path) -> None:
    install(Paths(tmp_path), Plan(3), tmp_path, Launchctl())
    assert remove(tmp_path, Launchctl())
    assert installed(tmp_path) is None
    assert not remove(tmp_path, Launchctl())


def test_a_damaged_schedule_file_is_named(tmp_path: Path) -> None:
    plist_path(tmp_path).write_text("not a plist", encoding="utf-8")
    with pytest.raises(ScheduleError, match="damaged"):
        installed(tmp_path)


def test_the_cron_line_runs_the_same_command(tmp_path: Path) -> None:
    paths = Paths(tmp_path / "my data")
    line = cron_line(paths, Plan(240))
    assert line.startswith(f"0 */4 * * * {HOME_ENV}={shlex.quote(str(paths.root))} ")
    assert shlex.join(SCHEDULED_RUN) in line
    assert line.endswith(f">> {shlex.quote(str(paths.log))} 2>&1")


@pytest.mark.parametrize(
    ("minutes", "said", "cron"),
    [(15, "15 min", "*/15 * * * *"), (60, "1 h", "0 */1 * * *"), (90, "1 h 30 min", "0 */1 * * *")],
)
def test_intervals_read_plainly_and_map_to_cron(
    tmp_path: Path, minutes: int, said: str, cron: str
) -> None:
    assert every(minutes) == said
    assert cron_line(Paths(tmp_path), Plan(minutes)).startswith(cron)


@pytest.mark.parametrize(
    ("minutes", "now", "upcoming"),
    [
        (120, datetime(2026, 10, 28, 9, 26, tzinfo=UTC), datetime(2026, 10, 28, 10, 0, tzinfo=UTC)),
        (120, datetime(2026, 10, 28, 22, 0, tzinfo=UTC), datetime(2026, 10, 29, 0, 0, tzinfo=UTC)),
        (90, datetime(2026, 10, 28, 1, 29, tzinfo=UTC), datetime(2026, 10, 28, 1, 30, tzinfo=UTC)),
        (1440, datetime(2026, 10, 28, 5, 0, tzinfo=UTC), datetime(2026, 10, 29, 0, 0, tzinfo=UTC)),
    ],
)
def test_the_next_run_is_the_next_set_time_of_day(
    minutes: int, now: datetime, upcoming: datetime
) -> None:
    assert next_run(Plan(minutes), now) == upcoming


def test_an_older_every_few_hours_schedule_is_still_read(tmp_path: Path) -> None:
    older = {"ProgramArguments": SCHEDULED_RUN, "StartInterval": 7200}
    plist_path(tmp_path).write_bytes(plistlib.dumps(older))
    assert installed(tmp_path) == Installed(120, Path(sys.executable))
