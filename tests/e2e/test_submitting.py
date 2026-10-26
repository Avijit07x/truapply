import sqlite3
from collections.abc import Iterator, Sequence
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

import pytest
from playwright.sync_api import Page

from satyaapply.apply.flow import HUMAN_CHECK_NOTE, ApplyRequest, Attempt, apply
from satyaapply.core.models import Job, Status
from satyaapply.core.paths import Paths
from satyaapply.resume.contract import Rendered, Resume
from satyaapply.resume.tailor import Tailored, TailorRequest
from satyaapply.run import applying
from satyaapply.run.applying import prepare
from satyaapply.run.context import RunContext
from satyaapply.store import jobs, records, trust
from satyaapply.store.db import connect
from satyaapply.store.jobs import AttemptRecord, ScoreUpdate, StatusChange
from tests.e2e.test_form_filler import FORM, FakeAnswerer, submission
from tests.unit import samples
from tests.unit.test_master import CountingResume

pytestmark = pytest.mark.e2e

NOW = datetime(2026, 10, 25, 12, 0, tzinfo=UTC)
RESUME_NAME = "Asha_Rao_Resume.pdf"


@pytest.fixture
def db(tmp_path: Path) -> Iterator[sqlite3.Connection]:
    connection = connect(tmp_path / "test.db")
    yield connection
    connection.close()


@pytest.fixture
def submitted() -> list[object]:
    return []


@pytest.fixture
def seen(
    db: sqlite3.Connection, submitted: list[object], monkeypatch: pytest.MonkeyPatch
) -> list[tuple[Status, object]]:
    found: list[tuple[Status, object]] = []
    sent = submitted

    def watched(page: Page, request: ApplyRequest) -> Attempt:
        def before() -> None:
            request.before_submit()
            record = records.find(db, 1)
            assert record is not None
            found.append((record.job.status, submission(page)))

        attempt = apply(page, replace(request, before_submit=before), FakeAnswerer())
        sent.append(submission(page))
        return attempt

    def tailored(_resume: Resume, request: TailorRequest) -> Tailored:
        pdf = request.out_dir / RESUME_NAME
        pdf.parent.mkdir(parents=True, exist_ok=True)
        pdf.write_bytes(b"%PDF-1.4 tailored")
        return Tailored(pdf, "", False, (), ())

    monkeypatch.setattr(applying, "apply", watched)
    monkeypatch.setattr(applying, "tailor", tailored)
    monkeypatch.setattr(applying, "still_open", lambda picks: [None] * len(picks))
    monkeypatch.setattr(applying, "_pause", lambda _source: None)
    return found


def run_context(tmp_path: Path) -> RunContext:
    paths = Paths(tmp_path / "home")
    paths.ensure()
    return RunContext(
        paths,
        samples.profile(tmp_path / "master.tex"),
        CountingResume(),
        Rendered(tmp_path / "m.pdf", 1),
        lambda: NOW,
        dry_run=False,
    )


def local_job(external_id: str = "42", query: str = "") -> Job:
    return replace(samples.job(external_id=external_id), apply_url=f"{FORM.as_uri()}{query}")


def approve(db: sqlite3.Connection, tmp_path: Path, query: str = "") -> None:
    jobs.add_many(db, [local_job(query=query)], NOW)
    pdf = tmp_path / RESUME_NAME
    pdf.write_bytes(b"%PDF-1.4 approved")
    jobs.record_attempt(db, 1, AttemptRecord(Status.READY, NOW, "filled", (), pdf))
    jobs.set_status(db, 1, StatusChange(Status.APPROVED, NOW))


def scored(db: sqlite3.Connection, scores: Sequence[int]) -> None:
    jobs.add_many(db, [local_job(str(score)) for score in scores], NOW)
    for job_id, score in enumerate(scores, start=1):
        jobs.save_score(db, job_id, ScoreUpdate(score, Status.SCORED, NOW, "fits"))


def test_an_approved_job_is_sent_for_real_after_marking_it_as_sending(
    db: sqlite3.Connection,
    tmp_path: Path,
    seen: list[tuple[Status, object]],
    submitted: list[object],
) -> None:
    approve(db, tmp_path)
    [done] = prepare(db, run_context(tmp_path), 5, show=False)
    assert (done.attempt.status, done.attempt.note) == (Status.APPLIED, "submitted and confirmed")
    assert seen == [(Status.SUBMITTING, None)]
    [form] = submitted
    assert isinstance(form, dict)
    assert form["resume"] == RESUME_NAME
    record = records.find(db, 1)
    assert record is not None
    assert record.job.status is Status.APPLIED
    assert db.execute("select auto_submitted from jobs where id = 1").fetchone()[0] == 0


def test_a_human_check_after_submit_is_left_for_the_user(
    db: sqlite3.Connection, tmp_path: Path, seen: list[tuple[Status, object]]
) -> None:
    approve(db, tmp_path, "?captcha=1")
    [done] = prepare(db, run_context(tmp_path), 5, show=False)
    assert (done.attempt.status, done.attempt.note) == (Status.FINISH, HUMAN_CHECK_NOTE)
    assert [status for status, _ in seen] == [Status.SUBMITTING]


def test_with_auto_submit_on_only_strong_matches_are_sent(
    db: sqlite3.Connection, tmp_path: Path, seen: list[tuple[Status, object]]
) -> None:
    scored(db, [85, 70])
    trust.set_auto_submit(db, True, NOW)
    done = prepare(db, run_context(tmp_path), 5, show=False)
    assert [item.attempt.status for item in done] == [Status.APPLIED, Status.READY]
    flags = db.execute("select auto_submitted from jobs order by id").fetchall()
    assert [row[0] for row in flags] == [1, 0]
    assert len(seen) == 1


def test_without_auto_submit_scored_jobs_stay_dry_runs(
    db: sqlite3.Connection, tmp_path: Path, seen: list[tuple[Status, object]]
) -> None:
    scored(db, [95])
    [done] = prepare(db, run_context(tmp_path), 5, show=False)
    assert done.attempt.status is Status.READY
    assert seen == []
