import base64
from collections.abc import Iterator
from pathlib import Path

import pytest

from tests.unit.tracker_api import get, post, running
from truapply.ai import tasks
from truapply.ai.replies import ProfileDraft
from truapply.core import autorun
from truapply.core.documents import ResumeFormat
from truapply.core.paths import Paths
from truapply.core.profile import ResumeRef, load
from truapply.resume.contract import Resume
from truapply.sources.discover import shared_boards
from truapply.tracker import automatic, resume_upload
from truapply.tracker.server import TrackerServer

DRAFT = ProfileDraft(
    name="Asha Rao",
    email="asha@example.com",
    phone="+91 90000 00000",
    city="Bengaluru",
    country="India",
    links=("https://github.com/asharao",),
    current_company="Acme Analytics",
    current_title="Frontend Engineer",
    years_experience=3,
    skills=("React",),
    suggested_roles=("Frontend Engineer",),
    title_keywords=("frontend", "react"),
    title_exclude=("senior",),
)
ANSWERS: dict[str, object] = {
    "name": "Asha Rao",
    "email": "asha@example.com",
    "phone": "+91 90000 00000",
    "city": "Bengaluru",
    "country": "India",
    "roles": ["Frontend Engineer"],
    "titleKeywords": ["frontend", "react"],
    "onsiteCity": True,
    "remoteCountry": True,
    "relocate": False,
    "remoteAbroad": False,
    "citizenship": "India",
    "workWithoutVisa": ["India"],
    "needsSponsorship": True,
    "noticePeriod": "30 days",
    "currency": "inr",
    "expectedMin": 1_200_000,
    "expectedMax": 1_800_000,
    "tailorResume": False,
    "jobsPerRun": 8,
    "runEveryMinutes": None,
}


@pytest.fixture
def tracker(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[TrackerServer]:
    def keep(paths: Paths, _resume: Resume) -> tuple[ResumeRef, int]:
        master = paths.resume_dir / "master.json"
        master.write_text("{}", encoding="utf-8")
        return ResumeRef(ResumeFormat.STRUCTURED, master), 1

    monkeypatch.setattr(tasks, "draft_profile", lambda _document: DRAFT)
    monkeypatch.setattr(resume_upload, "as_resume", lambda _document: None)
    monkeypatch.setattr(resume_upload, "kept", keep)
    monkeypatch.setattr(automatic, "agents", lambda: tmp_path / "agents")
    monkeypatch.setattr(automatic, "runner", lambda _arguments: 0)
    monkeypatch.setattr(automatic, "supported", lambda: True)
    with running(Paths(tmp_path / "fresh")) as server:
        yield server


def uploaded(name: str = "resume.pdf") -> dict[str, object]:
    return {"name": name, "data": base64.b64encode(b"%PDF-1.4 resume").decode()}


def test_a_fresh_folder_asks_for_setup_and_cannot_run(tracker: TrackerServer) -> None:
    assert get(tracker, "/api/summary")[1]["setupNeeded"] is True
    assert get(tracker, "/api/setup")[1]["draft"] is None
    code, answer = post(tracker, "/api/runs/start", {"limit": 3, "search": True})
    assert (code, answer["error"]) == (400, "Finish setup first.")


def test_the_resume_fills_in_the_details_to_check(tracker: TrackerServer) -> None:
    code, view = post(tracker, "/api/setup/resume", uploaded())
    assert code == 200
    assert view["draft"]["name"] == "Asha Rao"
    assert view["draft"]["roles"] == ["Frontend Engineer"]
    assert view["draft"]["currency"] == "INR"
    assert get(tracker, "/api/setup")[1]["draft"] == view["draft"]
    assert not (tracker.paths.resume_dir / "upload.pdf").exists()


def test_a_wrong_file_is_refused_before_claude_reads_it(tracker: TrackerServer) -> None:
    code, answer = post(tracker, "/api/setup/resume", uploaded("photo.png"))
    assert code == 400
    assert "Pick a resume file" in answer["error"]


def test_finishing_needs_the_resume_first(tracker: TrackerServer) -> None:
    code, answer = post(tracker, "/api/setup", ANSWERS)
    assert (code, answer["error"]) == (400, "Add your resume first.")


def test_work_rights_are_never_filled_in_for_you(tracker: TrackerServer) -> None:
    post(tracker, "/api/setup/resume", uploaded())
    unanswered = ANSWERS | {"citizenship": "", "workWithoutVisa": [], "needsSponsorship": None}
    code, answer = post(tracker, "/api/setup", unanswered)
    assert code == 400
    assert any(line.startswith("Citizenship") for line in answer["problems"])
    assert any(line.startswith("Countries you can work in") for line in answer["problems"])
    assert any(line.startswith("Visa sponsorship") for line in answer["problems"])
    assert not tracker.paths.profile.exists()


def test_finishing_saves_the_profile_and_opens_the_app(tracker: TrackerServer) -> None:
    post(tracker, "/api/setup/resume", uploaded())
    code, view = post(tracker, "/api/setup", ANSWERS)
    assert (code, view["needed"]) == (200, False)
    profile = load(tracker.paths)
    assert (profile.salary.currency, profile.salary.expected_min) == ("INR", 1_200_000)
    assert profile.skip_companies == ("Acme Analytics",)
    assert profile.title_exclude == ("senior",)
    assert (profile.settings.tailor_resume, profile.settings.jobs_per_run) == (False, 8)
    assert autorun.installed(automatic.agents()) is None
    assert len(get(tracker, "/api/companies")[1]["companies"]) == len(shared_boards())
    assert get(tracker, "/api/summary")[1]["setupNeeded"] is False
    assert post(tracker, "/api/setup", ANSWERS)[0] == 409
    assert post(tracker, "/api/setup/resume", uploaded())[0] == 409


def test_pages_that_need_a_profile_answer_before_setup_instead_of_dropping(
    tracker: TrackerServer,
) -> None:
    code, answer = get(tracker, "/api/companies")
    assert (code, answer["error"]) == (409, "Finish setup first.")


def test_picking_a_schedule_turns_automatic_runs_on_for_this_folder(
    tracker: TrackerServer,
) -> None:
    post(tracker, "/api/setup/resume", uploaded())
    code, view = post(tracker, "/api/setup", ANSWERS | {"runEveryMinutes": 60})
    assert code == 200
    assert view["automatic"]["on"] is True
    assert load(tracker.paths).settings.run_every_minutes == 60
