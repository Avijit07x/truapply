import sqlite3
import threading
import urllib.request
from collections.abc import Iterator
from contextlib import closing
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlencode

import pytest

from satyaapply.core.paths import Paths
from satyaapply.core.profile import load, save
from satyaapply.store import jobs, rules
from satyaapply.store.answers import AnswerSource, SavedAnswer, save_many
from satyaapply.store.db import connect
from satyaapply.store.rules import NewRule, RuleKind, RuleState
from satyaapply.tracker.learning import refresh_suggestions, suggested_word
from satyaapply.tracker.server import TrackerServer
from tests.unit import samples

NOW = datetime(2026, 10, 26, 9, 0, tzinfo=UTC)
FORM = "application/x-www-form-urlencoded"


class KeepRedirects(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *_args: object, **_kwargs: object) -> None:
        return None


@pytest.fixture
def paths(tmp_path: Path) -> Paths:
    paths = Paths(tmp_path / "home")
    paths.ensure()
    resume = tmp_path / "master.tex"
    resume.write_text("resume", encoding="utf-8")
    save(paths, samples.profile(resume))
    with closing(connect(paths.database)) as db:
        jobs.add_many(db, [samples.job()], NOW)
        save_many(db, [SavedAnswer("Notice period?", "30 days", AnswerSource.AI)], NOW)
    return paths


@pytest.fixture
def db(paths: Paths) -> Iterator[sqlite3.Connection]:
    with closing(connect(paths.database)) as connection:
        yield connection


@pytest.fixture
def tracker(paths: Paths) -> Iterator[TrackerServer]:
    server = TrackerServer(paths, 0)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield server
    server.shutdown()
    server.server_close()


def dismiss_too_senior(db: sqlite3.Connection, titles: list[str]) -> None:
    found = [
        replace(samples.job(external_id=f"s{n}", company=f"Co {n}"), title=title)
        for n, title in enumerate(titles)
    ]
    jobs.add_many(db, found, NOW)
    with db:
        db.execute(
            "insert into feedback (job_id, kind, value, at) "
            "select id, 'dismiss', 'too senior', ? from jobs where key glob '*:s[0-9]*'",
            (NOW.isoformat(),),
        )


def get(server: TrackerServer, path: str) -> str:
    with urllib.request.urlopen(server.url + path, timeout=5) as response:  # noqa: S310
        return str(response.read().decode("utf-8"))


def post(server: TrackerServer, path: str, fields: dict[str, str]) -> tuple[int, str]:
    headers = {"Origin": server.url, "Content-Type": FORM}
    data = urlencode(fields).encode()
    request = urllib.request.Request(server.url + path, data, headers, method="POST")  # noqa: S310
    try:
        with urllib.request.build_opener(KeepRedirects).open(request, timeout=5) as response:
            return int(response.status), ""
    except HTTPError as error:
        return error.code, error.headers.get("Location", "")


def test_rules_can_be_added_edited_and_removed(db: sqlite3.Connection) -> None:
    kept = rules.add(db, NewRule(RuleKind.RULE, "no staffing agencies", RuleState.ACTIVE, NOW))
    gone = rules.add(db, NewRule(RuleKind.RULE, "no Mumbai", RuleState.ACTIVE, NOW))
    rules.add(db, NewRule(RuleKind.SUGGESTION, "skip_title:staff", RuleState.SUGGESTED, NOW))
    rules.edit(db, kept, "no staffing or recruitment agencies")
    rules.delete(db, gone)
    assert rules.active_texts(db, RuleKind.RULE) == ("no staffing or recruitment agencies",)
    rules.set_state(db, kept, RuleState.DISMISSED)
    assert rules.active_texts(db, RuleKind.RULE) == ()
    assert [rule.state for rule in rules.of_kind(db, RuleKind.SUGGESTION)] == [RuleState.SUGGESTED]


def test_a_title_word_is_suggested_only_when_it_is_new_and_specific(tmp_path: Path) -> None:
    profile = samples.profile(tmp_path / "master.tex")
    titles = ["Staff Frontend Engineer", "Staff React Engineer", "Staff Engineer, Web"]
    assert suggested_word(titles, profile, set()) == "staff"
    assert suggested_word(titles, profile, {"staff"}) is None
    assert suggested_word(titles[:2], profile, set()) is None
    excluded = replace(profile, title_exclude=("staff",))
    assert suggested_word(titles, excluded, set()) is None


def test_three_too_senior_dismissals_suggest_one_skip_word(
    db: sqlite3.Connection, paths: Paths
) -> None:
    dismiss_too_senior(db, ["Staff Frontend Engineer"] * 3)
    refresh_suggestions(db, paths)
    refresh_suggestions(db, paths)
    found = rules.of_kind(db, RuleKind.SUGGESTION)
    assert [(rule.text, rule.state) for rule in found] == [
        ("skip_title:staff", RuleState.SUGGESTED)
    ]
    assert "staff" not in load(paths).title_exclude


def test_accepting_a_suggestion_is_the_only_thing_that_changes_the_profile(
    tracker: TrackerServer, db: sqlite3.Connection, paths: Paths
) -> None:
    dismiss_too_senior(db, ["Staff Frontend Engineer"] * 3)
    home = get(tracker, "/")
    assert "1 suggestion to review" in home
    assert "Add &#x27;staff&#x27; to skip titles?" in get(tracker, "/learned")
    assert "staff" not in load(paths).title_exclude
    suggestion = rules.of_kind(db, RuleKind.SUGGESTION)[0]
    assert post(tracker, f"/suggestions/{suggestion.id}/accept", {}) == (303, "/learned")
    assert load(paths).title_exclude[-1] == "staff"
    assert post(tracker, f"/suggestions/{suggestion.id}/accept", {})[0] == 404
    assert "skip titles" not in get(tracker, "/learned")


def test_dismissing_a_suggestion_leaves_the_profile_alone(
    tracker: TrackerServer, db: sqlite3.Connection, paths: Paths
) -> None:
    dismiss_too_senior(db, ["Staff Frontend Engineer"] * 3)
    get(tracker, "/learned")
    suggestion = rules.of_kind(db, RuleKind.SUGGESTION)[0]
    assert post(tracker, f"/suggestions/{suggestion.id}/dismiss", {}) == (303, "/learned")
    assert "staff" not in load(paths).title_exclude
    assert "skip titles" not in get(tracker, "/learned")


def test_a_rule_typed_on_the_home_page_is_saved_and_shown(
    tracker: TrackerServer, db: sqlite3.Connection
) -> None:
    assert "Tell SatyaApply" in get(tracker, "/")
    assert post(tracker, "/rules", {"text": "  no staffing\n agencies "}) == (303, "/")
    assert rules.active_texts(db, RuleKind.RULE) == ("no staffing agencies",)
    assert post(tracker, "/rules", {"text": "   "})[0] == 400
    assert post(tracker, "/rules", {"text": "x" * 301})[0] == 400
    assert "no staffing agencies" in get(tracker, "/learned")


def test_rules_and_notes_can_be_edited_and_deleted_from_the_learned_page(
    tracker: TrackerServer, db: sqlite3.Connection
) -> None:
    rule = rules.add(db, NewRule(RuleKind.RULE, "<b>no Mumbai</b>", RuleState.ACTIVE, NOW))
    page = get(tracker, "/learned")
    assert "<b>no Mumbai</b>" not in page
    assert "&lt;b&gt;no Mumbai&lt;/b&gt;" in page
    assert post(tracker, f"/rules/{rule}/edit", {"text": "Pune is fine"}) == (303, "/learned")
    assert rules.active_texts(db, RuleKind.RULE) == ("Pune is fine",)
    assert post(tracker, f"/rules/{rule}/delete", {}) == (303, "/learned")
    assert rules.active_texts(db, RuleKind.RULE) == ()
    assert post(tracker, "/rules/999/delete", {})[0] == 404


def test_a_tailoring_note_is_added_from_a_job_page(
    tracker: TrackerServer, db: sqlite3.Connection
) -> None:
    assert "How should your resume be tailored next time?" in get(tracker, "/jobs/1")
    note = {"text": "don't change my headline"}
    assert post(tracker, "/jobs/1/note", note) == (303, "/jobs/1")
    assert rules.active_texts(db, RuleKind.TAILORING_NOTE) == ("don't change my headline",)
    assert post(tracker, "/jobs/99/note", note)[0] == 404
    assert "don&#x27;t change my headline" in get(tracker, "/learned")


def test_an_edited_answer_becomes_the_users_own(
    tracker: TrackerServer, db: sqlite3.Connection
) -> None:
    assert "from the AI" in get(tracker, "/learned")
    edited = {"question": "notice period", "answer": "15 days"}
    assert post(tracker, "/answers/edit", edited) == (303, "/learned")
    assert rules.saved_answers(db) == (SavedAnswer("notice period", "15 days", AnswerSource.USER),)
    assert "from you" in get(tracker, "/learned")
    assert post(tracker, "/answers/edit", {"question": "made up", "answer": "x"})[0] == 404
    assert post(tracker, "/answers/delete", {"question": "notice period"}) == (303, "/learned")
    assert rules.saved_answers(db) == ()
