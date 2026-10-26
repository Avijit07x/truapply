from collections.abc import Iterator
from contextlib import closing
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from satyaapply.core.models import Status
from satyaapply.core.paths import Paths
from satyaapply.store import jobs
from satyaapply.store.db import connect
from satyaapply.store.groups import Group
from satyaapply.store.jobs import StatusChange
from satyaapply.tracker.listing import CARDS_PER_COLUMN, COLUMNS
from satyaapply.tracker.server import TrackerServer
from tests.unit import samples
from tests.unit.tracker_api import SEEDED, get, ids_in, running, seed_every_group

NOW = datetime(2026, 10, 25, 12, 0, tzinfo=UTC)


@pytest.fixture
def tracker(tmp_path: Path) -> Iterator[TrackerServer]:
    paths = Paths(tmp_path)
    paths.ensure()
    with closing(connect(paths.database)) as db:
        seed_every_group(db, NOW)
    with running(paths) as server:
        yield server


def test_every_workflow_box_counts_exactly_the_jobs_it_links_to(tracker: TrackerServer) -> None:
    status, workflow = get(tracker, "/api/workflow")
    assert status == 200
    assert set(workflow["groups"]) == {group.value for group in Group}
    for group in Group:
        listed = get(tracker, f"/api/jobs?group={group}")[1]
        ids = [job["id"] for job in listed["jobs"]]
        assert ids == ids_in(group), group
        assert workflow["groups"][group] == listed["total"] == len(ids), group


def test_status_filters_match_the_summary_counts(tracker: TrackerServer) -> None:
    summary = get(tracker, "/api/summary")[1]
    assert summary["total"] == len(SEEDED)
    for status in Status:
        listed = get(tracker, f"/api/jobs?status={status}")[1]
        assert listed["total"] == summary["counts"].get(status, 0) == len(listed["jobs"])
        assert {job["status"] for job in listed["jobs"]} <= {status.value}
    assert get(tracker, "/api/jobs")[1]["total"] == len(SEEDED)


def test_unknown_filters_are_refused(tracker: TrackerServer) -> None:
    assert get(tracker, "/api/jobs?status=everything")[0] == 400
    assert get(tracker, "/api/jobs?group=everything")[0] == 400


def test_the_board_has_its_columns_in_order_with_their_totals(tracker: TrackerServer) -> None:
    board = get(tracker, "/api/board")[1]
    assert [column["status"] for column in board["columns"]] == [str(s) for s in COLUMNS]
    applied = next(column for column in board["columns"] if column["status"] == "applied")
    assert applied["total"] == 2
    assert [job["id"] for job in applied["jobs"]] == [19, 17]
    assert "too senior" in board["dismissReasons"]


def test_a_board_column_shows_only_the_newest_cards(tmp_path: Path) -> None:
    paths = Paths(tmp_path)
    paths.ensure()
    many = CARDS_PER_COLUMN + 4
    with closing(connect(paths.database)) as db:
        jobs.add_many(db, [samples.job(external_id=str(n)) for n in range(many)], NOW)
        for job_id in range(1, many + 1):
            at = NOW + timedelta(minutes=job_id)
            jobs.set_status(db, job_id, StatusChange(Status.READY, at, "filled"))
    with running(paths) as server:
        board = get(server, "/api/board")[1]
    ready = next(column for column in board["columns"] if column["status"] == "ready")
    assert ready["total"] == many
    assert [job["id"] for job in ready["jobs"]] == list(range(many, many - CARDS_PER_COLUMN, -1))
