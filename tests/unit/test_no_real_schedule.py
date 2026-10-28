from pathlib import Path

from truapply.core import schedule, tasks
from truapply.tracker import automatic


def test_tests_never_reach_the_real_launch_agents_folder() -> None:
    real = Path.home() / "Library" / "LaunchAgents"
    assert schedule.agents_dir() != real
    assert automatic.agents() != real
    assert schedule.LAUNCHCTL != "/bin/launchctl"


def test_tests_never_reach_the_real_windows_task_folder() -> None:
    assert tasks.folder() != Path.home() / "AppData" / "Local" / tasks.TASK_NAME
    assert tasks.schtasks(["/Query"]) == 0
