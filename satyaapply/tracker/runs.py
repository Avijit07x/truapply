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

from satyaapply.core import schedule
from satyaapply.core.clock import utc_now
from satyaapply.core.errors import SatyaApplyError
from satyaapply.core.locks import is_held
from satyaapply.core.models import RunStage
from satyaapply.core.paths import AUTOMATIC_RUN, MANUAL_RUN, RUN_LOG_STAMP, Paths
from satyaapply.core.profile import MAX_JOBS_PER_RUN, Settings, load
from satyaapply.tracker import automatic
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
SUMMARY = "Summary"
FAILED = "✘"
STAGE_LINES = (
    ("Checking company career pages", RunStage.FIND),
    ("Checking Wellfound", RunStage.FIND),
    ("Scoring ", RunStage.SCORE),
    ("Tailoring your resume", RunStage.TAILOR),
)


@dataclass(frozen=True)
class Choice:
    limit: int
    search: bool
    job: int | None = None
    find: bool = True
    score: tuple[int, ...] = ()
    companies: bool = False
    only: RunStage | None = None


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
    companies = ["--find-companies"] if choice.companies else []
    only = ["--only", str(choice.only)] if choice.only else []
    return [*COMMAND_PREFIX, "--limit", str(choice.limit), *search, *find, *companies, *only]


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
        if REGISTRY.active() is not None or is_held(paths.lock):
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


def outcome_of(log: Path) -> str:
    text = log.read_text(encoding="utf-8", errors="replace")
    if SUMMARY in text.splitlines():
        return "done"
    return "failed" if FAILED in text else "stopped"


def kind_of(log: Path) -> str | None:
    with log.open(encoding="utf-8", errors="replace") as lines:
        first = lines.readline().strip()
    return RUN_KINDS.get(first)


def _finished_at(log: Path) -> datetime:
    return datetime.fromtimestamp(log.stat().st_mtime, UTC)


def _started_at(log: Path) -> datetime:
    return datetime.strptime(log.stem, RUN_LOG_STAMP).replace(tzinfo=UTC)


def _outside_run(paths: Paths) -> dict[str, object] | None:
    logs = recent_logs(paths)
    if not logs or not is_held(paths.lock):
        return None
    log = logs[0]
    return {
        "running": True,
        "startedAt": iso(_started_at(log)),
        "exitCode": None,
        "log": tail(log),
        "stoppable": False,
    }


def _current(paths: Paths, run: Run | None) -> dict[str, object]:
    if run is None or not run.running:
        outside = _outside_run(paths)
        if outside is not None:
            return outside
    if run is None:
        return {
            "running": False,
            "startedAt": None,
            "exitCode": None,
            "log": [],
            "stoppable": False,
        }
    return {
        "running": run.running,
        "startedAt": iso(run.started),
        "exitCode": run.process.returncode,
        "log": tail(run.log),
        "stoppable": run.running,
    }


def _saved_limit(paths: Paths) -> int:
    try:
        return load(paths).settings.jobs_per_run
    except SatyaApplyError:
        return Settings().jobs_per_run


def _going_log(paths: Paths, recent: list[Path]) -> str | None:
    run = REGISTRY.active()
    if run is not None:
        return run.log.name
    return recent[0].name if recent and is_held(paths.lock) else None


def next_automatic() -> datetime | None:
    every = automatic.current()["everyMinutes"]
    if not isinstance(every, int):
        return None
    return schedule.next_run(schedule.Plan(every), utc_now().astimezone())


def _shown_log(log: Path, going: str | None) -> dict[str, object]:
    running = log.name == going
    return {
        "name": log.name,
        "finishedAt": iso(_finished_at(log)),
        "kind": kind_of(log),
        "running": running,
        "outcome": None if running else outcome_of(log),
    }


def _stage_now(current: dict[str, object]) -> str | None:
    lines = current["log"]
    if not current["running"] or not isinstance(lines, list):
        return None
    stage = stage_of([str(line) for line in lines])
    return str(stage) if stage else None


def latest_start(paths: Paths) -> datetime | None:
    recent = recent_logs(paths)
    return _started_at(recent[0]) if recent else None


def state(paths: Paths) -> dict[str, object]:
    recent = recent_logs(paths)
    going = _going_log(paths, recent)
    upcoming = next_automatic()
    current = _current(paths, REGISTRY.current)
    return current | {
        "stage": _stage_now(current),
        "logs": [_shown_log(log, going) for log in recent],
        "nextAutomatic": iso(upcoming) if upcoming else None,
        "limits": {"min": MIN_LIMIT, "max": MAX_LIMIT, "default": _saved_limit(paths)},
    }


def _show(_db: sqlite3.Connection, paths: Paths, _match: re.Match[str], _body: Body) -> Response:
    return ok(state(paths))


def _log(_db: sqlite3.Connection, paths: Paths, match: re.Match[str], _body: Body) -> Response:
    name = match.group(1)
    log = paths.runs / name
    if not LOG_NAME.match(name) or not log.is_file():
        return not_found("No such run log.")
    finished = iso(_finished_at(log))
    return ok({"name": name, "finishedAt": finished, "kind": kind_of(log), "lines": tail(log)})


def _stage(body: Body) -> RunStage | None:
    wanted = body.get("only")
    return RunStage(wanted) if isinstance(wanted, str) and wanted in set(RunStage) else None


def parse_choice(body: Body) -> Choice | None:
    limit = number(body, "limit")
    search = flag(body, "search")
    if limit is None or search is None:
        return None
    return Choice(min(max(limit, MIN_LIMIT), MAX_LIMIT), search, only=_stage(body))


def stage_of(lines: list[str]) -> RunStage | None:
    for line in reversed(lines):
        for start, stage in STAGE_LINES:
            if line.startswith(start):
                return stage
    return None


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
