from pathlib import Path

import pytest

from tests.unit import samples
from truapply.apply.answering import answer_form
from truapply.apply.claims import made_up_numbers, without
from truapply.apply.options import as_number, best_option, is_truthy
from truapply.core.forms import Answer, Field, FieldKind, FormAnswers, FormContext


def field(kind: FieldKind, label: str, options: tuple[str, ...] = ()) -> Field:
    return Field("f1", kind, label, True, options, "", None)


@pytest.mark.parametrize(
    ("options", "answer", "expected"),
    [
        (("Yes", "No"), "yes", 0),
        (("No", "Not sure"), "No", 0),
        (("Not applicable", "No"), "No", 1),
        (("Yes, I am authorized", "No, I am not"), "Yes", 0),
        (("Immediate", "30 days"), "30", 1),
        (("India", "United States"), "Germany", None),
        (("Indianapolis, Indiana", "Bengaluru, Karnataka, India"), "Bengaluru, India", 1),
        (("Yes", "No"), "", None),
    ],
)
def test_options_match_the_way_people_answer(
    options: tuple[str, ...], answer: str, expected: int | None
) -> None:
    assert best_option(options, answer) == expected


def test_truthy_answers_tick_a_checkbox() -> None:
    assert all(is_truthy(value) for value in ("yes", "Yes", "true", "I agree"))
    assert not any(is_truthy(value) for value in ("no", "", "false"))


def test_numbers_are_taken_out_of_text() -> None:
    assert as_number("2 years") == "2"
    assert as_number("about 2.5") == "2.5"
    assert as_number("none") is None


def nothing_new(_context: FormContext, _fields: object) -> FormAnswers:
    return FormAnswers((), (), None, None, None)


def test_saved_answers_fill_fields_whose_options_fit(tmp_path: Path) -> None:
    fields = [
        field(FieldKind.TEXT, "Notice period *"),
        field(FieldKind.SELECT, "Country", ("India", "Germany")),
        field(FieldKind.SELECT, "Shirt size", ("S", "M")),
        field(FieldKind.FILE, "Resume"),
    ]
    fields = [
        Field(f"f{n}", item.kind, item.label, True, item.options, "", None)
        for n, item in enumerate(fields)
    ]
    known = {"notice period": "30 days", "country": "India", "shirt size": "XXL", "resume": "x"}
    context = FormContext(samples.profile(tmp_path / "m.tex"), "", samples.job())
    reply = answer_form(context, fields, known, nothing_new)
    assert reply.answers == {"f0": "30 days", "f1": "India", "f3": "RESUME"}


def test_only_numbers_missing_from_the_resume_and_facts_are_flagged(tmp_path: Path) -> None:
    context = FormContext(
        samples.profile(tmp_path / "m.tex"), "Built 40 components.", samples.job()
    )
    fields = [
        Field("f1", FieldKind.TEXTAREA, "Tell us about a project", False, (), "", None),
        Field("f2", FieldKind.TEXT, "Top 3 strengths", False, (), "", None),
        Field("f3", FieldKind.NUMBER, "Years of React", False, (), "", None),
    ]
    reply = FormAnswers(
        (
            Answer("f1", "I built 40 components and 1,600 stars.", False, False),
            Answer("f2", "3 strengths: speed, care, tests", False, False),
            Answer("f3", "2", True, False),
        ),
        (),
        None,
        None,
        "I cut load time by 70%.",
    )
    found = made_up_numbers(context, fields, reply)
    assert {claim.key: extra for claim, extra in found.items()} == {
        "f1": ["1600"],
        "cover_letter": ["70"],
    }
    kept = without(reply, found)
    assert [answer.id for answer in kept.answers] == ["f2", "f3"]
    assert kept.cover_letter is None
