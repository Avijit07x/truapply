from collections.abc import Sequence
from pathlib import Path

import pytest

from truapply.cli import build_parser
from truapply.core.errors import ScheduleError
from truapply.core.paths import Paths
from truapply.core.schedule import MINUTES_PER_DAY, Installed, Plan
from truapply.core.tasks import TASK_NAME, install, installed, program, remove, task_path


class Schtasks:
    def __init__(self, refuse: bool = False) -> None:
        self.calls: list[list[str]] = []
        self.refuse = refuse

    def __call__(self, arguments: Sequence[str]) -> int:
        self.calls.append(list(arguments))
        return 1 if self.refuse and arguments[0] == "/Create" else 0


def test_the_windows_task_runs_every_few_hours_from_midnight_and_catches_up(
    tmp_path: Path,
) -> None:
    paths = Paths(tmp_path / "my data")
    schtasks = Schtasks()
    target = install(paths, Plan(180), tmp_path / "tasks", schtasks)
    task = target.read_text(encoding="utf-16")
    assert "<StartBoundary>2026-01-01T00:00:00</StartBoundary>" in task
    assert "<Interval>PT180M</Interval>" in task
    assert "<StartWhenAvailable>true</StartWhenAvailable>" in task
    assert f'--home "{paths.root}" run --scheduled' in task
    assert schtasks.calls == [["/Create", "/TN", TASK_NAME, "/XML", str(target), "/F"]]
    assert installed(tmp_path / "tasks") == Installed(180, program())


def test_a_once_a_day_task_has_no_repeat(tmp_path: Path) -> None:
    install(Paths(tmp_path), Plan(MINUTES_PER_DAY), tmp_path, Schtasks())
    assert "<Repetition>" not in task_path(tmp_path).read_text(encoding="utf-16")
    found = installed(tmp_path)
    assert found is not None
    assert found.every_minutes == MINUTES_PER_DAY


def test_a_refused_task_says_so(tmp_path: Path) -> None:
    with pytest.raises(ScheduleError, match="Windows didn't accept"):
        install(Paths(tmp_path), Plan(60), tmp_path, Schtasks(refuse=True))


def test_removing_deletes_the_task_and_its_file(tmp_path: Path) -> None:
    install(Paths(tmp_path), Plan(60), tmp_path, Schtasks())
    schtasks = Schtasks()
    assert remove(tmp_path, schtasks)
    assert schtasks.calls == [["/Delete", "/TN", TASK_NAME, "/F"]]
    assert installed(tmp_path) is None
    assert not remove(tmp_path, Schtasks())


def test_a_damaged_task_file_is_reported(tmp_path: Path) -> None:
    task_path(tmp_path).write_text("not a task", encoding="utf-16")
    with pytest.raises(ScheduleError, match="damaged"):
        installed(tmp_path)


def test_the_scheduled_run_can_name_its_data_folder(tmp_path: Path) -> None:
    args = build_parser().parse_args(["--home", str(tmp_path), "run", "--scheduled"])
    assert args.home == tmp_path
