import re
import sqlite3
from collections import Counter
from collections.abc import Sequence
from dataclasses import replace

from truapply.core.clock import utc_now
from truapply.core.errors import TruApplyError
from truapply.core.models import normalize
from truapply.core.paths import Paths
from truapply.core.profile import Profile, load, save
from truapply.store import rules
from truapply.store.answers import AnswerSource, SavedAnswer, all_answers, save_many
from truapply.store.rules import NewRule, Rule, RuleKind, RuleState
from truapply.tracker.body import Body, text
from truapply.tracker.responses import Response, bad_request, not_found, ok
from truapply.tracker.routes import Route, route

RULE_LIMIT = 300
ANSWER_LIMIT = 2000
SKIP_TITLE = "skip_title:"
DISMISS = "dismiss"
TOO_SENIOR = "too senior"
SUGGEST_AFTER = 3
GENERIC_TITLE_WORDS = frozenset(
    {
        "engineer",
        "engineering",
        "software",
        "developer",
        "development",
        "web",
        "full",
        "stack",
        "and",
        "of",
        "the",
        "for",
        "in",
        "at",
        "with",
        "remote",
        "hybrid",
    }
)
TOO_LONG = f"Write it in 1 to {RULE_LIMIT} characters."


KINDS = {"rule": RuleKind.RULE, "tailoring_note": RuleKind.TAILORING_NOTE}


def clean_rule(body: Body) -> str | None:
    words = " ".join(text(body, "text", RULE_LIMIT + 1).split())
    return words if 0 < len(words) <= RULE_LIMIT else None


def suggested_word(titles: Sequence[str], profile: Profile, taken: set[str]) -> str | None:
    counts = Counter(word for title in titles for word in dict.fromkeys(normalize(title).split()))
    phrases = (*profile.title_exclude, *profile.title_keywords)
    known = {word for phrase in phrases for word in normalize(phrase).split()}
    skip = known | taken | GENERIC_TITLE_WORDS
    fits = (w for w, n in counts.most_common() if n >= SUGGEST_AFTER and w not in skip)
    return next((word for word in fits if not word.isdigit()), None)


def _skip_word(rule: Rule) -> str:
    return rule.text.removeprefix(SKIP_TITLE)


def pending(db: sqlite3.Connection) -> tuple[Rule, ...]:
    found = rules.of_kind(db, RuleKind.SUGGESTION)
    return tuple(rule for rule in found if rule.state is RuleState.SUGGESTED)


def refresh_suggestions(db: sqlite3.Connection, paths: Paths) -> None:
    titles = rules.feedback_titles(db, DISMISS, TOO_SENIOR)
    if len(titles) < SUGGEST_AFTER:
        return
    try:
        profile = load(paths)
    except TruApplyError:
        return
    taken = {_skip_word(rule) for rule in rules.of_kind(db, RuleKind.SUGGESTION)}
    word = suggested_word(titles, profile, taken)
    if word:
        suggestion = NewRule(RuleKind.SUGGESTION, SKIP_TITLE + word, RuleState.SUGGESTED, utc_now())
        rules.add(db, suggestion)


def _rule(rule: Rule) -> dict[str, object]:
    return {"id": rule.id, "text": rule.text}


def _learned(db: sqlite3.Connection) -> Response:
    answers = [
        {"question": item.question, "answer": item.answer, "source": item.source.value}
        for item in rules.saved_answers(db)
    ]
    return ok(
        {
            "rules": [_rule(rule) for rule in rules.of_kind(db, RuleKind.RULE)],
            "notes": [_rule(rule) for rule in rules.of_kind(db, RuleKind.TAILORING_NOTE)],
            "answers": answers,
            "suggestions": [{"id": rule.id, "word": _skip_word(rule)} for rule in pending(db)],
        }
    )


def _show(db: sqlite3.Connection, paths: Paths, _match: re.Match[str], _body: Body) -> Response:
    refresh_suggestions(db, paths)
    return _learned(db)


def _add_rule(db: sqlite3.Connection, _paths: Paths, _match: re.Match[str], body: Body) -> Response:
    kind = KINDS.get(text(body, "kind", RULE_LIMIT))
    words = clean_rule(body)
    if kind is None:
        return bad_request("Choose a rule or a tailoring note.")
    if words is None:
        return bad_request(TOO_LONG)
    rules.add(db, NewRule(kind, words, RuleState.ACTIVE, utc_now()))
    return _learned(db)


def _editable(db: sqlite3.Connection, match: re.Match[str]) -> Rule | None:
    rule = rules.find(db, int(match.group(1)))
    return rule if rule and rule.kind is not RuleKind.SUGGESTION else None


def _edit_rule(db: sqlite3.Connection, _paths: Paths, match: re.Match[str], body: Body) -> Response:
    rule = _editable(db, match)
    words = clean_rule(body)
    if rule is None:
        return not_found("No such rule.")
    if words is None:
        return bad_request(TOO_LONG)
    rules.edit(db, rule.id, words)
    return _learned(db)


def _delete_rule(
    db: sqlite3.Connection, _paths: Paths, match: re.Match[str], _body: Body
) -> Response:
    rule = _editable(db, match)
    if rule is None:
        return not_found("No such rule.")
    rules.delete(db, rule.id)
    return _learned(db)


def _edit_answer(
    db: sqlite3.Connection, _paths: Paths, _match: re.Match[str], body: Body
) -> Response:
    question = text(body, "question", ANSWER_LIMIT)
    answer = text(body, "answer", ANSWER_LIMIT + 1)
    if question not in all_answers(db):
        return not_found("No such saved answer.")
    if not 0 < len(answer) <= ANSWER_LIMIT:
        return bad_request(f"Write the answer in 1 to {ANSWER_LIMIT} characters.")
    save_many(db, [SavedAnswer(question, answer, AnswerSource.USER)], utc_now())
    return _learned(db)


def _delete_answer(
    db: sqlite3.Connection, _paths: Paths, _match: re.Match[str], body: Body
) -> Response:
    rules.forget_answer(db, text(body, "question", ANSWER_LIMIT))
    return _learned(db)


def _suggestion(db: sqlite3.Connection, match: re.Match[str]) -> Rule | None:
    rule = rules.find(db, int(match.group(1)))
    wanted = rule and rule.kind is RuleKind.SUGGESTION and rule.state is RuleState.SUGGESTED
    return rule if wanted else None


def _accept(db: sqlite3.Connection, paths: Paths, match: re.Match[str], _body: Body) -> Response:
    rule = _suggestion(db, match)
    if rule is None:
        return not_found("No such suggestion.")
    word = _skip_word(rule)
    try:
        profile = load(paths)
        if word not in profile.title_exclude:
            save(paths, replace(profile, title_exclude=(*profile.title_exclude, word)))
    except TruApplyError as error:
        return bad_request(str(error))
    rules.set_state(db, rule.id, RuleState.ACCEPTED)
    return _learned(db)


def _dismiss(db: sqlite3.Connection, _paths: Paths, match: re.Match[str], _body: Body) -> Response:
    rule = _suggestion(db, match)
    if rule is None:
        return not_found("No such suggestion.")
    rules.set_state(db, rule.id, RuleState.DISMISSED)
    return _learned(db)


GET: tuple[Route, ...] = (route("/learned", _show),)
POST: tuple[Route, ...] = (
    route("/rules", _add_rule),
    route(r"/rules/(\d+)/edit", _edit_rule),
    route(r"/rules/(\d+)/delete", _delete_rule),
    route("/answers/edit", _edit_answer),
    route("/answers/delete", _delete_answer),
    route(r"/suggestions/(\d+)/accept", _accept),
    route(r"/suggestions/(\d+)/dismiss", _dismiss),
)
