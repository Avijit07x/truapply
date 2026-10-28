import sqlite3
from collections.abc import Iterator
from contextlib import closing
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

import pytest

from tests.unit import samples
from tests.unit.tracker_api import get, post, running
from truapply.core.paths import Paths
from truapply.core.profile import load, save
from truapply.store import jobs, rules
from truapply.store.answers import AnswerSource, SavedAnswer, save_many
from truapply.store.db import connect
from truapply.store.rules import NewRule, RuleKind, RuleState
from truapply.tracker.learning import refresh_suggestions, suggested_word
from truapply.tracker.server import TrackerServer

NOW = datetime(2026, 10, 26, 9, 0, tzinfo=UTC)


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
    with running(paths) as server:
        yield server


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
    assert get(tracker, "/api/summary")[1]["suggestions"] == 1
    suggestions = get(tracker, "/api/learned")[1]["suggestions"]
    assert [item["word"] for item in suggestions] == ["staff"]
    assert "staff" not in load(paths).title_exclude
    accept = f"/api/suggestions/{suggestions[0]['id']}/accept"
    code, learned = post(tracker, accept)
    assert (code, learned["suggestions"]) == (200, [])
    assert load(paths).title_exclude[-1] == "staff"
    assert post(tracker, accept)[0] == 404
    assert get(tracker, "/api/summary")[1]["suggestions"] == 0


def test_dismissing_a_suggestion_leaves_the_profile_alone(
    tracker: TrackerServer, db: sqlite3.Connection, paths: Paths
) -> None:
    dismiss_too_senior(db, ["Staff Frontend Engineer"] * 3)
    suggestion = get(tracker, "/api/learned")[1]["suggestions"][0]
    code, learned = post(tracker, f"/api/suggestions/{suggestion['id']}/dismiss")
    assert (code, learned["suggestions"]) == (200, [])
    assert "staff" not in load(paths).title_exclude
    assert get(tracker, "/api/learned")[1]["suggestions"] == []


def test_a_rule_in_plain_words_is_saved_and_shown(
    tracker: TrackerServer, db: sqlite3.Connection
) -> None:
    code, learned = post(
        tracker, "/api/rules", {"kind": "rule", "text": "  no staffing\n agencies "}
    )
    assert code == 200
    assert [rule["text"] for rule in learned["rules"]] == ["no staffing agencies"]
    assert rules.active_texts(db, RuleKind.RULE) == ("no staffing agencies",)
    assert post(tracker, "/api/rules", {"kind": "rule", "text": "   "})[0] == 400
    assert post(tracker, "/api/rules", {"kind": "rule", "text": "x" * 301})[0] == 400
    assert post(tracker, "/api/rules", {"kind": "suggestion", "text": "x"})[0] == 400
    assert post(tracker, "/api/rules", {"text": "no kind"})[0] == 400


def test_rules_and_notes_can_be_edited_and_deleted(
    tracker: TrackerServer, db: sqlite3.Connection
) -> None:
    rule = rules.add(db, NewRule(RuleKind.RULE, "<b>no Mumbai</b>", RuleState.ACTIVE, NOW))
    assert get(tracker, "/api/learned")[1]["rules"] == [{"id": rule, "text": "<b>no Mumbai</b>"}]
    code, learned = post(tracker, f"/api/rules/{rule}/edit", {"text": "Pune is fine"})
    assert (code, learned["rules"]) == (200, [{"id": rule, "text": "Pune is fine"}])
    assert post(tracker, f"/api/rules/{rule}/edit", {"text": ""})[0] == 400
    assert post(tracker, f"/api/rules/{rule}/delete")[1]["rules"] == []
    assert rules.active_texts(db, RuleKind.RULE) == ()
    assert post(tracker, "/api/rules/999/delete")[0] == 404


def test_a_suggestion_cannot_be_edited_like_a_rule(
    tracker: TrackerServer, db: sqlite3.Connection
) -> None:
    idea = rules.add(db, NewRule(RuleKind.SUGGESTION, "skip_title:staff", RuleState.SUGGESTED, NOW))
    assert post(tracker, f"/api/rules/{idea}/edit", {"text": "skip_title:x"})[0] == 404
    assert post(tracker, f"/api/rules/{idea}/delete")[0] == 404


def test_a_tailoring_note_is_kept_apart_from_rules(
    tracker: TrackerServer, db: sqlite3.Connection
) -> None:
    note = {"kind": "tailoring_note", "text": "don't change my headline"}
    code, learned = post(tracker, "/api/rules", note)
    assert code == 200
    assert [item["text"] for item in learned["notes"]] == ["don't change my headline"]
    assert learned["rules"] == []
    assert rules.active_texts(db, RuleKind.TAILORING_NOTE) == ("don't change my headline",)


def test_an_edited_answer_becomes_the_users_own(
    tracker: TrackerServer, db: sqlite3.Connection
) -> None:
    saved = get(tracker, "/api/learned")[1]["answers"]
    assert saved == [{"question": "notice period", "answer": "30 days", "source": "ai"}]
    edited = {"question": "notice period", "answer": "15 days"}
    code, learned = post(tracker, "/api/answers/edit", edited)
    assert (code, learned["answers"][0]["source"]) == (200, "user")
    assert rules.saved_answers(db) == (SavedAnswer("notice period", "15 days", AnswerSource.USER),)
    assert post(tracker, "/api/answers/edit", {"question": "made up", "answer": "x"})[0] == 404
    assert post(tracker, "/api/answers/edit", edited | {"answer": ""})[0] == 400
    code, learned = post(tracker, "/api/answers/delete", {"question": "notice period"})
    assert (code, learned["answers"]) == (200, [])
    assert rules.saved_answers(db) == ()
