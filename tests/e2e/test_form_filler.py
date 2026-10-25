from collections.abc import Iterator, Sequence
from dataclasses import dataclass, replace
from pathlib import Path

import pytest
from playwright.sync_api import Page, sync_playwright

from satyaapply.apply.fields import read_fields
from satyaapply.apply.fill import Files, fill_field
from satyaapply.apply.flow import ApplyRequest, Attempt, apply
from satyaapply.core.forms import (
    RESUME_FILE,
    Answer,
    Field,
    FieldKind,
    FormAnswers,
    FormContext,
    Unknown,
)
from satyaapply.core.models import Status
from satyaapply.store.answers import question_key
from tests.unit import samples

pytestmark = pytest.mark.e2e

FORM = Path(__file__).with_name("form.html")
ANSWERS = {
    "first name": "Asha",
    "last name": "Rao",
    "email": "asha.rao@example.com",
    "country code": "India",
    "phone": "+91 90000 00000",
    "resume cv": RESUME_FILE,
    "link to your github profile": "https://github.com/asha-rao",
    "where will you work from city you will work from for payroll": "Bengaluru, India",
    "are you legally authorized to work in india": "Yes",
    "will you now or in the future require visa sponsorship": "No",
    "how many years of experience do you have with react": "2",
    "country": "India",
    "earliest start date": "2026-12-01",
    "which of these have you used": "React | TypeScript",
    "notice period": "30 days",
    "how did you hear about us": "Other",
    "please specify": "Company careers page",
    "portfolio link": "https://asha.example.com",
    "why do you want to work at northwind": "Your dashboards match my work.",
    "i agree to the privacy policy": "yes",
}
ATTESTATION = "i confirm i did not use ai tools to prepare this application"
CLEARANCE = "do you hold an active government security clearance"
WHY = "why do you want to work at northwind"
BOAST = "I shipped 1,600 dashboards last year."
BASE_LABEL = "Where will you work from? * City you will work from, for payroll"


@dataclass
class FakeAnswerer:
    hold_back: frozenset[str] = frozenset()
    boasts: int = 0
    calls: int = 0

    def __call__(self, context: FormContext, fields: Sequence[Field]) -> FormAnswers:
        self.calls += 1
        keys = {item.id: question_key(item.label) for item in fields}
        if ATTESTATION in keys.values():
            return FormAnswers((), (), None, "employer asks to confirm no AI was used", None)
        unknown = tuple(Unknown(id_, key, True) for id_, key in keys.items() if key == CLEARANCE)
        withheld = self.hold_back if not context.errors else frozenset()
        boast = self.boasts > 0 and WHY in keys.values()
        self.boasts -= boast
        answers = tuple(
            Answer(id_, BOAST if boast and key == WHY else ANSWERS[key], True, False)
            for id_, key in keys.items()
            if key in ANSWERS and key not in withheld
        )
        return FormAnswers(answers, unknown, None, None, None)


@pytest.fixture(scope="module")
def browser_page() -> Iterator[Page]:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page()
        yield page
        browser.close()


@pytest.fixture
def resume_pdf(tmp_path: Path) -> Path:
    path = tmp_path / "Asha_Rao_Resume.pdf"
    path.write_bytes(b"%PDF-1.4 test resume")
    return path


def request_for(
    tmp_path: Path, resume_pdf: Path, query: str = "", dry_run: bool = False
) -> ApplyRequest:
    job = replace(samples.job(), apply_url=f"{FORM.as_uri()}{query}")
    return ApplyRequest(
        context=FormContext(samples.profile(resume_pdf), "Resume text", job),
        files=Files(resume=None if dry_run else resume_pdf, cover_letter=None),
        known={},
        dry_run=dry_run,
        cover_letter_target=tmp_path / "Cover_Letter.pdf",
    )


def submission(page: Page) -> dict[str, object] | None:
    result = page.evaluate("window.__submission || null")
    return result if isinstance(result, dict) else None


@pytest.mark.parametrize("run", range(10))
def test_the_whole_form_is_filled_and_submitted(
    browser_page: Page, tmp_path: Path, resume_pdf: Path, run: int
) -> None:
    attempt = apply(browser_page, request_for(tmp_path, resume_pdf), FakeAnswerer())
    assert (attempt.status, attempt.note) == (Status.APPLIED, "submitted and confirmed"), run
    assert submission(browser_page) == {
        "first": "Asha",
        "last": "Rao",
        "email": "asha.rao@example.com",
        "phone": "+91 90000 00000",
        "resume": "Asha_Rao_Resume.pdf",
        "autofill": "",
        "dial": "India +91",
        "github": "https://github.com/asha-rao",
        "base": "Bengaluru, Karnataka, India",
        "heard": "Other",
        "heard_other": "Company careers page",
        "portfolio": "https://asha.example.com",
        "authorized": "yes",
        "sponsorship": "no",
        "years": "2",
        "country": "India",
        "start": "2026-12-01",
        "skills": ["react", "typescript"],
        "notice": "30 days",
        "why": "Your dashboards match my work.",
        "attest": None,
        "consent": "on",
    }


def test_a_dry_run_stops_before_submit_and_uploads_nothing(
    browser_page: Page, tmp_path: Path, resume_pdf: Path
) -> None:
    attempt = apply(browser_page, request_for(tmp_path, resume_pdf, dry_run=True), FakeAnswerer())
    assert attempt.status is Status.READY
    assert submission(browser_page) is None
    assert browser_page.locator("#resume").evaluate("input => input.files.length") == 0
    assert any(sent.answer.endswith("not uploaded)") for sent in attempt.sent)


def test_saved_answers_are_used_without_asking_the_ai(
    browser_page: Page, tmp_path: Path, resume_pdf: Path
) -> None:
    answerer = FakeAnswerer()
    request = replace(request_for(tmp_path, resume_pdf), known={"notice period": "60 days"})
    attempt = apply(browser_page, request, answerer)
    assert attempt.status is Status.APPLIED
    found = submission(browser_page)
    assert found is not None
    assert found["notice"] == "60 days"


def test_a_no_ai_attestation_is_never_ticked(
    browser_page: Page, tmp_path: Path, resume_pdf: Path
) -> None:
    attempt = apply(browser_page, request_for(tmp_path, resume_pdf, "?attest=1"), FakeAnswerer())
    assert attempt.status is Status.SKIPPED
    assert submission(browser_page) is None
    assert not browser_page.locator("#attest").is_checked()


def test_an_unknown_legal_question_waits_for_the_user(
    browser_page: Page, tmp_path: Path, resume_pdf: Path
) -> None:
    attempt: Attempt = apply(
        browser_page, request_for(tmp_path, resume_pdf, "?legal=1"), FakeAnswerer()
    )
    assert attempt.status is Status.NEEDS_INPUT
    assert CLEARANCE in attempt.questions
    assert submission(browser_page) is None


def test_a_closed_job_is_marked_closed(
    browser_page: Page, tmp_path: Path, resume_pdf: Path
) -> None:
    attempt = apply(browser_page, request_for(tmp_path, resume_pdf, "?closed=1"), FakeAnswerer())
    assert attempt.status is Status.CLOSED


def test_form_errors_are_sent_back_and_fixed(
    browser_page: Page, tmp_path: Path, resume_pdf: Path
) -> None:
    answerer = FakeAnswerer(hold_back=frozenset({"notice period"}))
    attempt = apply(browser_page, request_for(tmp_path, resume_pdf), answerer)
    assert attempt.status is Status.APPLIED
    found = submission(browser_page)
    assert found is not None
    assert found["notice"] == "30 days"
    assert answerer.calls >= 3


def test_labels_read_the_way_a_person_sees_them(browser_page: Page) -> None:
    browser_page.goto(FORM.as_uri())
    fields = {item.label: item for item in read_fields(browser_page)}
    assert fields["Link to your GitHub profile *"].required
    assert fields[BASE_LABEL].required
    assert fields[BASE_LABEL].kind is FieldKind.COMBOBOX
    assert not [label for label in fields if "autofill" in label.lower()]


def submitted_why(page: Page, tmp_path: Path, resume_pdf: Path, boasts: int) -> object:
    attempt = apply(page, request_for(tmp_path, resume_pdf), FakeAnswerer(boasts=boasts))
    assert attempt.status is Status.APPLIED
    assert all(BOAST not in sent.answer for sent in attempt.sent)
    found = submission(page)
    assert found is not None
    return found["why"]


def test_an_answer_with_a_made_up_number_is_redone(
    browser_page: Page, tmp_path: Path, resume_pdf: Path
) -> None:
    assert submitted_why(browser_page, tmp_path, resume_pdf, boasts=1) == ANSWERS[WHY]


def test_an_answer_that_keeps_a_made_up_number_is_left_out(
    browser_page: Page, tmp_path: Path, resume_pdf: Path
) -> None:
    assert submitted_why(browser_page, tmp_path, resume_pdf, boasts=2) == ""


def test_a_choice_shown_outside_the_box_counts_as_filled(browser_page: Page) -> None:
    browser_page.goto(FORM.as_uri())
    dial = next(item for item in read_fields(browser_page) if item.label == "Country code *")
    assert dial.required
    assert not dial.value
    assert fill_field(browser_page, dial, "India", Files(None, None)) == "India +91"
    assert [item.value for item in read_fields(browser_page) if item.id == dial.id] == ["India +91"]
