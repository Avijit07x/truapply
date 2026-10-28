import os
import re
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path
from xml.sax.saxutils import escape, unescape

from truapply.core.errors import ScheduleError
from truapply.core.paths import Paths
from truapply.core.schedule import MINUTES_PER_DAY, Installed, Plan, Runner

TASK_NAME = "TruApply"
SCHTASKS = "schtasks"
TIMEOUT_S = 30
TASK_FILE = "truapply-task.xml"
INTERVAL = re.compile(r"<Interval>PT(\d+)M</Interval>")
COMMAND = re.compile(r"<Command>([^<]+)</Command>")


def schtasks(arguments: Sequence[str]) -> int:
    completed = subprocess.run(  # noqa: S603
        [SCHTASKS, *arguments], capture_output=True, check=False, timeout=TIMEOUT_S
    )
    return completed.returncode


def folder() -> Path:
    local = os.environ.get("LOCALAPPDATA")
    return (Path(local) if local else Path.home() / "AppData" / "Local") / TASK_NAME


def task_path(tasks: Path) -> Path:
    return tasks / TASK_FILE


def program() -> Path:
    windowless = Path(sys.executable).with_name("pythonw.exe")
    return windowless if windowless.is_file() else Path(sys.executable)


def _repeat(plan: Plan) -> str:
    if plan.every_minutes >= MINUTES_PER_DAY:
        return ""
    return (
        f"<Repetition><Interval>PT{plan.every_minutes}M</Interval>"
        "<Duration>P1D</Duration><StopAtDurationEnd>false</StopAtDurationEnd></Repetition>"
    )


def task_xml(paths: Paths, plan: Plan) -> str:
    arguments = f'-m truapply --home "{paths.root}" run --scheduled'
    return f"""<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <Triggers>
    <CalendarTrigger>
      <StartBoundary>2026-01-01T00:00:00</StartBoundary>
      {_repeat(plan)}
      <ScheduleByDay><DaysInterval>1</DaysInterval></ScheduleByDay>
    </CalendarTrigger>
  </Triggers>
  <Principals>
    <Principal id="Author">
      <LogonType>InteractiveToken</LogonType>
      <RunLevel>LeastPrivilege</RunLevel>
    </Principal>
  </Principals>
  <Settings>
    <StartWhenAvailable>true</StartWhenAvailable>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <ExecutionTimeLimit>PT4H</ExecutionTimeLimit>
    <Priority>7</Priority>
  </Settings>
  <Actions Context="Author">
    <Exec>
      <Command>{escape(str(program()))}</Command>
      <Arguments>{escape(arguments)}</Arguments>
    </Exec>
  </Actions>
</Task>
"""


def install(paths: Paths, plan: Plan, tasks: Path, runner: Runner) -> Path:
    tasks.mkdir(parents=True, exist_ok=True)
    target = task_path(tasks)
    target.write_text(task_xml(paths, plan), encoding="utf-16")
    if runner(["/Create", "/TN", TASK_NAME, "/XML", str(target), "/F"]) != 0:
        raise ScheduleError("Windows didn't accept the schedule.")
    return target


def remove(tasks: Path, runner: Runner) -> bool:
    target = task_path(tasks)
    runner(["/Delete", "/TN", TASK_NAME, "/F"])
    existed = target.is_file()
    target.unlink(missing_ok=True)
    return existed


def installed(tasks: Path) -> Installed | None:
    target = task_path(tasks)
    if not target.is_file():
        return None
    try:
        task = target.read_text(encoding="utf-16")
    except UnicodeError as error:
        raise ScheduleError(f"The schedule file is damaged: {target}") from error
    command = COMMAND.search(task)
    if command is None:
        raise ScheduleError(f"The schedule file is damaged: {target}")
    interval = INTERVAL.search(task)
    minutes = int(interval.group(1)) if interval else MINUTES_PER_DAY
    return Installed(minutes, Path(unescape(command.group(1))))
