import json
from dataclasses import dataclass, field
from datetime import date
from enum import StrEnum
from pathlib import Path

from truapply.core.codec import decode, encode
from truapply.core.documents import ResumeFormat
from truapply.core.errors import DecodeError, ProfileInvalidError, ProfileMissingError
from truapply.core.files import write_private
from truapply.core.paths import Paths

PROFILE_VERSION = 1
RETIRED_KEYS = frozenset({"submit_mode", "auto_submit", "sites"})
RETIRED_SETTINGS = frozenset(
    {
        "strong_score",
        "trust_after",
        "ghosted_after_days",
        "linkedin_reading",
        "linkedin_reads_per_day",
    }
)
MAX_SCORE = 100
MIN_AUTO_SUBMIT_SCORE = 0
LAST_HOUR = 23
MAX_JOBS_PER_RUN = 50
MAX_SCORES_PER_RUN = 200
MIN_EVERY_MINUTES = 15
MAX_EVERY_MINUTES = 1440
MINUTES_PER_HOUR = 60


class UnknownQuestions(StrEnum):
    SKIP = "skip"
    GUESS = "guess"


class CompanySearch(StrEnum):
    OFF = "off"
    DAILY = "daily"
    WEEKLY = "weekly"


CURRENCIES = {
    "india": "INR",
    "united states": "USD",
    "usa": "USD",
    "united kingdom": "GBP",
    "uk": "GBP",
    "canada": "CAD",
    "australia": "AUD",
    "singapore": "SGD",
    "germany": "EUR",
    "france": "EUR",
    "netherlands": "EUR",
    "ireland": "EUR",
    "united arab emirates": "AED",
}
NOTICE_PERIODS = ("Immediate", "15 days", "30 days", "60 days", "90 days")


def currency_for(country: str) -> str:
    return CURRENCIES.get(country.strip().lower(), "USD")


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
    linkedin_cap: int = 10
    run_every_minutes: int = 180
    summary_hour: int = 20
    ai_calls_per_day: int = 300
    max_job_age_days: int = 30
    company_search: CompanySearch = CompanySearch.WEEKLY
    tailor_resume: bool = True
    auto_submit: bool = False
    auto_submit_score: int = 80
    wellfound: bool = True
    wellfound_roles: tuple[str, ...] = ()
    wellfound_titles: tuple[str, ...] = ()
    wellfound_skip: tuple[str, ...] = ()
    jobs_per_run: int = 5
    scores_per_run: int = 40


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
    settings: Settings = field(default_factory=Settings)
    version: int = PROFILE_VERSION


def _settings_problems(settings: Settings) -> list[str]:
    problems = []
    if not 0 <= settings.min_score <= MAX_SCORE:
        problems.append("settings.min_score must be 0-100")
    if not MIN_AUTO_SUBMIT_SCORE <= settings.auto_submit_score <= MAX_SCORE:
        problems.append("settings.auto_submit_score must be 0-100")
    if not 1 <= settings.jobs_per_run <= MAX_JOBS_PER_RUN:
        problems.append(f"settings.jobs_per_run must be 1-{MAX_JOBS_PER_RUN}")
    if not 1 <= settings.scores_per_run <= MAX_SCORES_PER_RUN:
        problems.append(f"settings.scores_per_run must be 1-{MAX_SCORES_PER_RUN}")
    if settings.linkedin_cap < 0:
        problems.append("settings.linkedin_cap can't be negative")
    if not 0 <= settings.summary_hour <= LAST_HOUR:
        problems.append("settings.summary_hour must be 0-23")
    if not MIN_EVERY_MINUTES <= settings.run_every_minutes <= MAX_EVERY_MINUTES:
        problems.append(
            f"settings.run_every_minutes must be {MIN_EVERY_MINUTES}-{MAX_EVERY_MINUTES}"
        )
    if settings.ai_calls_per_day < 1:
        problems.append("settings.ai_calls_per_day must be at least 1")
    return problems


def problems(profile: Profile) -> list[str]:
    found = _settings_problems(profile.settings)
    if "@" not in profile.email:
        found.append("email doesn't look like an email address")
    if not profile.roles:
        found.append("roles: add at least one target job title")
    if not 0 < profile.salary.expected_min <= profile.salary.expected_max:
        found.append("salary: need 0 < expected_min <= expected_max")
    if profile.daily_cap is not None and profile.daily_cap < 1:
        found.append("daily_cap must be at least 1, or null for no limit")
    if not profile.resume.path.is_file():
        found.append(f"resume.path: {profile.resume.path} doesn't exist")
    if profile.version != PROFILE_VERSION:
        found.append(f"version {profile.version} isn't supported (expected {PROFILE_VERSION})")
    return found


def _current(raw: object) -> object:
    if not isinstance(raw, dict):
        return raw
    kept = {key: value for key, value in raw.items() if key not in RETIRED_KEYS}
    settings = kept.get("settings")
    if isinstance(settings, dict):
        hours = settings.pop("run_every_hours", None)
        if isinstance(hours, int) and "run_every_minutes" not in settings:
            settings["run_every_minutes"] = hours * MINUTES_PER_HOUR
        kept["settings"] = {k: v for k, v in settings.items() if k not in RETIRED_SETTINGS}
    return kept


def load(paths: Paths) -> Profile:
    if not paths.profile.is_file():
        raise ProfileMissingError("No profile yet.")
    try:
        raw = _current(json.loads(paths.profile.read_text(encoding="utf-8")))
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
