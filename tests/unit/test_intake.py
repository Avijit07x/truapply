from collections.abc import Sequence
from contextlib import closing
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

import pytest

from satyaapply.core.models import Board, Job, Status
from satyaapply.core.notes import OUTSIDE_SEARCH_NOTE, WRONG_TITLE_NOTE
from satyaapply.sources import intake
from satyaapply.sources.ats import PollResult
from satyaapply.store import jobs, records
from satyaapply.store.db import connect
from satyaapply.store.jobs import StatusChange
from tests.unit import samples

NOW = datetime(2026, 10, 27, 9, 0, tzinfo=UTC)
FRONTEND = samples.job(external_id="greenhouse/northwind/1")
OFFICE = replace(samples.job(external_id="greenhouse/northwind/2"), title="Office Manager")
SALES = replace(samples.job(external_id="greenhouse/northwind/3"), title="Sales Executive")


@pytest.fixture
def db_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    def polled(checked: Sequence[Board]) -> PollResult:
        return PollResult([FRONTEND, OFFICE, SALES], list(checked), [], [])

    monkeypatch.setattr(intake, "poll", polled)
    return tmp_path / "jobs.db"


def stored(path: Path, job_id: int) -> tuple[Job, str | None]:
    with closing(connect(path)) as db:
        record = records.find(db, job_id)
        note = db.execute("select note from jobs where id = ?", (job_id,)).fetchone()[0]
    assert record is not None
    return record.job, note


def titles_with(word: str) -> intake.Wants:
    return intake.Wants(
        skip=lambda job: None if word in job.title else WRONG_TITLE_NOTE,
        keep=lambda job: "Sales" not in job.title,
    )


def test_every_job_found_is_kept_and_only_fitting_ones_are_queued(db_path: Path) -> None:
    with closing(connect(db_path)) as db:
        took = intake.take_in(db, [], titles_with("Frontend"), NOW)
    assert (took.found, took.kept, took.added) == (3, 1, 1)
    queued, _ = stored(db_path, 1)
    outside, note = stored(db_path, 2)
    assert queued.status is Status.NEW
    assert outside.status is Status.SKIPPED
    assert note == WRONG_TITLE_NOTE
    assert outside.description == ""
    with closing(connect(db_path)) as db:
        assert db.execute("select count(*) from jobs").fetchone()[0] == 2


def test_a_job_that_fits_after_a_change_goes_back_in_the_queue(db_path: Path) -> None:
    with closing(connect(db_path)) as db:
        intake.take_in(db, [], titles_with("Frontend"), NOW)
        took = intake.take_in(db, [], titles_with("Manager"), NOW)
    assert took.added == 1
    back, note = stored(db_path, 2)
    assert back.status is Status.NEW
    assert note is None
    assert back.description == OFFICE.description


def test_jobs_skipped_for_other_reasons_stay_skipped(db_path: Path) -> None:
    with closing(connect(db_path)) as db:
        intake.take_in(db, [], titles_with("Frontend"), NOW)
        jobs.set_status(db, 1, StatusChange(Status.SKIPPED, NOW, "score 30"))
        intake.take_in(db, [], titles_with("Frontend"), NOW)
    assert stored(db_path, 1)[0].status is Status.SKIPPED


def test_jobs_skipped_before_reasons_were_saved_get_their_reason_next_time(
    db_path: Path,
) -> None:
    with closing(connect(db_path)) as db:
        jobs.add_outside_search(db, [(OFFICE, OUTSIDE_SEARCH_NOTE)], NOW)
        intake.take_in(db, [], titles_with("Frontend"), NOW)
    assert stored(db_path, 1)[1] == WRONG_TITLE_NOTE
