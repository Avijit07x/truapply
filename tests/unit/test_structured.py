from dataclasses import replace

from tests.unit import samples
from truapply.core.documents import ResumeEntry, ResumeSection
from truapply.resume.contract import Draft
from truapply.resume.structured import StructuredResume, to_html, to_json


def test_html_escapes_everything() -> None:
    data = replace(samples.resume_data(), headline="<script>alert(1)</script>")
    html = to_html(data)
    assert "<script>alert" not in html
    assert "&lt;script&gt;" in html


def test_readable_text_lists_every_bullet() -> None:
    resume = StructuredResume(samples.resume_data())
    text = resume.readable(resume.source)
    assert "- Cut load time by 30%." in text
    assert "EXPERIENCE" in text


def test_reordering_bullets_has_no_problems() -> None:
    data = samples.resume_data()
    section = data.sections[1]
    entry = section.entries[0]
    swapped = replace(entry, bullets=tuple(reversed(entry.bullets)))
    tailored = replace(data, sections=(data.sections[0], replace(section, entries=(swapped,))))
    assert StructuredResume(data).problems(Draft(to_json(tailored), ())) == []


def test_changed_contact_and_invented_entries_are_problems() -> None:
    data = samples.resume_data()
    invented = ResumeSection(
        "Experience",
        (),
        (ResumeEntry("Big Tech", "Staff Engineer", "2020", "Remote", ("Led 50 people.",)),),
    )
    tailored = replace(data, contact=("someone@else.com",), sections=(data.sections[0], invented))
    problems = StructuredResume(data).problems(Draft(to_json(tailored), ()))
    assert problems == [
        "the name or contact details changed",
        "removed entries: Acme Analytics",
        "new entries: Big Tech",
    ]
