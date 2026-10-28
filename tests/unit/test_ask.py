from collections.abc import Iterator
from datetime import date

import pytest

from truapply.core.errors import SetupCancelledError
from truapply.onboarding import ask
from truapply.onboarding.ask import Option, parse_amount, parse_date

OPTIONS = [Option("One", 1), Option("Two", 2), Option("Three", 3)]


def answers(monkeypatch: pytest.MonkeyPatch, *typed: str) -> None:
    queue: Iterator[str] = iter(typed)

    def fake_input(_prompt: str) -> str:
        try:
            return next(queue)
        except StopIteration:
            raise EOFError from None

    monkeypatch.setattr("builtins.input", fake_input)


@pytest.mark.parametrize(
    ("typed", "expected"),
    [
        ("1200000", 1_200_000),
        ("12,00,000", 1_200_000),
        ("12 LPA", 1_200_000),
        ("12.5 lakhs", 1_250_000),
        ("1.2 cr", 12_000_000),
        ("85k", 85_000),
        ("twelve", None),
        ("1.2.3", None),
    ],
)
def test_amounts_are_understood_the_way_people_type_them(typed: str, expected: int | None) -> None:
    assert parse_amount(typed) == expected


@pytest.mark.parametrize(
    ("typed", "expected"),
    [
        ("2001-05-07", date(2001, 5, 7)),
        ("07/05/2001", date(2001, 5, 7)),
        ("7-5-2001", date(2001, 5, 7)),
        ("31/02/2001", None),
        ("May 7", None),
    ],
)
def test_dates_are_day_first(typed: str, expected: date | None) -> None:
    assert parse_date(typed) == expected


def test_enter_picks_the_recommended_option(monkeypatch: pytest.MonkeyPatch) -> None:
    answers(monkeypatch, "")
    assert ask.choose("Pick", OPTIONS, default=1) == 2


def test_invalid_choices_are_asked_again(monkeypatch: pytest.MonkeyPatch) -> None:
    answers(monkeypatch, "9", "x", "1,2", "3")
    assert ask.choose("Pick", OPTIONS) == 3


def test_several_choices_can_be_picked(monkeypatch: pytest.MonkeyPatch) -> None:
    answers(monkeypatch, "3, 1")
    assert ask.choose_many("Pick", OPTIONS, defaults=[0]) == [1, 3]


def test_required_text_is_asked_again_until_given(monkeypatch: pytest.MonkeyPatch) -> None:
    answers(monkeypatch, "", "Asha")
    assert ask.text("Name", required=True) == "Asha"


def test_running_out_of_input_cancels_setup(monkeypatch: pytest.MonkeyPatch) -> None:
    answers(monkeypatch)
    with pytest.raises(SetupCancelledError):
        ask.text("Name")
