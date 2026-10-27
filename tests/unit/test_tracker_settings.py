import json
from contextlib import closing
from http import HTTPStatus
from pathlib import Path
from typing import Any

import pytest

from satyaapply.core.paths import Paths
from satyaapply.core.profile import load, save
from satyaapply.store.db import connect
from satyaapply.tracker import settings
from satyaapply.tracker.body import Body
from satyaapply.tracker.routes import Route
from satyaapply.tracker.settings_fields import MAX_ITEMS
from tests.unit import samples

VALID: dict[str, object] = {
    "name": "Asha Rao",
    "email": "asha.rao@example.com",
    "phone": "+91 90000 00000",
    "city": "Bengaluru",
    "country": "India",
    "links": ["https://github.com/asharao"],
    "currentCompany": "Acme Analytics",
    "yearsExperience": 2.5,
    "roles": ["Frontend Engineer"],
    "titleKeywords": ["frontend", "react"],
    "titleExclude": ["senior"],
    "skipCompanies": ["Acme Analytics"],
    "relocateCities": [],
    "maxJobAgeDays": 30,
    "wellfound": True,
    "wellfoundRoles": [],
    "wellfoundTitles": [],
    "wellfoundSkip": [],
    "minScore": 60,
    "onsiteCity": True,
    "remoteCountry": True,
    "relocate": False,
    "remoteAbroad": False,
    "currency": "INR",
    "expectedMin": 1_200_000,
    "expectedMax": 1_800_000,
    "currentSalary": 800_000,
    "noticePeriod": "30 days",
    "citizenship": "India",
    "workWithoutVisa": ["India"],
    "needsSponsorship": True,
    "dateOfBirth": "",
    "gender": "",
    "disability": "",
    "veteran": "",
    "ethnicity": "",
    "extraFacts": "",
    "unknownQuestions": "skip",
    "coverLetter": "required",
    "jobsPerRun": 5,
    "scoresPerRun": 40,
    "dailyCap": 20,
    "linkedinCap": 10,
    "aiCallsPerDay": 300,
    "runEveryMinutes": 180,
    "summaryHour": 20,
}


@pytest.fixture
def paths(tmp_path: Path) -> Paths:
    paths = Paths(tmp_path / "home")
    paths.ensure()
    resume = tmp_path / "master.tex"
    resume.write_text("resume", encoding="utf-8")
    save(paths, samples.profile(resume))
    return paths


def call(routes: tuple[Route, ...], paths: Paths, body: Body) -> tuple[HTTPStatus, Any]:
    match = routes[0].pattern.match("/api/settings")
    assert match is not None
    with closing(connect(paths.database)) as db:
        response = routes[0].handler(db, paths, match, body)
    return response.status, json.loads(response.body)


def test_current_values_and_fixed_facts_are_shown(paths: Paths) -> None:
    status, view = call(settings.GET, paths, {})
    assert status == HTTPStatus.OK
    assert view["values"] == VALID
    assert view["limits"]["maxItems"] == MAX_ITEMS
    assert view["limits"]["numbers"]["jobsPerRun"] == {"min": 1, "max": 50}


def test_saving_persists_trimmed_values(paths: Paths) -> None:
    keywords = [" python ", "", "Go", "python ", " go ", "full   stack"]
    body = VALID | {"titleKeywords": keywords, "minScore": 70, "dailyCap": None}
    body = body | {"onsiteCity": False, "remoteAbroad": True}
    status, view = call(settings.POST, paths, body)
    assert status == HTTPStatus.OK
    assert view["values"]["titleKeywords"] == ["python", "Go", "full stack"]
    saved = load(paths)
    assert saved.title_keywords == ("python", "Go", "full stack")
    assert saved.settings.min_score == 70
    assert saved.daily_cap is None
    assert not saved.work_places.onsite_city
    assert saved.work_places.remote_abroad


@pytest.mark.parametrize(
    "change",
    [
        {"minScore": 150},
        {"minScore": "60"},
        {"minScore": -1},
        {"minScore": 60.5},
        {"minScore": None},
        {"expectedMin": 2_000_000},
        {"dailyCap": 0},
        {"skipCompanies": [f"c{n}" for n in range(51)]},
        {"skipCompanies": "Acme"},
        {"titleExclude": ["x" * 201]},
        {"noticePeriod": "x" * 201},
        {"onsiteCity": "yes"},
        {"name": " "},
        {"yearsExperience": -1},
        {"yearsExperience": "2"},
        {"dateOfBirth": "31/12/1999"},
        {"unknownQuestions": "maybe"},
        {"coverLetter": None},
        {"jobsPerRun": 51},
        {"scoresPerRun": 0},
        {"runEveryMinutes": 14},
        {"summaryHour": 24},
        {"aiCallsPerDay": 0},
        {"extraFacts": "x" * 4001},
    ],
)
def test_invalid_input_is_refused(paths: Paths, change: dict[str, object]) -> None:
    before = load(paths)
    status, answer = call(settings.POST, paths, VALID | change)
    assert status == HTTPStatus.BAD_REQUEST
    assert answer["error"] == settings.NOT_SAVED
    assert answer["problems"]
    assert load(paths) == before


def test_every_hidden_setting_can_be_changed(paths: Paths) -> None:
    body = VALID | {
        "name": "Asha  R",
        "yearsExperience": 3.5,
        "roles": ["Frontend Engineer", "Full Stack Engineer"],
        "currency": "usd",
        "currentSalary": None,
        "dateOfBirth": "1999-12-31",
        "gender": "Woman",
        "extraFacts": " Led a team of 3. ",
        "unknownQuestions": "guess",
        "coverLetter": "never",
        "jobsPerRun": 12,
        "scoresPerRun": 80,
        "linkedinCap": 4,
        "aiCallsPerDay": 500,
        "runEveryMinutes": 360,
        "summaryHour": 9,
        "needsSponsorship": False,
    }
    status, _ = call(settings.POST, paths, body)
    assert status == HTTPStatus.OK
    saved = load(paths)
    assert saved.name == "Asha R"
    assert saved.years_experience == 3.5
    assert saved.roles == ("Frontend Engineer", "Full Stack Engineer")
    assert saved.salary.currency == "USD"
    assert saved.salary.current is None
    assert saved.dob is not None and saved.dob.isoformat() == "1999-12-31"
    assert saved.diversity is not None and saved.diversity.gender == "Woman"
    assert saved.extra_facts == "Led a team of 3."
    assert saved.unknown_questions == "guess"
    assert saved.cover_letter == "never"
    assert not saved.needs_sponsorship_elsewhere
    chosen = saved.settings
    assert (chosen.jobs_per_run, chosen.scores_per_run, chosen.linkedin_cap) == (12, 80, 4)
    assert (chosen.ai_calls_per_day, chosen.run_every_minutes, chosen.summary_hour) == (500, 360, 9)


def test_empty_diversity_means_not_shared(paths: Paths) -> None:
    call(settings.POST, paths, VALID | {"gender": "Woman"})
    call(settings.POST, paths, VALID)
    assert load(paths).diversity is None


def test_every_problem_is_named_at_once(paths: Paths) -> None:
    _, answer = call(settings.POST, paths, VALID | {"minScore": 150, "dailyCap": 0})
    assert len(answer["problems"]) == 2
    assert any(item.startswith("Minimum match score") for item in answer["problems"])


def test_missing_profile_asks_for_setup(tmp_path: Path) -> None:
    paths = Paths(tmp_path / "empty")
    for routes in (settings.GET, settings.POST):
        status, answer = call(routes, paths, VALID)
        assert status == HTTPStatus.CONFLICT
        assert "satyaapply setup" in answer["error"]
    assert not paths.profile.exists()
