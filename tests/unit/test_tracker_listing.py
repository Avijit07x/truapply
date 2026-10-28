from collections.abc import Iterator
from contextlib import closing
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from satyaapply.core.models import Source, Status
from satyaapply.core.notes import WELLFOUND_NOTE
from satyaapply.core.paths import Paths
from satyaapply.core.profile import save
from satyaapply.store import groups, jobs
from satyaapply.store.browse import PAGE_SIZE
from satyaapply.store.db import connect
from satyaapply.store.groups import Group
from satyaapply.store.jobs import ScoreUpdate, StatusChange
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


def test_the_default_list_leaves_out_skipped_and_closed_jobs(tracker: TrackerServer) -> None:
    left_out = sum(1 for status, *_ in SEEDED if status in (Status.SKIPPED, Status.CLOSED))
    listed = get(tracker, "/api/jobs")[1]
    assert listed["total"] == len(SEEDED) - left_out == len(listed["jobs"])
    assert not {"skipped", "closed"} & {job["status"] for job in listed["jobs"]}
    assert get(tracker, "/api/jobs?group=found")[1]["total"] == len(SEEDED)


def test_show_all_lists_every_job_found_skipped_ones_too(tracker: TrackerServer) -> None:
    listed = get(tracker, "/api/jobs?show=all")[1]
    assert listed["total"] == len(SEEDED) == len(listed["jobs"])
    assert "skipped" in {job["status"] for job in listed["jobs"]}
    assert get(tracker, "/api/jobs?show=all&status=applied")[1]["total"] == sum(
        1 for status, *_ in SEEDED if status is Status.APPLIED
    )


@pytest.mark.parametrize(
    "query",
    [
        "show=everything",
        "status=everything",
        "group=everything",
        "sort=salary",
        "order=sideways",
        "page=0",
        "page=-1",
        "page=two",
        "page=%C2%B2",
        "page=1%C2%B2",
        "page=1000000",
        "minScore=101",
        "minScore=-1",
        "minScore=high",
        "source=myspace",
    ],
)
def test_unknown_filters_sorts_and_pages_are_refused(tracker: TrackerServer, query: str) -> None:
    assert get(tracker, f"/api/jobs?{query}")[0] == 400


@pytest.fixture
def many(tmp_path: Path) -> Iterator[TrackerServer]:
    paths = Paths(tmp_path)
    paths.ensure()
    count = PAGE_SIZE + 5
    picks = [samples.job(external_id=str(n), company=f"Company {n:03}") for n in range(count)]
    picks[7] = replace(picks[7], title="Design Engineer", company="Lumen_Labs")
    picks[9] = replace(picks[9], company="100% Remote")
    picks[11] = replace(picks[11], location="Pune, India")
    with closing(connect(paths.database)) as db:
        jobs.add_many(db, picks, NOW)
        jobs.save_score(db, 3, ScoreUpdate(91, Status.SCORED, NOW, "strong"))
        jobs.save_score(db, 4, ScoreUpdate(55, Status.SCORED, NOW, "weak"))
    with running(paths) as server:
        yield server


def ids(server: TrackerServer, query: str) -> list[int]:
    return [job["id"] for job in get(server, f"/api/jobs?{query}")[1]["jobs"]]


def test_the_list_comes_in_pages_and_a_page_past_the_end_is_the_last(many: TrackerServer) -> None:
    first = get(many, "/api/jobs")[1]
    assert (first["total"], first["page"], first["pageSize"]) == (PAGE_SIZE + 5, 1, PAGE_SIZE)
    assert len(first["jobs"]) == PAGE_SIZE
    second = get(many, "/api/jobs?page=2")[1]
    assert (second["page"], len(second["jobs"])) == (2, 5)
    assert not {job["id"] for job in first["jobs"]} & {job["id"] for job in second["jobs"]}
    assert get(many, "/api/jobs?page=40")[1]["page"] == 2


def test_search_matches_title_or_company_and_treats_wildcards_as_text(many: TrackerServer) -> None:
    assert ids(many, "q=design") == [8]
    assert ids(many, "q=lumen_labs") == [8]
    assert ids(many, "q=lumen%25labs") == []
    assert ids(many, "q=100%25") == [10]
    assert ids(many, "q=company%20001") == [2]


def test_sorting_by_score_puts_unscored_jobs_last_either_way(many: TrackerServer) -> None:
    assert ids(many, "sort=score")[:3] == [3, 4, 55]
    assert ids(many, "sort=score&order=asc")[:2] == [4, 3]
    assert ids(many, "sort=score&order=asc&page=2")[-1] == 1
    assert ids(many, "sort=company")[:3] == [10, 1, 2]
    assert ids(many, "sort=title&order=desc&q=engineer")[0] == 55


def test_the_board_has_its_columns_in_order_with_their_totals(tracker: TrackerServer) -> None:
    board = get(tracker, "/api/board")[1]
    assert [column["status"] for column in board["columns"]] == [str(s) for s in COLUMNS]
    applied = next(column for column in board["columns"] if column["status"] == "applied")
    assert applied["total"] == 1
    assert [job["id"] for job in applied["jobs"]] == ids_in(Group.APPLIED)
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


def test_column_filters_narrow_by_company_location_and_lowest_score(many: TrackerServer) -> None:
    assert ids(many, "company=lumen") == [8]
    assert ids(many, "location=pune") == [12]
    assert ids(many, "minScore=60") == [3]
    assert ids(many, "minScore=50") == [4, 3]
    assert ids(many, "minScore=50&company=company%20003") == [4]
    assert ids(many, "sort=location&order=desc")[0] == 12


def test_the_list_says_which_jobs_can_be_dismissed_and_why(many: TrackerServer) -> None:
    listed = get(many, "/api/jobs")[1]
    assert {"ready", "scored"} <= set(listed["dismissable"])
    assert not {"applied", "dismissed", "closed"} & set(listed["dismissable"])
    assert "too senior" in listed["dismissReasons"]


def test_wellfound_jobs_stay_out_of_career_jobs_and_have_their_own_list_and_counts(
    tmp_path: Path,
) -> None:
    paths = Paths(tmp_path)
    paths.ensure()
    (tmp_path / "master.tex").write_text("resume", encoding="utf-8")
    save(paths, samples.profile(tmp_path / "master.tex"))
    listed = replace(samples.job(Source.WELLFOUND, "9"), title="UI Engineer")
    with closing(connect(paths.database)) as db:
        jobs.add_many(db, [samples.job(external_id="1"), samples.job(external_id="2")], NOW)
        jobs.add_ready(db, [listed], NOW, WELLFOUND_NOTE)
    with running(paths) as server:
        career = get(server, "/api/jobs?show=all")[1]
        found = get(server, "/api/jobs?source=wellfound")[1]
        summary = get(server, "/api/summary")[1]
        board = get(server, "/api/board")[1]
    assert {job["source"] for job in career["jobs"]} == {"career_pages"}
    assert [job["title"] for job in found["jobs"]] == ["UI Engineer"]
    assert summary["counts"] == {"new": 2}
    assert summary["sites"] == [{"source": "wellfound", "total": 1, "counts": {"ready": 1}}]
    ready = next(column for column in board["columns"] if column["status"] == "ready")
    assert ready["total"] == 0


def test_no_wellfound_tab_when_it_is_off(tmp_path: Path) -> None:
    paths = Paths(tmp_path)
    paths.ensure()
    (tmp_path / "master.tex").write_text("resume", encoding="utf-8")
    profile = samples.profile(tmp_path / "master.tex")
    save(paths, replace(profile, settings=replace(profile.settings, wellfound=False)))
    with running(paths) as server:
        assert get(server, "/api/summary")[1]["sites"] == []


def test_new_jobs_counts_each_tab_since_your_last_visit(tmp_path: Path) -> None:
    paths = Paths(tmp_path)
    paths.ensure()
    later = NOW + timedelta(hours=1)
    with closing(connect(paths.database)) as db:
        jobs.add_many(db, [samples.job(external_id="1")], NOW)
        jobs.add_many(db, [samples.job(external_id="2"), samples.job(external_id="3")], later)
        jobs.set_status(db, 3, StatusChange(Status.CLOSED, later, "gone"))
        jobs.add_ready(db, [samples.job(Source.WELLFOUND, "9")], later, WELLFOUND_NOTE)
    since = (NOW + timedelta(minutes=30)).isoformat().replace("+", "%2B")
    with running(paths) as server:
        status, new = get(server, f"/api/new-jobs?jobs={since}&wellfound={since}")
        refused = get(server, "/api/new-jobs?jobs=yesterday")[0]
    assert (status, new) == (200, {"jobs": 1, "wellfound": 1})
    assert refused == 400


def test_the_workflow_counts_what_the_latest_run_changed(
    tmp_path: Path,
) -> None:
    paths = Paths(tmp_path)
    paths.ensure()
    with closing(connect(paths.database)) as db:
        seed_every_group(db, NOW)
        assert groups.changed_since(db, NOW + timedelta(minutes=10))[Group.APPLIED] == 1
        assert groups.changed_since(db, NOW + timedelta(hours=1))[Group.APPLIED] == 0
        assert groups.changed_since(db, NOW - timedelta(minutes=1))[Group.FOUND] == len(SEEDED)
    with running(paths) as server:
        assert get(server, "/api/workflow")[1]["lastRun"] is None
