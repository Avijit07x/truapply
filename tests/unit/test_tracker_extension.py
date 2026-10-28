import base64
import hashlib
import json
from collections.abc import Sequence
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path

import pytest

from tests.unit import samples
from tests.unit.tracker_api import JSON_TYPE, Reply, fetch, get, running
from truapply.ai.replies import Posting
from truapply.core.forms import RESUME_FILE, Answer, Field, FormAnswers, FormContext, Unknown
from truapply.core.models import Job, Source, Status
from truapply.core.paths import Paths
from truapply.core.profile import save
from truapply.store import answers, feedback, jobs, records
from truapply.store.answers import AnswerSource, SavedAnswer
from truapply.store.db import connect
from truapply.store.feedback import FeedbackKind
from truapply.store.jobs import AttemptRecord
from truapply.tracker import extension
from truapply.tracker.extension import EXTENSION_ID, EXTENSION_ORIGIN, NO_JOB
from truapply.tracker.server import TrackerServer

NOW = datetime(2026, 10, 27, 12, 0, tzinfo=UTC)
MANIFEST = Path(__file__).resolve().parents[2] / "web" / "extension" / "manifest.json"
GREENHOUSE = Job(
    Source.CAREER_PAGES,
    "greenhouse/northwind/7001",
    "https://job-boards.greenhouse.io/northwind/jobs/7001",
    "Northwind",
    "Frontend Engineer",
    apply_url="https://job-boards.greenhouse.io/embed/job_app?for=northwind&token=7001",
)
ASHBY = Job(
    Source.CAREER_PAGES,
    "ashby/Contoso/5f1c",
    "https://jobs.ashbyhq.com/Contoso/5f1c",
    "Contoso",
    "Frontend Engineer",
    apply_url="https://jobs.ashbyhq.com/Contoso/5f1c/application",
)


def field(id_: str, kind: str, label: str, options: Sequence[str] = ()) -> dict[str, object]:
    return {
        "id": id_,
        "kind": kind,
        "label": label,
        "required": True,
        "options": list(options),
        "value": "",
        "max_length": None,
    }


def call(server: TrackerServer, path: str, body: object, origin: str = EXTENSION_ORIGIN) -> Reply:
    headers = {"Origin": origin, "Content-Type": JSON_TYPE}
    status, _, answer = fetch(server, path, json.dumps(body).encode(), headers)
    return status, json.loads(answer)


@pytest.fixture
def paths(tmp_path: Path) -> Paths:
    home = Paths(tmp_path / "home")
    home.ensure()
    master = tmp_path / "master.tex"
    master.write_text("\\begin{document}Asha Rao, React\\end{document}", encoding="utf-8")
    save(home, samples.profile(master))
    pdf = home.job_dir(1) / "Asha_Rao_Resume.pdf"
    pdf.parent.mkdir(parents=True, exist_ok=True)
    pdf.write_bytes(b"%PDF-1.4")
    with closing(connect(home.database)) as db:
        jobs.add_many(db, [GREENHOUSE, ASHBY], NOW)
        jobs.record_attempt(db, 1, AttemptRecord(Status.READY, NOW, "", (), pdf))
    return home


class Asked:
    def __init__(self, reply: FormAnswers) -> None:
        self.reply = reply
        self.labels: list[str] = []

    def __call__(self, _context: FormContext, fields: Sequence[Field]) -> FormAnswers:
        self.labels.extend(item.label for item in fields)
        return self.reply


def answered(*found: tuple[str, str], unknown: Sequence[Unknown] = ()) -> FormAnswers:
    given = tuple(Answer(id_, value, reusable=True, guessed=False) for id_, value in found)
    return FormAnswers(given, tuple(unknown), None, None, None)


def test_the_manifest_key_gives_the_extension_id_the_app_trusts() -> None:
    key = json.loads(MANIFEST.read_text(encoding="utf-8"))["key"]
    digest = hashlib.sha256(base64.b64decode(key)).hexdigest()[:32]
    assert "".join(chr(ord("a") + int(char, 16)) for char in digest) == EXTENSION_ID


def test_other_websites_and_extensions_are_refused(paths: Paths) -> None:
    with running(paths) as server:
        for origin in (
            "https://evil.example",
            "chrome-extension://abcdefghijklmnopabcdefghijklmnop",
        ):
            status, _ = call(server, "/api/extension/job", {"url": GREENHOUSE.url}, origin)
            assert status == 403


@pytest.mark.parametrize(
    ("url", "job_id"),
    [
        (GREENHOUSE.url, 1),
        (GREENHOUSE.apply_url, 1),
        ("https://job-boards.greenhouse.io/northwind/jobs/7001?gh_src=abc", 1),
        ("https://job-boards.greenhouse.io/embed/job_app?for=northwind&token=7001&gh_src=x", 1),
        ("https://job-boards.greenhouse.io/embed/job_app/confirmation?for=northwind&token=7001", 1),
        ("https://jobs.lever.co/northwind/7001/thanks", None),
        (ASHBY.apply_url, 2),
        ("https://jobs.ashbyhq.com/contoso/5f1c/application?utm_source=x", 2),
    ],
)
def test_a_job_page_finds_its_job(paths: Paths, url: str, job_id: int | None) -> None:
    with running(paths) as server:
        status, body = call(server, "/api/extension/job", {"url": url})
    assert status == 200
    if job_id is None:
        assert body["job"] is None
        return
    assert body["job"]["id"] == job_id
    assert body["job"]["status"] == ("ready" if job_id == 1 else "new")


def test_a_page_the_app_does_not_know_finds_nothing(paths: Paths) -> None:
    with running(paths) as server:
        _, body = call(server, "/api/extension/job", {"url": "https://jobs.lever.co/x/123/apply"})
    assert body == {"job": None}


def test_saved_answers_fill_without_asking_the_ai(
    paths: Paths, monkeypatch: pytest.MonkeyPatch
) -> None:
    asked = Asked(answered())
    monkeypatch.setattr(extension, "answer_fields", asked)
    with closing(connect(paths.database)) as db:
        answers.save_many(db, [SavedAnswer("Notice period", "30 days", AnswerSource.USER)], NOW)
    fields = [field("f1", "text", "Notice period *"), field("f2", "file", "Resume/CV *")]
    with running(paths) as server:
        status, body = call(server, "/api/extension/jobs/1/answers", {"fields": fields})
    assert status == 200
    assert body["answers"] == [{"id": "f1", "value": "30 days"}, {"id": "f2", "value": RESUME_FILE}]
    assert asked.labels == []


def test_consent_is_never_answered_and_is_left_for_you(
    paths: Paths, monkeypatch: pytest.MonkeyPatch
) -> None:
    asked = Asked(answered(("f1", "yes"), ("f2", "Yes")))
    monkeypatch.setattr(extension, "answer_fields", asked)
    fields = [
        field("f1", "checkbox", "I agree to the privacy policy *"),
        field("f2", "combobox", "Do you consent to AI-assisted interview transcription?*"),
        field("f3", "radio", "SMS", ["Yes - I consent to receiving SMS", "No - I do not consent"]),
        field("f4", "checkbox", "I confirm that all the information provided above is true"),
        field("f5", "checkbox", "I hereby declare that the details above are accurate"),
        field("f6", "radio", "I certify this application is my own work", ["Yes", "No"]),
    ]
    with running(paths) as server:
        _, body = call(server, "/api/extension/jobs/1/answers", {"fields": fields})
    assert body["answers"] == []
    assert [item["id"] for item in body["forYou"]] == ["f1", "f2", "f3", "f4", "f5", "f6"]
    assert asked.labels == []


def test_choices_come_back_as_the_exact_option_and_unknowns_are_left_for_you(
    paths: Paths, monkeypatch: pytest.MonkeyPatch
) -> None:
    legal = Unknown("f2", "Will you need sponsorship?", legal=True)
    asked = Asked(answered(("f1", "india"), ("f3", "maybe"), unknown=[legal]))
    monkeypatch.setattr(extension, "answer_fields", asked)
    fields = [
        field("f1", "combobox", "Country *", ["Indonesia +62", "India +91"]),
        field("f2", "select", "Will you need sponsorship? *", ["Yes", "No"]),
        field("f3", "radio", "Can you start in May? *", ["Yes", "No"]),
    ]
    with running(paths) as server:
        _, body = call(server, "/api/extension/jobs/1/answers", {"fields": fields})
    assert body["answers"] == [{"id": "f1", "value": "India +91"}]
    assert [item["id"] for item in body["forYou"]] == ["f2", "f3"]


def test_fields_the_page_already_filled_are_left_alone(
    paths: Paths, monkeypatch: pytest.MonkeyPatch
) -> None:
    asked = Asked(answered())
    monkeypatch.setattr(extension, "answer_fields", asked)
    typed = field("f1", "text", "Full name *") | {"value": "Asha Rao"}
    with running(paths) as server:
        _, body = call(server, "/api/extension/jobs/1/answers", {"fields": [typed]})
    assert body["answers"] == []
    assert asked.labels == []


def test_a_job_without_a_tailored_resume_sends_your_original_one(paths: Paths) -> None:
    with running(paths) as server:
        assert call(server, "/api/extension/job", {"url": ASHBY.url})[1]["job"]["resume"] is None
        paths.master_pdf.write_bytes(b"%PDF-1.4 original")
        job = call(server, "/api/extension/job", {"url": ASHBY.url})[1]["job"]
        status, _, pdf = fetch(server, "/jobs/2/resume.pdf")
    assert job["resume"] == paths.master_pdf.name
    assert (status, pdf) == (200, b"%PDF-1.4 original")


def test_submitting_marks_the_job_applied_and_learns_what_you_typed(paths: Paths) -> None:
    sent = [
        {"question": "Full name", "answer": "Asha Rao", "kind": "text", "yours": False},
        {"question": "Notice period", "answer": "15 days", "kind": "text", "yours": True},
        {"question": "Why us?", "answer": "Because I like it.", "kind": "textarea", "yours": True},
    ]
    with running(paths) as server:
        status, _ = call(server, "/api/extension/jobs/1/applied", {"sent": sent})
    assert status == 200
    with closing(connect(paths.database)) as db:
        record = records.find(db, 1)
        assert record is not None
        assert record.job.status is Status.APPLIED
        assert [item.question for item in record.sent] == ["Full name", "Notice period", "Why us?"]
        saved = answers.all_answers(db)
        assert [item.kind for item in feedback.for_job(db, 1)] == [
            FeedbackKind.FINISHED,
            FeedbackKind.EDIT,
        ]
    assert "15 days" in saved.values()
    assert "Because I like it." not in saved.values()


def test_applying_twice_changes_nothing(paths: Paths) -> None:
    with running(paths) as server:
        call(server, "/api/extension/jobs/1/applied", {"sent": []})
        status, _ = call(server, "/api/extension/jobs/1/applied", {"sent": []})
    assert status == 200
    with closing(connect(paths.database)) as db:
        assert len(feedback.for_job(db, 1)) == 1


def test_settings_say_where_the_extension_folder_is(paths: Paths) -> None:
    with running(paths) as server:
        status, body = get(server, "/api/settings")
    assert status == 200
    assert Path(body["extension"]["folder"]).parts[-2:] == ("truapply", "extension")


def test_profile_facts_fill_the_usual_fields_without_the_ai(
    paths: Paths, monkeypatch: pytest.MonkeyPatch
) -> None:
    asked = Asked(answered())
    monkeypatch.setattr(extension, "answer_fields", asked)
    fields = [
        field("f1", "text", "First Name*"),
        field("f2", "text", "Last Name*"),
        field("f3", "email", "Email*"),
        field("f4", "tel", "Phone*"),
        field("f5", "text", "GitHub URL"),
        field("f6", "text", "Current company"),
        field("f7", "combobox", "Location (City)*"),
        field("f8", "text", "LinkedIn Profile"),
        field("f9", "text", "LinkedIn of someone who can vouch for your work"),
        field("f10", "email", "Confirm your email*"),
        field("f11", "text", "Which country are you currently based in?*"),
        field("f12", "text", "Nationality*"),
    ]
    with running(paths) as server:
        _, body = call(server, "/api/extension/jobs/1/answers", {"fields": fields})
    assert {item["id"]: item["value"] for item in body["answers"]} == {
        "f1": "Asha",
        "f2": "Rao",
        "f3": "asha.rao@example.com",
        "f4": "+91 90000 00000",
        "f5": "https://github.com/asharao",
        "f6": "Acme Analytics",
        "f7": "Bengaluru",
        "f10": "asha.rao@example.com",
        "f11": "India",
        "f12": "India",
    }
    assert asked.labels == ["LinkedIn Profile", "LinkedIn of someone who can vouch for your work"]


def test_a_quick_request_fills_what_it_knows_and_names_the_rest_for_claude(
    paths: Paths, monkeypatch: pytest.MonkeyPatch
) -> None:
    asked = Asked(answered(("f2", "I like your product.")))
    monkeypatch.setattr(extension, "answer_fields", asked)
    fields = [field("f1", "email", "Email*"), field("f2", "textarea", "Why us?*")]
    with running(paths) as server:
        _, body = call(server, "/api/extension/jobs/1/answers", {"fields": fields, "ai": False})
    assert body["answers"] == [{"id": "f1", "value": "asha.rao@example.com"}]
    assert body["waiting"] == ["f2"]
    assert asked.labels == []


def test_claudes_answers_are_kept_on_the_job_so_opening_it_again_is_instant(
    paths: Paths, monkeypatch: pytest.MonkeyPatch
) -> None:
    fields = [field("f1", "textarea", "Why us?*")]
    once = Answer("f1", "I like your product.", reusable=False, guessed=False)
    first = Asked(FormAnswers((once,), (), None, None, None))
    monkeypatch.setattr(extension, "answer_fields", first)
    with running(paths) as server:
        call(server, "/api/extension/jobs/1/answers", {"fields": fields})
        again = Asked(answered())
        monkeypatch.setattr(extension, "answer_fields", again)
        _, body = call(server, "/api/extension/jobs/1/answers", {"fields": fields, "ai": False})
        call(server, "/api/extension/jobs/2/answers", {"fields": fields})
    assert first.labels == ["Why us?*"]
    assert body == {
        "answers": [{"id": "f1", "value": "I like your product."}],
        "forYou": [],
        "waiting": [],
        "note": None,
    }
    assert again.labels == ["Why us?*"]


POSTING = {
    "title": "Frontend Engineer",
    "company": "Wingspan",
    "location": "Bengaluru, India",
    "description": "Build React dashboards with TypeScript.",
}
LINKEDIN = "https://www.linkedin.com/jobs/view/4012345678/?refId=abc"


class Preparing:
    def __init__(self) -> None:
        self.jobs: list[int] = []

    def __call__(self, _paths: Paths, job_id: int) -> bool:
        self.jobs.append(job_id)
        return True


def test_a_job_page_is_added_and_prepared_in_the_background(
    paths: Paths, monkeypatch: pytest.MonkeyPatch
) -> None:
    preparing = Preparing()
    monkeypatch.setattr(extension, "start_preparing", preparing)
    with running(paths) as server:
        status, body = call(server, "/api/extension/add", {"url": LINKEDIN, "posting": POSTING})
        again = call(server, "/api/extension/add", {"url": LINKEDIN, "posting": POSTING})[1]
        search = "https://www.linkedin.com/jobs/search/?currentJobId=4012345678&keywords=react"
        found = call(server, "/api/extension/job", {"url": search})[1]
    assert status == 200
    assert body["preparing"] is True
    assert body["job"]["company"] == "Wingspan"
    assert again["job"]["id"] == found["job"]["id"] == body["job"]["id"] == 3
    assert preparing.jobs == [3, 3]
    with closing(connect(paths.database)) as db:
        record = records.find(db, 3)
    assert record is not None
    assert (record.job.source, record.job.external_id) == (Source.LINKEDIN, "4012345678")
    assert record.job.description == POSTING["description"]


def test_a_page_from_any_other_site_is_found_again_without_its_tracking_bits(
    paths: Paths, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(extension, "start_preparing", Preparing())
    page = "https://jobs.smartrecruiters.com/Acme/744000012345-frontend-engineer?trid=x#apply"
    with running(paths) as server:
        added = call(server, "/api/extension/add", {"url": page, "posting": POSTING})[1]
        plain = "https://jobs.smartrecruiters.com/Acme/744000012345-frontend-engineer"
        found = call(server, "/api/extension/job", {"url": plain})[1]
    assert found["job"]["id"] == added["job"]["id"]
    with closing(connect(paths.database)) as db:
        record = records.find(db, added["job"]["id"])
    assert record is not None
    assert record.job.source is Source.MANUAL


def test_a_page_without_job_details_is_read_by_claude(
    paths: Paths, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(extension, "start_preparing", Preparing())
    read: list[str] = []

    def reader(text: str) -> Posting:
        read.append(text)
        return Posting(**POSTING)

    monkeypatch.setattr(extension, "read_posting", reader)
    body = {
        "url": "https://www.naukri.com/job-listings-frontend-wingspan-160925500123",
        "text": "page",
    }
    with running(paths) as server:
        _, added = call(server, "/api/extension/add", body)
    assert read == ["page"]
    assert added["job"]["title"] == "Frontend Engineer"


def test_a_page_with_no_job_on_it_is_refused(paths: Paths, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(extension, "start_preparing", Preparing())
    monkeypatch.setattr(extension, "read_posting", lambda _text: Posting("", "", "", ""))
    with running(paths) as server:
        status, body = call(server, "/api/extension/add", {"url": LINKEDIN, "text": "a blog post"})
    assert (status, body["error"]) == (400, NO_JOB)
