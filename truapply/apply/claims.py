from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace

from truapply.ai.context import candidate_facts
from truapply.core.forms import Field, FieldKind, FormAnswers, FormContext
from truapply.core.numbers import numbers

FREE_TEXT = frozenset({FieldKind.TEXT, FieldKind.TEXTAREA})
COVER_LETTER_KEY = "cover_letter"


@dataclass(frozen=True)
class Claim:
    key: str
    label: str
    text: str


Unsupported = Mapping[Claim, Sequence[str]]


def _claims(fields: Sequence[Field], reply: FormAnswers) -> list[Claim]:
    free_text = {item.id: item for item in fields if item.kind in FREE_TEXT}
    claims = [
        Claim(answer.id, free_text[answer.id].label, answer.value)
        for answer in reply.answers
        if answer.id in free_text
    ]
    if reply.cover_letter:
        claims.append(Claim(COVER_LETTER_KEY, "the cover letter", reply.cover_letter))
    return claims


def made_up_numbers(
    context: FormContext, fields: Sequence[Field], reply: FormAnswers
) -> dict[Claim, list[str]]:
    known = numbers(f"{context.resume_text}\n{candidate_facts(context.profile)}")
    found = {}
    for claim in _claims(fields, reply):
        extra = sorted(numbers(claim.text) - known - numbers(claim.label))
        if extra:
            found[claim] = extra
    return found


def problems(found: Unsupported) -> tuple[str, ...]:
    return tuple(
        f'The answer for "{claim.label}" used numbers that are in neither the resume nor the '
        f"facts: {', '.join(extra)}. Use only numbers from those, or leave the number out."
        for claim, extra in found.items()
    )


def without(reply: FormAnswers, found: Unsupported) -> FormAnswers:
    keys = {claim.key for claim in found}
    return replace(
        reply,
        answers=tuple(answer for answer in reply.answers if answer.id not in keys),
        cover_letter=None if COVER_LETTER_KEY in keys else reply.cover_letter,
    )
