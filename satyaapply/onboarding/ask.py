import re
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from typing import Generic, TypeVar

from satyaapply.core.errors import SetupCancelledError

T = TypeVar("T")

RULE_WIDTH = 64
AMOUNT = re.compile(r"^\s*([\d][\d.,]*)\s*(lpa|lakhs?|l|crores?|cr|k)?\s*$", re.IGNORECASE)
DAY_FIRST_DATE = re.compile(r"^\s*(\d{1,2})[/.-](\d{1,2})[/.-](\d{4})\s*$")
MULTIPLIERS = {
    "lpa": 100_000,
    "lakh": 100_000,
    "lakhs": 100_000,
    "l": 100_000,
    "cr": 10_000_000,
    "crore": 10_000_000,
    "crores": 10_000_000,
    "k": 1_000,
}


@dataclass(frozen=True)
class Option(Generic[T]):
    label: str
    value: T
    note: str = ""


def _read(prompt: str) -> str:
    try:
        return input(prompt).strip()
    except EOFError:
        raise SetupCancelledError("Setup stopped before it finished.") from None


def heading(title: str) -> None:
    print(f"\n── {title} {'─' * max(0, RULE_WIDTH - len(title))}")


def say(message: str) -> None:
    print(f"  {message}")


def _show(question: str, options: Sequence[Option[T]], defaults: set[int]) -> None:
    print(f"\n{question}")
    for number, option in enumerate(options, start=1):
        tag = "  (recommended)" if number - 1 in defaults else ""
        print(f"  {number}. {option.label}{tag}")
        if option.note:
            print(f"     {option.note}")


def _picks(answer: str, count: int) -> list[int]:
    parts = [part.strip() for part in answer.split(",") if part.strip()]
    if not parts or not all(part.isdigit() and 1 <= int(part) <= count for part in parts):
        return []
    return sorted({int(part) - 1 for part in parts})


def choose(question: str, options: Sequence[Option[T]], default: int = 0) -> T:
    _show(question, options, {default})
    while True:
        answer = _read(f"  Choose 1-{len(options)} [Enter = {default + 1}]: ")
        picks = [default] if not answer else _picks(answer, len(options))
        if len(picks) == 1:
            return options[picks[0]].value
        say("Type one of the numbers above.")


def choose_many(question: str, options: Sequence[Option[T]], defaults: Sequence[int]) -> list[T]:
    _show(question, options, set(defaults))
    shown = ",".join(str(index + 1) for index in defaults)
    while True:
        answer = _read(f"  Choose one or more, like 1,3 [Enter = {shown}]: ")
        picks = list(defaults) if not answer else _picks(answer, len(options))
        if picks:
            return [options[index].value for index in picks]
        say("Type numbers from the list, separated by commas.")


def text(question: str, default: str = "", required: bool = False) -> str:
    shown = f" [{default}]" if default else ""
    while True:
        answer = _read(f"\n{question}{shown}: ") or default
        if answer or not required:
            return answer
        say("This one is needed.")


def items(question: str, default: Sequence[str], required: bool = False) -> tuple[str, ...]:
    while True:
        answer = text(f"{question} (comma-separated)", ", ".join(default))
        values = tuple(item.strip() for item in answer.split(",") if item.strip())
        if values or not required:
            return values
        say("Add at least one.")


def yes_no(question: str, default: bool) -> bool:
    return choose(question, [Option("Yes", True), Option("No", False)], 0 if default else 1)


def parse_amount(answer: str) -> int | None:
    match = AMOUNT.match(answer)
    if not match:
        return None
    try:
        number = float(match.group(1).replace(",", ""))
    except ValueError:
        return None
    unit = (match.group(2) or "").lower()
    return round(number * MULTIPLIERS.get(unit, 1))


def amount(question: str, required: bool, minimum: int = 1) -> int | None:
    while True:
        answer = text(question)
        if not answer and not required:
            return None
        value = parse_amount(answer)
        if value is not None and value >= minimum:
            return value
        say(f"Type a yearly amount of at least {minimum:,}, like 1200000 or 12 LPA.")


def parse_date(answer: str) -> date | None:
    try:
        return date.fromisoformat(answer.strip())
    except ValueError:
        pass
    match = DAY_FIRST_DATE.match(answer)
    if not match:
        return None
    day, month, year = (int(group) for group in match.groups())
    try:
        return date(year, month, day)
    except ValueError:
        return None


def optional_date(question: str) -> date | None:
    while True:
        answer = text(question)
        if not answer:
            return None
        parsed = parse_date(answer)
        if parsed:
            say(f"Saved as {parsed:%d %B %Y}.")
            return parsed
        say("Type it like 2001-05-07 or 07/05/2001 (day first).")
