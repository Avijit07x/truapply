import re
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field, replace
from pathlib import Path

from playwright.sync_api import Locator, Page

from satyaapply.ai.tasks import answer_fields
from satyaapply.apply.claims import made_up_numbers, problems, without
from satyaapply.apply.cover import write_cover_letter
from satyaapply.apply.detect import PageState, form_errors, is_confirmed
from satyaapply.apply.fields import form_scope, read_fields
from satyaapply.apply.fill import Files, fill_field
from satyaapply.apply.opener import open_form
from satyaapply.apply.options import best_option
from satyaapply.browser.page import find_button, visible_text, wait_until_quiet
from satyaapply.core.forms import (
    COVER_LETTER_FILE,
    Field,
    FieldKind,
    FormAnswers,
    FormContext,
    Sent,
)
from satyaapply.core.models import Status
from satyaapply.core.profile import UnknownQuestions
from satyaapply.store.answers import question_key

MAX_STEPS = 15
MAX_ERROR_ROUNDS = 2
MAX_FILL_ROUNDS = 3
SUBMIT = re.compile(
    r"^\s*(submit( your)?( application)?|send( my)? application|apply( now)?|finish"
    r"|complete( my)? application)\s*$",
    re.IGNORECASE,
)
NEXT = re.compile(
    r"^\s*(next( step)?|continue|review( your application)?|save (and|&) continue|proceed)\s*$",
    re.IGNORECASE,
)
CHOICE_KINDS = frozenset({FieldKind.SELECT, FieldKind.RADIO, FieldKind.COMBOBOX})
REFILLABLE = frozenset(FieldKind) - {FieldKind.FILE, FieldKind.CHECKBOX}
NO_REPLY = FormAnswers((), (), None, None, None)
STATE_OUTCOMES = {
    PageState.CLOSED: (Status.CLOSED, "the job is closed"),
    PageState.ALREADY_APPLIED: (Status.APPLIED, "already applied before"),
    PageState.HUMAN_CHECK: (Status.NEEDS_INPUT, "the site asks to prove you're human"),
    PageState.NO_FORM: (Status.EXTERNAL, "no application form found; apply yourself"),
}

Answerer = Callable[[FormContext, Sequence[Field]], FormAnswers]
Errors = tuple[str, ...]


def _nothing() -> None:
    return None


@dataclass(frozen=True)
class ApplyRequest:
    context: FormContext
    files: Files
    known: Mapping[str, str]
    dry_run: bool
    cover_letter_target: Path
    before_submit: Callable[[], None] = _nothing


@dataclass(frozen=True)
class Attempt:
    status: Status
    note: str
    sent: tuple[Sent, ...] = ()
    learned: tuple[Sent, ...] = ()
    questions: tuple[str, ...] = ()


@dataclass
class FormSession:
    page: Page
    request: ApplyRequest
    answer: Answerer
    sent: dict[str, Sent] = field(default_factory=dict)
    learned: list[Sent] = field(default_factory=list)
    questions: list[str] = field(default_factory=list)
    handled: set[str] = field(default_factory=set)

    def attempt(self, status: Status, note: str) -> Attempt:
        return Attempt(
            status,
            note,
            tuple(self.sent.values()),
            tuple(self.learned),
            tuple(dict.fromkeys(self.questions)),
        )


def known_values(fields: Sequence[Field], known: Mapping[str, str]) -> dict[str, str]:
    values = {}
    for item in fields:
        saved = known.get(question_key(item.label))
        if not saved or item.kind is FieldKind.FILE:
            continue
        if item.kind in CHOICE_KINDS and item.options and best_option(item.options, saved) is None:
            continue
        values[item.id] = saved
    return values


def _stop(session: FormSession, reply: FormAnswers) -> Attempt | None:
    if reply.blocker:
        return session.attempt(Status.NEEDS_INPUT, f"needs you: {reply.blocker}")
    if reply.skip_reason:
        return session.attempt(Status.SKIPPED, reply.skip_reason)
    legal = [item.question for item in reply.unknown if item.legal]
    others = [item.question for item in reply.unknown if not item.legal]
    session.questions.extend(legal + others)
    if legal:
        return session.attempt(Status.NEEDS_INPUT, "a legal question your profile doesn't answer")
    skipping = session.request.context.profile.unknown_questions is UnknownQuestions.SKIP
    if others and skipping:
        return session.attempt(Status.NEEDS_INPUT, "questions your profile doesn't answer yet")
    return None


def _files(session: FormSession, reply: FormAnswers) -> Files:
    request = session.request
    wants_letter = any(answer.value == COVER_LETTER_FILE for answer in reply.answers)
    if request.dry_run or not wants_letter or not reply.cover_letter:
        return request.files
    letter = write_cover_letter(
        session.page.context, reply.cover_letter, request.cover_letter_target
    )
    return replace(request.files, cover_letter=letter)


def _remember(session: FormSession, fields: Sequence[Field], reply: FormAnswers) -> None:
    by_id = {item.id: item for item in fields}
    session.learned.extend(
        Sent(by_id[answer.id].label, answer.value)
        for answer in reply.answers
        if answer.reusable
        and not answer.guessed
        and answer.id in by_id
        and by_id[answer.id].kind is not FieldKind.FILE
    )


def _truthful(session: FormSession, context: FormContext, fields: Sequence[Field]) -> FormAnswers:
    if not fields:
        return NO_REPLY
    reply = session.answer(context, fields)
    found = made_up_numbers(context, fields, reply)
    if not found:
        return reply
    retry = session.answer(replace(context, errors=context.errors + problems(found)), fields)
    return without(retry, made_up_numbers(context, fields, retry))


def _lost(session: FormSession, item: Field) -> bool:
    return item.kind in REFILLABLE and not item.value and item.id in session.sent


def _refills(session: FormSession, fields: Sequence[Field]) -> dict[str, str]:
    return {item.id: session.sent[item.id].answer for item in fields if _lost(session, item)}


def _fill_round(session: FormSession, fields: Sequence[Field], errors: Errors) -> Attempt | None:
    values = known_values(fields, session.request.known)
    if not errors:
        values.update(_refills(session, fields))
    unanswered = [item for item in fields if item.id not in values]
    reply = _truthful(session, replace(session.request.context, errors=errors), unanswered)
    stop = _stop(session, reply)
    if stop:
        return stop
    values.update({answer.id: answer.value for answer in reply.answers})
    files = _files(session, reply)
    for item in fields:
        session.handled.add(item.id)
        value = values.get(item.id, "")
        entered = fill_field(session.page, item, value, files) if value else None
        if entered is not None:
            session.sent[item.id] = Sent(item.label, entered)
    _remember(session, fields, reply)
    return None


def _fill_step(session: FormSession, errors: Errors) -> Attempt | None:
    for _ in range(MAX_FILL_ROUNDS):
        fields = [
            item
            for item in read_fields(session.page)
            if errors or item.id not in session.handled or _lost(session, item)
        ]
        if not fields:
            return None
        stop = _fill_round(session, fields, errors)
        if stop:
            return stop
        errors = ()
    return None


def _missing_required(session: FormSession) -> list[str]:
    dry_run = session.request.dry_run
    return [
        item.label
        for item in read_fields(session.page)
        if item.required and not item.value and not (dry_run and item.kind is FieldKind.FILE)
    ]


def _finish(session: FormSession, submit: Locator) -> Attempt | None:
    missing = _missing_required(session)
    if missing:
        session.questions.extend(missing)
        return session.attempt(Status.NEEDS_INPUT, "required fields still empty")
    if session.request.dry_run:
        return session.attempt(Status.READY, "filled and stopped before Submit")
    session.request.before_submit()
    submit.click()
    wait_until_quiet(session.page)
    if is_confirmed(visible_text(session.page)):
        return session.attempt(Status.APPLIED, "submitted and confirmed")
    if form_errors(session.page):
        return None
    return session.attempt(Status.UNCONFIRMED, "submitted, but no confirmation was shown")


def _advance(session: FormSession) -> tuple[Attempt | None, Errors]:
    proceed = find_button(form_scope(session.page), NEXT)
    if proceed is None:
        return session.attempt(Status.FAILED, "no Next or Submit button found"), ()
    proceed.click()
    wait_until_quiet(session.page)
    return None, tuple(form_errors(session.page))


def _step(session: FormSession, errors: Errors) -> tuple[Attempt | None, Errors]:
    stop = _fill_step(session, errors)
    if stop:
        return stop, ()
    submit = find_button(form_scope(session.page), SUBMIT)
    if submit is None:
        return _advance(session)
    return _finish(session, submit), tuple(form_errors(session.page))


def apply(page: Page, request: ApplyRequest, answer: Answerer = answer_fields) -> Attempt:
    state = open_form(page, request.context.job)
    if state is not PageState.FORM:
        status, note = STATE_OUTCOMES[state]
        return Attempt(status, note)
    session = FormSession(page, request, answer)
    errors: Errors = ()
    error_rounds = 0
    for _ in range(MAX_STEPS):
        result, errors = _step(session, errors)
        if result:
            return result
        error_rounds = error_rounds + 1 if errors else 0
        if error_rounds > MAX_ERROR_ROUNDS:
            return session.attempt(
                Status.FAILED, "the form kept showing errors: " + "; ".join(errors)
            )
    return session.attempt(Status.FAILED, f"gave up after {MAX_STEPS} steps")
