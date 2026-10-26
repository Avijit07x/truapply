import os
import re
import sqlite3
import subprocess
import sys
import threading
from collections import deque
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from satyaapply.core.clock import utc_now
from satyaapply.core.paths import Paths
from satyaapply.tracker.body import Body, flag, number
from satyaapply.tracker.detail import iso
from satyaapply.tracker.responses import Response, bad_request, not_found, ok
from satyaapply.tracker.routes import Route, route

COMMAND_PREFIX: tuple[str, ...] = (sys.executable, "-m", "satyaapply", "run")
DEFAULT_LIMIT = 5
MIN_LIMIT = 1
MAX_LIMIT = 20
TAIL_LINES = 200
RECENT_LOGS = 5
STOP_WAIT_SECONDS = 10
STAMP = "%Y%m%d-%H%M%S-%f"
LOG_NAME = re.compile(r"^\d{8}-\d{6}-\d{6}\.log$")
ALREADY_RUNNING = "A run is already going."


@dataclass(frozen=True)
class Choice:
    limit: int
    search: bool
    send: bool = False


@dataclass(frozen=True)
class Run:
    process: subprocess.Popen[bytes]
    log: Path
    started: datetime

    @property
    def running(self) -> bool:
        return self.process.poll() is None


class Registry:
    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.current: Run | None = None

    def active(self) -> Run | None:
        run = self.current
        return run if run is not None and run.running else None


REGISTRY = Registry()


def runs_dir(paths: Paths) -> Path:
    return paths.root / "runs"


def command(choice: Choice) -> list[str]:
    search = [] if choice.search else ["--no-search"]
    send = ["--send"] if choice.send else []
    return [*COMMAND_PREFIX, "--limit", str(choice.limit), *search, *send]


def start(paths: Paths, choice: Choice) -> Run | None:
    with REGISTRY.lock:
        if REGISTRY.active() is not None:
            return None
        folder = runs_dir(paths)
        folder.mkdir(parents=True, exist_ok=True)
        started = utc_now()
        log = folder / f"{started.strftime(STAMP)}.log"
        environment = {**os.environ, "PYTHONUNBUFFERED": "1"}
        with log.open("wb") as out:
            process = subprocess.Popen(  # noqa: S603
                command(choice),
                stdin=subprocess.DEVNULL,
                stdout=out,
                stderr=subprocess.STDOUT,
                env=environment,
            )
        REGISTRY.current = Run(process, log, started)
        return REGISTRY.current


def stop() -> None:
    run = REGISTRY.active()
    if run is None:
        return
    run.process.terminate()
    try:
        run.process.wait(STOP_WAIT_SECONDS)
    except subprocess.TimeoutExpired:
        run.process.kill()
        run.process.wait()


def tail(log: Path) -> list[str]:
    if not log.is_file():
        return []
    with log.open(encoding="utf-8", errors="replace") as lines:
        return [line.rstrip("\n") for line in deque(lines, maxlen=TAIL_LINES)]


def recent_logs(paths: Paths) -> list[Path]:
    folder = runs_dir(paths)
    if not folder.is_dir():
        return []
    named = (item for item in folder.iterdir() if LOG_NAME.match(item.name))
    return sorted(named, key=lambda item: item.name, reverse=True)[:RECENT_LOGS]


def _finished_at(log: Path) -> datetime:
    return datetime.fromtimestamp(log.stat().st_mtime, UTC)


def _current(run: Run | None) -> dict[str, object]:
    if run is None:
        return {"running": False, "startedAt": None, "exitCode": None, "log": []}
    return {
        "running": run.running,
        "startedAt": iso(run.started),
        "exitCode": run.process.returncode,
        "log": tail(run.log),
    }


def state(paths: Paths) -> dict[str, object]:
    logs = [{"name": log.name, "finishedAt": iso(_finished_at(log))} for log in recent_logs(paths)]
    limits = {"min": MIN_LIMIT, "max": MAX_LIMIT, "default": DEFAULT_LIMIT}
    return _current(REGISTRY.current) | {"logs": logs, "limits": limits}


def _show(_db: sqlite3.Connection, paths: Paths, _match: re.Match[str], _body: Body) -> Response:
    return ok(state(paths))


def _log(_db: sqlite3.Connection, paths: Paths, match: re.Match[str], _body: Body) -> Response:
    name = match.group(1)
    log = runs_dir(paths) / name
    if not LOG_NAME.match(name) or not log.is_file():
        return not_found("No such run log.")
    return ok({"name": name, "finishedAt": iso(_finished_at(log)), "lines": tail(log)})


def parse_choice(body: Body) -> Choice | None:
    limit = number(body, "limit")
    search, send = flag(body, "search"), flag(body, "send")
    if limit is None or search is None or send is None:
        return None
    return Choice(min(max(limit, MIN_LIMIT), MAX_LIMIT), search, send)


def _start(_db: sqlite3.Connection, paths: Paths, _match: re.Match[str], body: Body) -> Response:
    choice = parse_choice(body)
    if choice is None:
        return bad_request(f"Enter how many jobs to run, from {MIN_LIMIT} to {MAX_LIMIT}.")
    if start(paths, choice) is None:
        return bad_request(ALREADY_RUNNING)
    return ok(state(paths))


def _stop(_db: sqlite3.Connection, paths: Paths, _match: re.Match[str], _body: Body) -> Response:
    stop()
    return ok(state(paths))


GET: tuple[Route, ...] = (
    route("/runs", _show),
    route("/runs/log/([^/]+)", _log),
)
POST: tuple[Route, ...] = (
    route("/runs/start", _start),
    route("/runs/stop", _stop),
)
