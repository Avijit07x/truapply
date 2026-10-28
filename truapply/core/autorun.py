import sys
from pathlib import Path

from truapply.core import schedule, tasks
from truapply.core.paths import Paths
from truapply.core.schedule import Installed, Plan, Runner

WINDOWS = sys.platform == "win32"
SUPPORTED = WINDOWS or sys.platform == "darwin"


def folder() -> Path:
    return tasks.folder() if WINDOWS else schedule.agents_dir()


def runner() -> Runner:
    return tasks.schtasks if WINDOWS else schedule.launchctl


def install(paths: Paths, plan: Plan, where: Path, run: Runner) -> Path:
    return (tasks.install if WINDOWS else schedule.install)(paths, plan, where, run)


def remove(where: Path, run: Runner) -> bool:
    return (tasks.remove if WINDOWS else schedule.remove)(where, run)


def installed(where: Path) -> Installed | None:
    return (tasks.installed if WINDOWS else schedule.installed)(where)
