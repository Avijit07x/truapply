from dataclasses import dataclass
from datetime import date
from enum import StrEnum
from typing import TypeVar

from truapply.tracker.body import Body, flag, number, strings

MAX_ITEMS = 50
MAX_TEXT = 200
MAX_LONG_TEXT = 4000

E = TypeVar("E", bound=StrEnum)


@dataclass(frozen=True)
class Number:
    name: str
    label: str
    low: int
    high: int


class Reader:
    def __init__(self, body: Body) -> None:
        self.body = body
        self.problems: list[str] = []

    def items(self, name: str, label: str) -> tuple[str, ...]:
        given = strings(self.body, name)
        if given is None:
            self.problems.append(f"{label}: send a list of words.")
            return ()
        kept: dict[str, str] = {}
        for part in given:
            words = " ".join(part.split())
            if words:
                kept.setdefault(words.casefold(), words)
        found = tuple(kept.values())
        if len(found) > MAX_ITEMS or any(len(item) > MAX_TEXT for item in found):
            self.problems.append(
                f"{label}: up to {MAX_ITEMS} entries, each up to {MAX_TEXT} characters."
            )
        return found

    def text(self, name: str, label: str, *, required: bool = False) -> str:
        value = self.body.get(name)
        words = " ".join(value.split()) if isinstance(value, str) else ""
        if len(words) > MAX_TEXT:
            self.problems.append(f"{label}: up to {MAX_TEXT} characters.")
        elif required and not words:
            self.problems.append(f"{label}: can't be empty.")
        return words

    def long_text(self, name: str, label: str) -> str:
        value = self.body.get(name)
        written = value.strip() if isinstance(value, str) else ""
        if len(written) > MAX_LONG_TEXT:
            self.problems.append(f"{label}: up to {MAX_LONG_TEXT:,} characters.")
        return written

    def number(self, spec: Number) -> int:
        value = number(self.body, spec.name)
        if value is not None and spec.low <= value <= spec.high:
            return value
        self.problems.append(
            f"{spec.label}: enter a whole number from {spec.low:,} to {spec.high:,}."
        )
        return spec.low

    def optional_number(self, spec: Number) -> int | None:
        return None if self.body.get(spec.name) is None else self.number(spec)

    def decimal(self, spec: Number) -> float:
        value = self.body.get(spec.name)
        given = None if isinstance(value, bool) or not isinstance(value, int | float) else value
        if given is not None and spec.low <= given <= spec.high:
            return float(given)
        self.problems.append(f"{spec.label}: enter a number from {spec.low} to {spec.high}.")
        return float(spec.low)

    def flag(self, name: str, label: str) -> bool:
        value = flag(self.body, name)
        if value is None:
            self.problems.append(f"{label}: tick or untick it.")
        return bool(value)

    def choice(self, name: str, label: str, kind: type[E], current: E) -> E:
        value = self.body.get(name)
        if isinstance(value, str) and value in {item.value for item in kind}:
            return kind(value)
        self.problems.append(f"{label}: pick one of the choices.")
        return current

    def day(self, name: str, label: str) -> date | None:
        value = self.body.get(name)
        if value is None or value == "":
            return None
        if isinstance(value, str):
            try:
                return date.fromisoformat(value)
            except ValueError:
                pass
        self.problems.append(f"{label}: pick a date, or leave it empty.")
        return None
