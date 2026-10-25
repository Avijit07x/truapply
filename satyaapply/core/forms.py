from dataclasses import dataclass
from enum import StrEnum

from satyaapply.core.models import Job
from satyaapply.core.profile import Profile

RESUME_FILE = "RESUME"
COVER_LETTER_FILE = "COVER_LETTER"
MULTI_VALUE_SEPARATOR = " | "


class FieldKind(StrEnum):
    TEXT = "text"
    EMAIL = "email"
    TEL = "tel"
    NUMBER = "number"
    URL = "url"
    DATE = "date"
    TEXTAREA = "textarea"
    SELECT = "select"
    RADIO = "radio"
    CHECKBOX = "checkbox"
    CHECKBOXES = "checkboxes"
    FILE = "file"
    COMBOBOX = "combobox"


@dataclass(frozen=True)
class Field:
    id: str
    kind: FieldKind
    label: str
    required: bool
    options: tuple[str, ...]
    value: str
    max_length: int | None


@dataclass(frozen=True)
class Answer:
    id: str
    value: str
    reusable: bool
    guessed: bool


@dataclass(frozen=True)
class Unknown:
    id: str
    question: str
    legal: bool


@dataclass(frozen=True)
class FormAnswers:
    answers: tuple[Answer, ...]
    unknown: tuple[Unknown, ...]
    blocker: str | None
    skip_reason: str | None
    cover_letter: str | None


@dataclass(frozen=True)
class FormContext:
    profile: Profile
    resume_text: str
    job: Job
    errors: tuple[str, ...] = ()


@dataclass(frozen=True)
class Sent:
    question: str
    answer: str
