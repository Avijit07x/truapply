from dataclasses import dataclass, field
from datetime import date
from enum import StrEnum
from pathlib import Path

import pytest

from satyaapply.core.codec import decode, encode, json_schema
from satyaapply.core.errors import DecodeError


class Color(StrEnum):
    RED = "red"
    BLUE = "blue"


@dataclass(frozen=True)
class Inner:
    amount: int
    note: str | None


@dataclass(frozen=True)
class Outer:
    name: str
    colors: tuple[Color, ...]
    inner: Inner
    born: date | None
    home: Path
    ratio: float = 1.0
    tags: tuple[str, ...] = field(default_factory=tuple)


VALID = {
    "name": "x",
    "colors": ["red", "blue"],
    "inner": {"amount": 3, "note": None},
    "born": "2001-05-07",
    "home": "~/resume.tex",
}


def test_decodes_nested_types_and_fills_defaults() -> None:
    value = decode(Outer, VALID)
    home = Path("~/resume.tex").expanduser()
    assert value == Outer("x", (Color.RED, Color.BLUE), Inner(3, None), date(2001, 5, 7), home)


def test_encode_then_decode_round_trips() -> None:
    value = decode(Outer, VALID)
    assert decode(Outer, encode(value)) == value


@pytest.mark.parametrize(
    ("change", "expected"),
    [
        ({"inner": {"amount": "3", "note": None}}, "inner.amount must be a whole number"),
        ({"inner": {"amount": True, "note": None}}, "inner.amount must be a whole number"),
        ({"colors": ["green"]}, "colors[0] must be one of: red, blue"),
        ({"born": "07/05/2001"}, "born must be a date"),
        ({"surprise": 1}, "surprise is not a known field"),
    ],
)
def test_bad_values_name_the_exact_field(change: dict[str, object], expected: str) -> None:
    with pytest.raises(DecodeError, match=expected.replace("[", r"\[").replace("]", r"\]")):
        decode(Outer, {**VALID, **change})


def test_missing_required_field_is_reported() -> None:
    data = {key: value for key, value in VALID.items() if key != "name"}
    with pytest.raises(DecodeError, match="name is required"):
        decode(Outer, data)


def test_schema_requires_every_field_and_forbids_extras() -> None:
    schema = json_schema(Inner)
    assert schema["required"] == ["amount", "note"]
    assert schema["additionalProperties"] is False
    assert schema["properties"] == {
        "amount": {"type": "integer"},
        "note": {"anyOf": [{"type": "string"}, {"type": "null"}]},
    }
