from pathlib import Path

from satyaapply.core import schedule
from satyaapply.tracker import automatic


def test_tests_never_reach_the_real_launch_agents_folder() -> None:
    real = Path.home() / "Library" / "LaunchAgents"
    assert schedule.agents_dir() != real
    assert automatic.agents() != real
    assert schedule.LAUNCHCTL != "/bin/launchctl"
