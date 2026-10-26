import re
import sqlite3
from collections import Counter
from collections.abc import Sequence
from dataclasses import replace

from satyaapply.core.clock import utc_now
from satyaapply.core.errors import SatyaApplyError
from satyaapply.core.models import normalize
from satyaapply.core.paths import Paths
from satyaapply.core.profile import Profile, load, save
from satyaapply.store import records, rules
from satyaapply.store.answers import AnswerSource, SavedAnswer, all_answers, save_many
from satyaapply.store.records import JobRecord
from satyaapply.store.rules import NewRule, Rule, RuleKind, RuleState
from satyaapply.tracker.html import e, empty, joined, page, section
from satyaapply.tracker.responses import Response, back_to, bad_request, html, not_found
from satyaapply.tracker.routes import Form, Route, route

LEARNED = "/learned"
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
RULE_HINT = (
    "Plain words, like 'no staffing agencies' or 'Pune is fine, Mumbai is not'. It changes how "
    "jobs are scored. It can't add facts to your resume."
)
NOTE_HINT = "How should your resume be tailored next time? e.g. don't change my headline"
TOO_LONG = f"Write it in 1 to {RULE_LIMIT} characters."


def _clean(form: Form) -> str | None:
    text = " ".join(form.get("text", "").split())
    return text if 0 < len(text) <= RULE_LIMIT else None


def _add(db: sqlite3.Connection, kind: RuleKind, form: Form) -> bool:
    text = _clean(form)
    if text is not None:
        rules.add(db, NewRule(kind, text, RuleState.ACTIVE, utc_now()))
    return text is not None


def _add_rule(db: sqlite3.Connection, _paths: Paths, _match: re.Match[str], form: Form) -> Response:
    return back_to("/") if _add(db, RuleKind.RULE, form) else bad_request(TOO_LONG)


def _add_note(db: sqlite3.Connection, _paths: Paths, match: re.Match[str], form: Form) -> Response:
    job_id = int(match.group(1))
    if records.find(db, job_id) is None:
        return not_found()
    added = _add(db, RuleKind.TAILORING_NOTE, form)
    return back_to(f"/jobs/{job_id}") if added else bad_request(TOO_LONG)


def _editable(db: sqlite3.Connection, match: re.Match[str]) -> Rule | None:
    rule = rules.find(db, int(match.group(1)))
    return rule if rule and rule.kind is not RuleKind.SUGGESTION else None


def _edit_rule(db: sqlite3.Connection, _paths: Paths, match: re.Match[str], form: Form) -> Response:
    rule = _editable(db, match)
    text = _clean(form)
    if rule is None:
        return not_found()
    if text is None:
        return bad_request(TOO_LONG)
    rules.edit(db, rule.id, text)
    return back_to(LEARNED)


def _delete_rule(
    db: sqlite3.Connection, _paths: Paths, match: re.Match[str], _form: Form
) -> Response:
    rule = _editable(db, match)
    if rule is None:
        return not_found()
    rules.delete(db, rule.id)
    return back_to(LEARNED)


def _edit_answer(
    db: sqlite3.Connection, _paths: Paths, _match: re.Match[str], form: Form
) -> Response:
    question = form.get("question", "")
    answer = form.get("answer", "").strip()
    if question not in all_answers(db):
        return not_found()
    if not 0 < len(answer) <= ANSWER_LIMIT:
        return bad_request(f"Write the answer in 1 to {ANSWER_LIMIT} characters.")
    save_many(db, [SavedAnswer(question, answer, AnswerSource.USER)], utc_now())
    return back_to(LEARNED)


def _delete_answer(
    db: sqlite3.Connection, _paths: Paths, _match: re.Match[str], form: Form
) -> Response:
    rules.forget_answer(db, form.get("question", ""))
    return back_to(LEARNED)


def suggested_word(titles: Sequence[str], profile: Profile, taken: set[str]) -> str | None:
    counts = Counter(word for title in titles for word in dict.fromkeys(normalize(title).split()))
    phrases = (*profile.title_exclude, *profile.title_keywords)
    known = {word for phrase in phrases for word in normalize(phrase).split()}
    skip = known | taken | GENERIC_TITLE_WORDS
    fits = (w for w, n in counts.most_common() if n >= SUGGEST_AFTER and w not in skip)
    return next((word for word in fits if not word.isdigit()), None)


def _skip_word(rule: Rule) -> str:
    return rule.text.removeprefix(SKIP_TITLE)


def _pending(db: sqlite3.Connection) -> tuple[Rule, ...]:
    found = rules.of_kind(db, RuleKind.SUGGESTION)
    return tuple(rule for rule in found if rule.state is RuleState.SUGGESTED)


def refresh_suggestions(db: sqlite3.Connection, paths: Paths) -> None:
    titles = rules.feedback_titles(db, DISMISS, TOO_SENIOR)
    if len(titles) < SUGGEST_AFTER:
        return
    try:
        profile = load(paths)
    except SatyaApplyError:
        return
    taken = {_skip_word(rule) for rule in rules.of_kind(db, RuleKind.SUGGESTION)}
    word = suggested_word(titles, profile, taken)
    if word:
        suggestion = NewRule(RuleKind.SUGGESTION, SKIP_TITLE + word, RuleState.SUGGESTED, utc_now())
        rules.add(db, suggestion)


def _suggestion(db: sqlite3.Connection, match: re.Match[str]) -> Rule | None:
    rule = rules.find(db, int(match.group(1)))
    wanted = rule and rule.kind is RuleKind.SUGGESTION and rule.state is RuleState.SUGGESTED
    return rule if wanted else None


def _accept(db: sqlite3.Connection, paths: Paths, match: re.Match[str], _form: Form) -> Response:
    rule = _suggestion(db, match)
    if rule is None:
        return not_found()
    word = _skip_word(rule)
    try:
        profile = load(paths)
        if word not in profile.title_exclude:
            save(paths, replace(profile, title_exclude=(*profile.title_exclude, word)))
    except SatyaApplyError as error:
        return bad_request(e(error))
    rules.set_state(db, rule.id, RuleState.ACCEPTED)
    return back_to(LEARNED)


def _dismiss(db: sqlite3.Connection, _paths: Paths, match: re.Match[str], _form: Form) -> Response:
    rule = _suggestion(db, match)
    if rule is None:
        return not_found()
    rules.set_state(db, rule.id, RuleState.DISMISSED)
    return back_to(LEARNED)


def _button(action: str, label: str, extra: str = "", secondary: bool = True) -> str:
    style = ' class="secondary"' if secondary else ""
    return f'<form method="post" action="{action}">{extra}<button{style}>{label}</button></form>'


def _rule_row(rule: Rule) -> str:
    return (
        f'<li><form method="post" action="/rules/{rule.id}/edit" class="button-row">'
        f'<input type="text" name="text" value="{e(rule.text)}" maxlength="{RULE_LIMIT}" '
        'aria-label="Edit" required><button>Save</button></form>'
        f"{_button(f'/rules/{rule.id}/delete', 'Delete')}</li>"
    )


def _answer_row(answer: SavedAnswer) -> str:
    origin = "from you" if answer.source is AnswerSource.USER else "from the AI"
    hidden = f'<input type="hidden" name="question" value="{e(answer.question)}">'
    return (
        f'<li><p><strong>{e(answer.question)}</strong> <span class="muted">{origin}</span></p>'
        f'<form method="post" action="/answers/edit">{hidden}'
        f'<textarea name="answer" rows="2" maxlength="{ANSWER_LIMIT}" aria-label="Answer" '
        f"required>{e(answer.answer)}</textarea>"
        '<div class="button-row"><button>Save</button></div></form>'
        f"{_button('/answers/delete', 'Delete', hidden)}</li>"
    )


def _suggestion_text(rule: Rule) -> str:
    return f"Add '{_skip_word(rule)}' to skip titles?"


def _suggestion_row(rule: Rule) -> str:
    return (
        f"<li><p>{e(_suggestion_text(rule))}</p>"
        '<div class="button-row">'
        f"{_button(f'/suggestions/{rule.id}/accept', 'Accept', secondary=False)}"
        f"{_button(f'/suggestions/{rule.id}/dismiss', 'Dismiss')}</div></li>"
    )


def _listed(rows: Sequence[str], none: str) -> str:
    return f'<ul class="learned">{joined(rows)}</ul>' if rows else empty(none)


def _learned(db: sqlite3.Connection, paths: Paths, _match: re.Match[str], _form: Form) -> Response:
    refresh_suggestions(db, paths)
    own = [_rule_row(rule) for rule in rules.of_kind(db, RuleKind.RULE)]
    notes = [_rule_row(rule) for rule in rules.of_kind(db, RuleKind.TAILORING_NOTE)]
    answers = [_answer_row(answer) for answer in rules.saved_answers(db)]
    ideas = [_suggestion_row(rule) for rule in _pending(db)]
    body = joined(
        (
            "<h1>What it learned</h1>",
            section("Your rules", _listed(own, "No rules yet. Add one on the home page.")),
            section("Tailoring notes", _listed(notes, "No notes yet. Add one on a job's page.")),
            section("Saved answers", _listed(answers, "No saved answers yet.")),
            section("Suggestions", _listed(ideas, "Nothing to suggest right now.")),
        )
    )
    return html(page("What it learned", body, "/learned"))


GET: tuple[Route, ...] = (route(LEARNED, _learned),)
POST: tuple[Route, ...] = (
    route(r"/rules", _add_rule),
    route(r"/rules/(\d+)/edit", _edit_rule),
    route(r"/rules/(\d+)/delete", _delete_rule),
    route(r"/answers/edit", _edit_answer),
    route(r"/answers/delete", _delete_answer),
    route(r"/suggestions/(\d+)/accept", _accept),
    route(r"/suggestions/(\d+)/dismiss", _dismiss),
    route(r"/jobs/(\d+)/note", _add_note),
)


def home_panel(db: sqlite3.Connection, paths: Paths) -> str:
    refresh_suggestions(db, paths)
    pending = len(_pending(db))
    waiting = f" · {pending} suggestion{'' if pending == 1 else 's'} to review" if pending else ""
    body = (
        '<form method="post" action="/rules">'
        f'<textarea name="text" rows="2" maxlength="{RULE_LIMIT}" aria-label="Tell SatyaApply" '
        'required></textarea><div class="button-row"><button>Add rule</button></div></form>'
        f'<p class="muted">{e(RULE_HINT)}</p>'
        f'<p><a href="{LEARNED}">What it learned</a>{waiting}</p>'
    )
    return section("Tell SatyaApply", body)


def job_controls(_db: sqlite3.Connection, record: JobRecord) -> str:
    if record.job.id is None:
        return ""
    body = (
        f'<form method="post" action="/jobs/{record.job.id}/note">'
        f'<label for="tailoring-note">{e(NOTE_HINT)}</label>'
        f'<textarea id="tailoring-note" name="text" rows="2" maxlength="{RULE_LIMIT}" required>'
        '</textarea><div class="button-row"><button>Save note</button></div></form>'
    )
    return section("Tailoring note", body)
