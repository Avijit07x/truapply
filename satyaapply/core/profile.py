import json
from dataclasses import dataclass, field
from datetime import date
from enum import StrEnum
from pathlib import Path

from satyaapply.core.codec import decode, encode
from satyaapply.core.documents import ResumeFormat
from satyaapply.core.errors import DecodeError, ProfileInvalidError, ProfileMissingError
from satyaapply.core.files import write_private
from satyaapply.core.models import Source
from satyaapply.core.paths import Paths

PROFILE_VERSION = 1
MAX_SCORE = 100
LAST_HOUR = 23


class SubmitMode(StrEnum):
    TRUST = "trust"
    REVIEW_ONLY = "review_only"


class UnknownQuestions(StrEnum):
    SKIP = "skip"
    GUESS = "guess"


class CoverLetter(StrEnum):
    REQUIRED = "required"
    ALWAYS = "always"
    NEVER = "never"


@dataclass(frozen=True)
class ResumeRef:
    format: ResumeFormat
    path: Path


@dataclass(frozen=True)
class WorkPlaces:
    onsite_city: bool
    remote_country: bool
    relocate: bool
    relocate_cities: tuple[str, ...]
    remote_abroad: bool


@dataclass(frozen=True)
class Salary:
    currency: str
    expected_min: int
    expected_max: int
    current: int | None


@dataclass(frozen=True)
class Diversity:
    gender: str
    disability: str
    veteran: str
    ethnicity: str


@dataclass(frozen=True)
class Settings:
    min_score: int = 60
    strong_score: int = 80
    trust_after: int = 20
    linkedin_cap: int = 10
    run_every_hours: int = 3
    summary_hour: int = 20
    ai_calls_per_day: int = 300
    ghosted_after_days: int = 21
    max_job_age_days: int = 30


@dataclass(frozen=True)
class Profile:
    name: str
    email: str
    phone: str
    city: str
    country: str
    links: tuple[str, ...]
    current_company: str
    years_experience: float
    resume: ResumeRef
    roles: tuple[str, ...]
    title_keywords: tuple[str, ...]
    title_exclude: tuple[str, ...]
    work_places: WorkPlaces
    sites: tuple[Source, ...]
    submit_mode: SubmitMode
    unknown_questions: UnknownQuestions
    daily_cap: int | None
    cover_letter: CoverLetter
    skip_companies: tuple[str, ...]
    notice_period: str
    citizenship: str
    work_without_visa: tuple[str, ...]
    needs_sponsorship_elsewhere: bool
    salary: Salary
    dob: date | None
    diversity: Diversity | None
    extra_facts: str
    auto_submit: bool = False
    settings: Settings = field(default_factory=Settings)
    version: int = PROFILE_VERSION


def _settings_problems(settings: Settings) -> list[str]:
    problems = []
    if not 0 <= settings.min_score <= settings.strong_score <= MAX_SCORE:
        problems.append("settings: need 0 <= min_score <= strong_score <= 100")
    if settings.trust_after < 1:
        problems.append("settings.trust_after must be at least 1")
    if settings.linkedin_cap < 0:
        problems.append("settings.linkedin_cap can't be negative")
    if not 0 <= settings.summary_hour <= LAST_HOUR:
        problems.append("settings.summary_hour must be 0-23")
    if settings.run_every_hours < 1 or settings.ai_calls_per_day < 1:
        problems.append("settings.run_every_hours and ai_calls_per_day must be at least 1")
    return problems


def problems(profile: Profile) -> list[str]:
    found = _settings_problems(profile.settings)
    if "@" not in profile.email:
        found.append("email doesn't look like an email address")
    if not profile.roles:
        found.append("roles: add at least one target job title")
    if not profile.sites:
        found.append("sites: pick at least one job site")
    if not 0 < profile.salary.expected_min <= profile.salary.expected_max:
        found.append("salary: need 0 < expected_min <= expected_max")
    if profile.daily_cap is not None and profile.daily_cap < 1:
        found.append("daily_cap must be at least 1, or null for no limit")
    if not profile.resume.path.is_file():
        found.append(f"resume.path: {profile.resume.path} doesn't exist")
    if profile.version != PROFILE_VERSION:
        found.append(f"version {profile.version} isn't supported (expected {PROFILE_VERSION})")
    return found


def load(paths: Paths) -> Profile:
    if not paths.profile.is_file():
        raise ProfileMissingError("No profile yet.")
    try:
        raw = json.loads(paths.profile.read_text(encoding="utf-8"))
        profile = decode(Profile, raw)
    except json.JSONDecodeError as error:
        problem = f"not valid JSON (line {error.lineno})"
        raise ProfileInvalidError(paths.profile, [problem]) from None
    except DecodeError as error:
        raise ProfileInvalidError(paths.profile, [str(error)]) from None
    found = problems(profile)
    if found:
        raise ProfileInvalidError(paths.profile, found)
    return profile


def save(paths: Paths, profile: Profile) -> None:
    found = problems(profile)
    if found:
        raise ProfileInvalidError(paths.profile, found)
    write_private(paths.profile, json.dumps(encode(profile), indent=2, ensure_ascii=False) + "\n")
