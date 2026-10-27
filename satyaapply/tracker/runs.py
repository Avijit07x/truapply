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
from satyaapply.core.errors import SatyaApplyError
from satyaapply.core.paths import AUTOMATIC_RUN, MANUAL_RUN, Paths
from satyaapply.core.profile import MAX_JOBS_PER_RUN, Settings, load
from satyaapply.tracker.body import Body, flag, number
from satyaapply.tracker.detail import iso
from satyaapply.tracker.responses import Response, bad_request, not_found, ok
from satyaapply.tracker.routes import Route, route

COMMAND_PREFIX: tuple[str, ...] = (sys.executable, "-m", "satyaapply", "run")
MIN_LIMIT = 1
MAX_LIMIT = MAX_JOBS_PER_RUN
TAIL_LINES = 200
RECENT_LOGS = 5
STOP_WAIT_SECONDS = 10
LOG_NAME = re.compile(r"^\d{8}-\d{6}-\d{6}\.log$")
ALREADY_RUNNING = "A run is already going."
RUN_KINDS = {AUTOMATIC_RUN: "automatic", MANUAL_RUN: "manual"}


@dataclass(frozen=True)
class Choice:
    limit: int
    search: bool
    job: int | None = None
    find: bool = True
    score: tuple[int, ...] = ()


@dataclass(frozen=True)
class Run:
    process: subprocess.Popen[bytes]
    log: Path
    started: datetime
    choice: Choice

    @property
    def running(self) -> bool:
        return self.process.poll() is None


class Registry:
    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.current: Run | None = None
        self.waiting: set[int] = set()
        self.watching = False

    def active(self) -> Run | None:
        run = self.current
        return run if run is not None and run.running else None


REGISTRY = Registry()


def command(choice: Choice) -> list[str]:
    if choice.job is not None:
        return [*COMMAND_PREFIX, "--job", str(choice.job)]
    if choice.score:
        return [*COMMAND_PREFIX, "--score", *(str(job_id) for job_id in choice.score)]
    search = [] if choice.search else ["--no-search"]
    find = [] if choice.find else ["--no-find"]
    return [*COMMAND_PREFIX, "--limit", str(choice.limit), *search, *find]


def _spawn(arguments: list[str], log: Path) -> subprocess.Popen[bytes]:
    log.parent.mkdir(parents=True, exist_ok=True)
    environment = {**os.environ, "PYTHONUNBUFFERED": "1"}
    with log.open("wb") as out:
        return subprocess.Popen(  # noqa: S603
            arguments,
            stdin=subprocess.DEVNULL,
            stdout=out,
            stderr=subprocess.STDOUT,
            env=environment,
        )


def _launch(paths: Paths, choice: Choice) -> Run:
    started = utc_now()
    log = paths.run_log(started)
    REGISTRY.current = Run(_spawn(command(choice), log), log, started, choice)
    return REGISTRY.current


def start(paths: Paths, choice: Choice) -> Run | None:
    with REGISTRY.lock:
        if REGISTRY.active() is not None:
            return None
        return _launch(paths, choice)


def _scoring_choice(job_ids: tuple[int, ...]) -> Choice:
    return Choice(len(job_ids), search=False, score=job_ids)


def _score_when_free(paths: Paths) -> None:
    while True:
        busy = REGISTRY.active()
        if busy is not None:
            busy.process.wait()
            continue
        with REGISTRY.lock:
            if REGISTRY.active() is not None:
                continue
            waiting = tuple(sorted(REGISTRY.waiting))
            REGISTRY.waiting.clear()
            REGISTRY.watching = False
            if waiting:
                _launch(paths, _scoring_choice(waiting))
            return


def score(paths: Paths, job_ids: list[int]) -> None:
    with REGISTRY.lock:
        if REGISTRY.active() is None:
            _launch(paths, _scoring_choice(tuple(job_ids)))
            return
        REGISTRY.waiting.update(job_ids)
        if not REGISTRY.watching:
            REGISTRY.watching = True
            threading.Thread(target=_score_when_free, args=(paths,), daemon=True).start()


def scoring_now() -> list[int]:
    with REGISTRY.lock:
        run = REGISTRY.active()
        now = set(run.choice.score) if run is not None else set()
        return sorted(now | REGISTRY.waiting)


def stop() -> None:
    with REGISTRY.lock:
        REGISTRY.waiting.clear()
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
    folder = paths.runs
    if not folder.is_dir():
        return []
    named = (item for item in folder.iterdir() if LOG_NAME.match(item.name))
    return sorted(named, key=_finished_at, reverse=True)[:RECENT_LOGS]


def kind_of(log: Path) -> str | None:
    with log.open(encoding="utf-8", errors="replace") as lines:
        first = lines.readline().strip()
    return RUN_KINDS.get(first)


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


def _saved_limit(paths: Paths) -> int:
    try:
        return load(paths).settings.jobs_per_run
    except SatyaApplyError:
        return Settings().jobs_per_run


def state(paths: Paths) -> dict[str, object]:
    logs = [
        {"name": log.name, "finishedAt": iso(_finished_at(log)), "kind": kind_of(log)}
        for log in recent_logs(paths)
    ]
    limits = {"min": MIN_LIMIT, "max": MAX_LIMIT, "default": _saved_limit(paths)}
    return _current(REGISTRY.current) | {"logs": logs, "limits": limits}


def _show(_db: sqlite3.Connection, paths: Paths, _match: re.Match[str], _body: Body) -> Response:
    return ok(state(paths))


def _log(_db: sqlite3.Connection, paths: Paths, match: re.Match[str], _body: Body) -> Response:
    name = match.group(1)
    log = paths.runs / name
    if not LOG_NAME.match(name) or not log.is_file():
        return not_found("No such run log.")
    finished = iso(_finished_at(log))
    return ok({"name": name, "finishedAt": finished, "kind": kind_of(log), "lines": tail(log)})


def parse_choice(body: Body) -> Choice | None:
    limit = number(body, "limit")
    search = flag(body, "search")
    if limit is None or search is None:
        return None
    return Choice(min(max(limit, MIN_LIMIT), MAX_LIMIT), search)


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
