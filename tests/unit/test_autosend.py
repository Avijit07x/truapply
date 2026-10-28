import json
import sqlite3
from contextlib import closing
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from http import HTTPStatus
from pathlib import Path
from typing import Any

import pytest

from satyaapply.core.models import Source, Status
from satyaapply.core.notes import AUTO_SENT_NOTE, UNCONFIRMED_NOTE
from satyaapply.core.paths import Paths
from satyaapply.core.profile import load, save
from satyaapply.run.lock import run_lock
from satyaapply.store import autosend, jobs
from satyaapply.store.autosend import SendState
from satyaapply.store.db import connect
from satyaapply.tracker import actions, extension
from satyaapply.tracker import autosend as routes
from satyaapply.tracker.body import Body
from satyaapply.tracker.routes import Incoming, Route, dispatch
from tests.unit import samples

NOW = datetime(2026, 10, 27, 9, 0, tzinfo=UTC)
BEFORE = NOW - timedelta(hours=1)


def ready(db: sqlite3.Connection, external_id: str, score: int, at: datetime = NOW) -> int:
    source, _, external_id = external_id.rpartition(":")
    source = source or Source.CAREER_PAGES
    jobs.add_many(db, [samples.job(Source(source), external_id)], at)
    key = f"{source}:{external_id}"
    with db:
        db.execute(
            "update jobs set status = ?, score = ?, resume_pdf = 'r.pdf', status_at = ?"
            " where key = ?",
            (Status.READY, score, at.isoformat(), key),
        )
    row: int = db.execute("select id from jobs where key = ?", (key,)).fetchone()[0]
    return row


@pytest.fixture
def paths(tmp_path: Path) -> Paths:
    paths = Paths(tmp_path / "home")
    paths.ensure()
    resume = tmp_path / "master.tex"
    resume.write_text("resume", encoding="utf-8")
    profile = samples.profile(resume)
    chosen = replace(profile.settings, auto_submit=True, auto_submit_score=70)
    save(paths, replace(profile, settings=chosen))
    return paths


def call(paths: Paths, table: tuple[Route, ...], path: str, body: Body | None = None) -> Any:
    with closing(connect(paths.database)) as db:
        response = dispatch(table, Incoming(db, paths, f"/api{path}", body or {}))
    assert response is not None
    assert response.status == HTTPStatus.OK, response.body
    return json.loads(response.body)


def test_only_strong_jobs_prepared_after_turning_it_on_are_sent_one_at_a_time(
    tmp_path: Path,
) -> None:
    with closing(connect(tmp_path / "jobs.db")) as db:
        old = ready(db, "old", 95, BEFORE)
        strong = ready(db, "strong", 90)
        ready(db, "weak", 60)
        ready(db, "wellfound:9", 99)
        assert autosend.claim_next(db, 70, NOW) is None
        autosend.turned_on(db, NOW - timedelta(minutes=1))
        first = autosend.claim_next(db, 70, NOW)
        assert first is not None and first.id == strong
        assert autosend.claim_next(db, 70, NOW) is None
        assert autosend.submitting(db, strong, NOW)
        assert not autosend.submitting(db, strong, NOW)
        autosend.mark_sent(db, strong)
        assert autosend.claim_next(db, 70, NOW) is None
        assert old != strong


def test_a_send_that_stalls_is_held_for_you_and_never_tried_again(tmp_path: Path) -> None:
    with closing(connect(tmp_path / "jobs.db")) as db:
        autosend.turned_on(db, BEFORE)
        first, second = ready(db, "a", 90), ready(db, "b", 85)
        assert autosend.claim_next(db, 70, NOW) is not None
        later = NOW + autosend.CLAIM_FOR + timedelta(minutes=1)
        found = autosend.claim_next(db, 70, later)
        assert found is not None and found.id == second
        assert autosend.state(db, first) is SendState.HELD
        assert autosend.submitting(db, second, later)
        autosend.hold(db, second, "the site showed a check")
        note = db.execute("select note from jobs where id = ?", (second,)).fetchone()[0]
        assert note == UNCONFIRMED_NOTE
        assert autosend.claim_next(db, 70, later) is None


def test_trust_is_lost_after_two_thumbs_down_in_the_last_ten_sent(tmp_path: Path) -> None:
    with closing(connect(tmp_path / "jobs.db")) as db:
        sent = [ready(db, str(n), 90) for n in range(3)]
        db.execute("update jobs set auto_submitted = 1, applied_at = status_at")
        db.execute("update jobs set feedback = -1 where id = ?", (sent[0],))
        db.commit()
        assert not autosend.lost_trust(db)
        db.execute("update jobs set feedback = -1 where id = ?", (sent[1],))
        db.commit()
        assert autosend.lost_trust(db)


def test_the_extension_gets_nothing_while_off_or_during_a_run(paths: Paths) -> None:
    with closing(connect(paths.database)) as db:
        autosend.turned_on(db, BEFORE)
        ready(db, "a", 90)
    with run_lock(paths):
        assert call(paths, routes.POST, "/extension/send/next") == {"job": None}
    profile = load(paths)
    off = replace(profile.settings, auto_submit=False)
    save(paths, replace(profile, settings=off))
    assert call(paths, routes.POST, "/extension/send/next") == {"job": None}
    save(paths, profile)
    job = call(paths, routes.POST, "/extension/send/next")["job"]
    assert job["url"] == "https://jobs.example.com/a"


def test_a_confirmed_send_is_marked_auto_submitted(paths: Paths) -> None:
    with closing(connect(paths.database)) as db:
        autosend.turned_on(db, BEFORE)
        job_id = ready(db, "a", 90)
    call(paths, routes.POST, "/extension/send/next")
    assert call(paths, routes.POST, f"/extension/jobs/{job_id}/submitting") == {"go": True}
    call(paths, extension.POST, f"/extension/jobs/{job_id}/applied", {"sent": []})
    with closing(connect(paths.database)) as db:
        row = db.execute("select status, auto_submitted, note from jobs").fetchone()
    assert tuple(row) == (Status.APPLIED, 1, AUTO_SENT_NOTE)


def test_two_thumbs_down_on_sent_jobs_turn_auto_submit_off(paths: Paths) -> None:
    with closing(connect(paths.database)) as db:
        sent = [ready(db, str(n), 90) for n in range(2)]
        db.execute("update jobs set auto_submitted = 1, applied_at = status_at")
        db.commit()
    for job_id in sent:
        call(paths, actions.POST, f"/jobs/{job_id}/thumbs", {"value": -1})
    assert not load(paths).settings.auto_submit


def test_send_these_queues_strong_ready_jobs_and_sends_them_even_during_a_run(
    paths: Paths,
) -> None:
    with closing(connect(paths.database)) as db:
        older = ready(db, "older", 74, BEFORE)
        ready(db, "low", 62, BEFORE)
    with run_lock(paths):
        assert call(paths, routes.POST, "/extension/send/next") == {"job": None}
        queued = call(paths, routes.POST, "/autosend/queue")
        assert queued == {"queued": 1, "below": 1, "score": 70}
        job = call(paths, routes.POST, "/extension/send/next")["job"]
    assert job["id"] == older


def test_send_these_asks_you_to_turn_auto_submit_on_first(paths: Paths) -> None:
    profile = load(paths)
    save(paths, replace(profile, settings=replace(profile.settings, auto_submit=False)))
    with closing(connect(paths.database)) as db:
        response = dispatch(routes.POST, Incoming(db, paths, "/api/autosend/queue", {}))
    assert response is not None and response.status == HTTPStatus.BAD_REQUEST


def test_a_send_confirmed_after_it_stopped_waiting_still_counts_as_auto_submitted(
    paths: Paths,
) -> None:
    with closing(connect(paths.database)) as db:
        autosend.turned_on(db, BEFORE)
        job_id = ready(db, "a", 90)
    call(paths, routes.POST, "/extension/send/next")
    call(paths, routes.POST, f"/extension/jobs/{job_id}/submitting")
    call(paths, routes.POST, f"/extension/jobs/{job_id}/held", {"why": "no thank-you yet"})
    call(paths, extension.POST, f"/extension/jobs/{job_id}/applied", {"sent": []})
    with closing(connect(paths.database)) as db:
        row = db.execute("select status, auto_submitted from jobs").fetchone()
    assert tuple(row) == (Status.APPLIED, 1)
