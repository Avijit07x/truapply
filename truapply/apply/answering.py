import re
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, replace

from truapply.apply.claims import made_up_numbers, problems, without
from truapply.apply.options import as_number, best_option, is_truthy
from truapply.apply.profile_facts import profile_fact
from truapply.core.forms import (
    MULTI_VALUE_SEPARATOR,
    RESUME_FILE,
    Field,
    FieldKind,
    FormAnswers,
    FormContext,
    Sent,
)
from truapply.core.profile import Profile
from truapply.store.answers import question_key

CONSENT = re.compile(
    r"\b(i agree|agree to|consent|privacy|terms (of|and)|acknowledge|i confirm|i certify"
    r"|i declare|i attest|i hereby)",
    re.IGNORECASE,
)
RESUME_FIELD = re.compile(r"resume|\bcv\b|curriculum", re.IGNORECASE)
CHOICE_KINDS = frozenset({FieldKind.SELECT, FieldKind.RADIO, FieldKind.COMBOBOX})
CONSENT_WHY = "only you can agree to or confirm this"
LEGAL_WHY = "a legal question your profile doesn't answer"
UNKNOWN_WHY = "your profile doesn't answer this yet"
NO_MATCH_WHY = "none of the choices fits your profile"
FILE_WHY = "attach this file yourself"
NO_REPLY = FormAnswers((), (), None, None, None)

Answerer = Callable[[FormContext, Sequence[Field]], FormAnswers]


@dataclass(frozen=True)
class ForYou:
    id: str
    label: str
    why: str


@dataclass(frozen=True)
class FormReply:
    answers: dict[str, str]
    for_you: tuple[ForYou, ...]
    learned: tuple[Sent, ...]
    note: str | None
    waiting: tuple[str, ...] = ()
    from_ai: tuple[Sent, ...] = ()


def is_consent(item: Field) -> bool:
    return bool(CONSENT.search(" ".join((item.label, *item.options))))


def _choice(item: Field, value: str) -> str | None:
    if not item.options:
        return value
    index = best_option(item.options, value)
    return None if index is None else item.options[index]


def _picks(item: Field, value: str) -> str | None:
    found = [best_option(item.options, part) for part in value.split(MULTI_VALUE_SEPARATOR)]
    chosen = sorted({index for index in found if index is not None})
    return MULTI_VALUE_SEPARATOR.join(item.options[index] for index in chosen) or None


def entry(item: Field, value: str) -> str | None:
    if item.kind in CHOICE_KINDS:
        return _choice(item, value)
    if item.kind is FieldKind.CHECKBOXES:
        return _picks(item, value)
    if item.kind is FieldKind.CHECKBOX:
        return "yes" if is_truthy(value) else None
    if item.kind is FieldKind.NUMBER:
        return as_number(value)
    return value[: item.max_length] if item.max_length else value


def _known(fields: Sequence[Field], known: Mapping[str, str], profile: Profile) -> dict[str, str]:
    values = {}
    for item in fields:
        saved = known.get(question_key(item.label)) or profile_fact(profile, item.label)
        value = entry(item, saved) if saved else None
        if value:
            values[item.id] = value
    return values


def _files(fields: Sequence[Field]) -> tuple[dict[str, str], list[ForYou]]:
    resumes = {item.id: RESUME_FILE for item in fields if RESUME_FIELD.search(item.label)}
    others = [ForYou(item.id, item.label, FILE_WHY) for item in fields if item.id not in resumes]
    return resumes, others


def _truthful(answer: Answerer, context: FormContext, fields: Sequence[Field]) -> FormAnswers:
    if not fields:
        return NO_REPLY
    reply = answer(context, fields)
    found = made_up_numbers(context, fields, reply)
    if not found:
        return reply
    retry = answer(replace(context, errors=problems(found)), fields)
    return without(retry, made_up_numbers(context, fields, retry))


def _learned(fields: Sequence[Field], reply: FormAnswers) -> tuple[Sent, ...]:
    by_id = {item.id: item for item in fields}
    return tuple(
        Sent(by_id[found.id].label, found.value)
        for found in reply.answers
        if found.reusable and not found.guessed and found.id in by_id
    )


def answer_form(
    context: FormContext,
    fields: Sequence[Field],
    known: Mapping[str, str],
    answer: Answerer | None,
) -> FormReply:
    empty = [item for item in fields if not item.value]
    yours = [ForYou(item.id, item.label, CONSENT_WHY) for item in empty if is_consent(item)]
    files = [item for item in empty if item.kind is FieldKind.FILE]
    values, others = _files(files)
    yours += others
    open_ = [item for item in empty if not is_consent(item) and item.kind is not FieldKind.FILE]
    values |= _known(open_, known, context.profile)
    asked = [item for item in open_ if item.id not in values]
    if answer is None:
        ordered = {item.id: values[item.id] for item in fields if item.id in values}
        return FormReply(ordered, tuple(yours), (), None, tuple(item.id for item in asked))
    reply = _truthful(answer, context, asked)
    by_id = {item.id: item for item in asked}
    unknown = {item.id: LEGAL_WHY if item.legal else UNKNOWN_WHY for item in reply.unknown}
    for found in reply.answers:
        item = by_id.get(found.id)
        value = entry(item, found.value) if item and found.id not in unknown else None
        if value:
            values[found.id] = value
        elif item and found.id not in unknown:
            unknown[found.id] = NO_MATCH_WHY
    yours += [ForYou(item.id, item.label, unknown[item.id]) for item in asked if item.id in unknown]
    ordered = {item.id: values[item.id] for item in fields if item.id in values}
    from_ai = tuple(Sent(item.label, values[item.id]) for item in asked if item.id in values)
    return FormReply(ordered, tuple(yours), _learned(asked, reply), reply.blocker, (), from_ai)
