import os
import plistlib
import shlex
import subprocess
import sys
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from xml.parsers.expat import ExpatError

from truapply.core.errors import ScheduleError
from truapply.core.paths import HOME_ENV, Paths

LABEL = "com.truapply.run"
LAUNCHCTL = "/bin/launchctl"
SECONDS_PER_MINUTE = 60
MINUTES_PER_HOUR = 60
MINUTES_PER_DAY = 24 * MINUTES_PER_HOUR
FALLBACK_PATH = "/usr/local/bin:/usr/bin:/bin"
TIMEOUT_S = 30

Runner = Callable[[Sequence[str]], int]


@dataclass(frozen=True)
class Plan:
    every_minutes: int


@dataclass(frozen=True)
class Installed:
    every_minutes: int
    program: Path


def launchctl(arguments: Sequence[str]) -> int:
    completed = subprocess.run(  # noqa: S603
        [LAUNCHCTL, *arguments], capture_output=True, check=False, timeout=TIMEOUT_S
    )
    return completed.returncode


def agents_dir() -> Path:
    return Path.home() / "Library" / "LaunchAgents"


def plist_path(agents: Path) -> Path:
    return agents / f"{LABEL}.plist"


def run_command() -> list[str]:
    return [sys.executable, "-m", "truapply", "run", "--scheduled"]


def launch_agent(paths: Paths, plan: Plan) -> dict[str, object]:
    return {
        "Label": LABEL,
        "ProgramArguments": run_command(),
        "StartCalendarInterval": times_of_day(plan),
        "EnvironmentVariables": {
            "PATH": os.environ.get("PATH", FALLBACK_PATH),
            HOME_ENV: str(paths.root),
        },
        "StandardOutPath": str(paths.log),
        "StandardErrorPath": str(paths.log),
        "ProcessType": "Background",
        "LowPriorityIO": True,
    }


def times_of_day(plan: Plan) -> list[dict[str, int]]:
    starts = range(0, MINUTES_PER_DAY, plan.every_minutes)
    return [
        {"Hour": start // MINUTES_PER_HOUR, "Minute": start % MINUTES_PER_HOUR} for start in starts
    ]


def next_run(plan: Plan, now: datetime) -> datetime:
    midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
    gap = timedelta(minutes=plan.every_minutes)
    upcoming = midnight + ((now - midnight) // gap + 1) * gap
    return min(upcoming, midnight + timedelta(days=1))


def every(minutes: int) -> str:
    hours, rest = divmod(minutes, MINUTES_PER_HOUR)
    parts = [f"{hours} h" if hours else "", f"{rest} min" if rest else ""]
    return " ".join(part for part in parts if part)


def _cron_times(plan: Plan) -> str:
    minutes = plan.every_minutes
    if minutes < MINUTES_PER_HOUR:
        return f"*/{minutes} * * * *"
    return f"0 */{minutes // MINUTES_PER_HOUR} * * *"


def cron_line(paths: Paths, plan: Plan) -> str:
    home = f"{HOME_ENV}={shlex.quote(str(paths.root))}"
    log = shlex.quote(str(paths.log))
    return f"{_cron_times(plan)} {home} {shlex.join(run_command())} >> {log} 2>&1"


def _service() -> tuple[str, str]:
    domain = f"gui/{os.getuid()}"
    return domain, f"{domain}/{LABEL}"


def install(paths: Paths, plan: Plan, agents: Path, runner: Runner = launchctl) -> Path:
    agents.mkdir(parents=True, exist_ok=True)
    target = plist_path(agents)
    target.write_bytes(plistlib.dumps(launch_agent(paths, plan)))
    domain, service = _service()
    runner(["bootout", service])
    if runner(["bootstrap", domain, str(target)]) != 0:
        raise ScheduleError("macOS didn't accept the schedule.")
    return target


def remove(agents: Path, runner: Runner = launchctl) -> bool:
    target = plist_path(agents)
    runner(["bootout", _service()[1]])
    existed = target.is_file()
    target.unlink(missing_ok=True)
    return existed


def installed(agents: Path) -> Installed | None:
    target = plist_path(agents)
    if not target.is_file():
        return None
    try:
        agent = plistlib.loads(target.read_bytes())
    except (plistlib.InvalidFileException, ExpatError, ValueError) as error:
        raise ScheduleError(f"The schedule file is damaged: {target}") from error
    program = agent.get("ProgramArguments") if isinstance(agent, dict) else None
    minutes = _every_minutes(agent) if isinstance(agent, dict) else None
    if not isinstance(program, list) or not program or minutes is None:
        raise ScheduleError(f"The schedule file is damaged: {target}")
    return Installed(minutes, Path(str(program[0])))


def _minute_of_day(time: object) -> int | None:
    if not isinstance(time, dict):
        return None
    hour, minute = time.get("Hour"), time.get("Minute")
    if not isinstance(hour, int) or not isinstance(minute, int):
        return None
    return hour * MINUTES_PER_HOUR + minute


def _every_minutes(agent: dict[str, object]) -> int | None:
    interval = agent.get("StartInterval")
    if isinstance(interval, int):
        return interval // SECONDS_PER_MINUTE
    times = agent.get("StartCalendarInterval")
    if not isinstance(times, list) or not times:
        return None
    if len(times) == 1:
        return MINUTES_PER_DAY
    first, second = _minute_of_day(times[0]), _minute_of_day(times[1])
    return second - first if first is not None and second is not None else None
