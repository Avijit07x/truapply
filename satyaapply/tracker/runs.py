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
from satyaapply.store.records import JobRecord
from satyaapply.tracker.html import e, empty, joined, page, section, when
from satyaapply.tracker.responses import Response, back_to, bad_request, html, not_found
from satyaapply.tracker.routes import Form, Route, route

COMMAND_PREFIX: tuple[str, ...] = (sys.executable, "-m", "satyaapply", "run")
DEFAULT_LIMIT = 5
MIN_LIMIT = 1
MAX_LIMIT = 20
TAIL_LINES = 200
RECENT_LOGS = 5
STOP_WAIT_SECONDS = 10
STAMP = "%Y%m%d-%H%M%S-%f"
LOG_NAME = re.compile(r"^\d{8}-\d{6}-\d{6}\.log$")
EXPLAIN = "Finds new jobs, scores them, fills forms, and sends the jobs you approved."
REFRESH = '<meta http-equiv="refresh" content="3">'
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


def tail(log: Path) -> str:
    if not log.is_file():
        return ""
    with log.open(encoding="utf-8", errors="replace") as lines:
        return "".join(deque(lines, maxlen=TAIL_LINES))


def recent_logs(paths: Paths) -> list[Path]:
    folder = runs_dir(paths)
    if not folder.is_dir():
        return []
    named = (item for item in folder.iterdir() if LOG_NAME.match(item.name))
    return sorted(named, key=lambda item: item.name, reverse=True)[:RECENT_LOGS]


def _finished_at(log: Path) -> datetime:
    return datetime.fromtimestamp(log.stat().st_mtime, UTC)


def _log_block(log: Path) -> str:
    text = tail(log)
    return f'<pre class="diff">{e(text)}</pre>' if text else empty("Nothing written yet.")


def _start_form(limit: int, search: bool) -> str:
    checked = " checked" if search else ""
    return (
        '<form method="post" action="/runs/start">'
        f'<label>How many jobs (1-20) <input type="number" name="limit" min="{MIN_LIMIT}" '
        f'max="{MAX_LIMIT}" value="{limit}" required></label>'
        f'<label><input type="checkbox" name="search" value="on"{checked}> '
        "Search for new jobs first</label>"
        '<label><input type="checkbox" name="send" value="on"> '
        "Really send the jobs I approved (otherwise everything stays a dry run)</label>"
        '<div class="button-row"><button>Run now</button></div></form>'
    )


def _stop_form() -> str:
    return (
        '<form method="post" action="/runs/stop" class="button-row">'
        '<button class="secondary">Stop</button></form>'
    )


def _running_view(run: Run) -> str:
    status = f"<p><strong>Running since {e(when(run.started))}.</strong></p>"
    return REFRESH + section("Run in progress", status + _stop_form() + _log_block(run.log))


def _finished_view(run: Run) -> str:
    status = f"<p><strong>Finished</strong> with exit code {e(run.process.returncode)}.</p>"
    return section("Last run", status + _log_block(run.log))


def _log_links(paths: Paths) -> str:
    items = [
        f'<li><a href="/runs/log/{e(log.name)}">{e(when(_finished_at(log)))}</a></li>'
        for log in recent_logs(paths)
    ]
    return section("Earlier runs", f"<ul>{joined(items)}</ul>") if items else ""


def _runs_page(
    _db: sqlite3.Connection, paths: Paths, _match: re.Match[str], _form: Form
) -> Response:
    run = REGISTRY.current
    if run is not None and run.running:
        return html(page("Run jobs", f"<h1>Run jobs</h1>{_running_view(run)}", "/runs"))
    intro = f'<p class="muted">{e(EXPLAIN)}</p>'
    last = _finished_view(run) if run is not None else ""
    body = section("Run now", intro + _start_form(DEFAULT_LIMIT, search=True))
    return html(page("Run jobs", f"<h1>Run jobs</h1>{body}{last}{_log_links(paths)}", "/runs"))


def _log_page(_db: sqlite3.Connection, paths: Paths, match: re.Match[str], _form: Form) -> Response:
    name = match.group(1)
    if not LOG_NAME.match(name):
        return not_found()
    log = runs_dir(paths) / name
    if not log.is_file():
        return not_found()
    body = f'<h1>Run log</h1><p><a href="/runs">Back to runs</a></p>{_log_block(log)}'
    return html(page("Run log", body, "/runs"))


def parse_choice(form: Form) -> Choice | None:
    try:
        limit = int(form.get("limit", ""))
    except ValueError:
        return None
    bounded = min(max(limit, MIN_LIMIT), MAX_LIMIT)
    return Choice(bounded, form.get("search") == "on", form.get("send") == "on")


def _start(_db: sqlite3.Connection, paths: Paths, _match: re.Match[str], form: Form) -> Response:
    choice = parse_choice(form)
    if choice is None:
        return bad_request("Enter how many jobs to run, from 1 to 20.")
    if start(paths, choice) is None:
        return bad_request(ALREADY_RUNNING)
    return back_to("/runs")


def _stop(_db: sqlite3.Connection, _paths: Paths, _match: re.Match[str], _form: Form) -> Response:
    stop()
    return back_to("/runs")


def _run_button() -> str:
    return (
        '<form method="post" action="/runs/start" class="button-row">'
        f'<input type="hidden" name="limit" value="{DEFAULT_LIMIT}">'
        '<input type="hidden" name="search" value="on">'
        "<button>▶ Run now</button></form>"
    )


def _home_status(paths: Paths) -> str:
    if REGISTRY.active() is not None:
        return '<p>Running… <a href="/runs">See progress</a></p>'
    logs = recent_logs(paths)
    if not logs:
        return empty("No runs yet.")
    finished = when(_finished_at(logs[0]))
    return f'<p class="muted">Last run finished {e(finished)}. <a href="/runs">See runs</a></p>'


def home_panel(_db: sqlite3.Connection, paths: Paths) -> str:
    body = f'<div class="card">{_run_button()}{_home_status(paths)}</div>'
    return section("Run jobs", body)


def job_controls(_db: sqlite3.Connection, _record: JobRecord) -> str:
    return ""


GET: tuple[Route, ...] = (
    route("/runs", _runs_page),
    route("/runs/log/(.+)", _log_page),
)
POST: tuple[Route, ...] = (
    route("/runs/start", _start),
    route("/runs/stop", _stop),
)
