import re
import sqlite3
from dataclasses import replace
from http import HTTPStatus

from satyaapply.core.clock import utc_now
from satyaapply.core.errors import ProfileInvalidError, ProfileMissingError, SatyaApplyError
from satyaapply.core.paths import Paths
from satyaapply.core.profile import (
    LAST_HOUR,
    MAX_EVERY_MINUTES,
    MAX_JOBS_PER_RUN,
    MAX_SCORE,
    MAX_SCORES_PER_RUN,
    MIN_AUTO_SUBMIT_SCORE,
    MIN_EVERY_MINUTES,
    CompanySearch,
    CoverLetter,
    Diversity,
    Profile,
    Settings,
    UnknownQuestions,
    load,
    save,
)
from satyaapply.core.profile import problems as profile_problems
from satyaapply.store import autosend
from satyaapply.tracker import automatic
from satyaapply.tracker.body import Body
from satyaapply.tracker.extension import install_info
from satyaapply.tracker.responses import Response, bad_request, ok, problem
from satyaapply.tracker.routes import Route, route
from satyaapply.tracker.settings_fields import (
    MAX_ITEMS,
    MAX_LONG_TEXT,
    MAX_TEXT,
    Number,
    Reader,
)

MAX_JOB_AGE_DAYS = 365
MAX_DAILY_CAP = 500
MAX_AI_CALLS = 5000
MAX_YEARS = 60
MAX_SALARY = 100_000_000_000
MISSING = "Run `satyaapply setup` first."
NOT_SAVED = "Nothing was saved. Fix these first."
UNKNOWN_LABEL = "Questions it can't answer"

JOB_AGE = Number("maxJobAgeDays", "Oldest job to consider, in days", 1, MAX_JOB_AGE_DAYS)
MIN_SCORE = Number("minScore", "Minimum match score", 0, MAX_SCORE)
AUTO_SCORE = Number("autoSubmitScore", "Auto-submit from score", MIN_AUTO_SUBMIT_SCORE, MAX_SCORE)
SALARY_MIN = Number("expectedMin", "Expected salary, lowest", 1, MAX_SALARY)
SALARY_MAX = Number("expectedMax", "Expected salary, highest", 1, MAX_SALARY)
SALARY_NOW = Number("currentSalary", "Current salary", 0, MAX_SALARY)
YEARS = Number("yearsExperience", "Years of experience", 0, MAX_YEARS)
DAILY_CAP = Number("dailyCap", "Applications per day", 1, MAX_DAILY_CAP)
LINKEDIN_CAP = Number("linkedinCap", "LinkedIn applications per day", 0, MAX_DAILY_CAP)
JOBS_PER_RUN = Number("jobsPerRun", "Jobs to tailor each run", 1, MAX_JOBS_PER_RUN)
SCORES_PER_RUN = Number("scoresPerRun", "Jobs to score each run", 1, MAX_SCORES_PER_RUN)
AI_CALLS = Number("aiCallsPerDay", "Claude calls per day", 1, MAX_AI_CALLS)
EVERY_MINUTES = Number(
    "runEveryMinutes", "Minutes between automatic runs", MIN_EVERY_MINUTES, MAX_EVERY_MINUTES
)
SUMMARY_HOUR = Number("summaryHour", "Daily summary hour", 0, LAST_HOUR)
LIMITED = (
    JOB_AGE,
    MIN_SCORE,
    AUTO_SCORE,
    DAILY_CAP,
    LINKEDIN_CAP,
    JOBS_PER_RUN,
    SCORES_PER_RUN,
    AI_CALLS,
    EVERY_MINUTES,
    SUMMARY_HOUR,
    YEARS,
)
DIVERSITY = ("gender", "disability", "veteran", "ethnicity")


def _diversity(profile: Profile) -> dict[str, str]:
    given = profile.diversity
    return {name: getattr(given, name) if given else "" for name in DIVERSITY}


def _values(profile: Profile) -> dict[str, object]:
    places, salary, chosen = profile.work_places, profile.salary, profile.settings
    return {
        "name": profile.name,
        "email": profile.email,
        "phone": profile.phone,
        "city": profile.city,
        "country": profile.country,
        "links": list(profile.links),
        "currentCompany": profile.current_company,
        "yearsExperience": profile.years_experience,
        "roles": list(profile.roles),
        "titleKeywords": list(profile.title_keywords),
        "titleExclude": list(profile.title_exclude),
        "skipCompanies": list(profile.skip_companies),
        "relocateCities": list(places.relocate_cities),
        "maxJobAgeDays": chosen.max_job_age_days,
        "wellfound": chosen.wellfound,
        "wellfoundRoles": list(chosen.wellfound_roles),
        "wellfoundTitles": list(chosen.wellfound_titles),
        "wellfoundSkip": list(chosen.wellfound_skip),
        "minScore": chosen.min_score,
        "onsiteCity": places.onsite_city,
        "remoteCountry": places.remote_country,
        "relocate": places.relocate,
        "remoteAbroad": places.remote_abroad,
        "currency": salary.currency,
        "expectedMin": salary.expected_min,
        "expectedMax": salary.expected_max,
        "currentSalary": salary.current,
        "noticePeriod": profile.notice_period,
        "citizenship": profile.citizenship,
        "workWithoutVisa": list(profile.work_without_visa),
        "needsSponsorship": profile.needs_sponsorship_elsewhere,
        "dateOfBirth": profile.dob.isoformat() if profile.dob else "",
        **_diversity(profile),
        "extraFacts": profile.extra_facts,
        "unknownQuestions": profile.unknown_questions.value,
        "coverLetter": profile.cover_letter.value,
        "companySearch": chosen.company_search.value,
        "autoSubmit": chosen.auto_submit,
        "autoSubmitScore": chosen.auto_submit_score,
        "jobsPerRun": chosen.jobs_per_run,
        "scoresPerRun": chosen.scores_per_run,
        "dailyCap": profile.daily_cap,
        "linkedinCap": chosen.linkedin_cap,
        "aiCallsPerDay": chosen.ai_calls_per_day,
        "runEveryMinutes": chosen.run_every_minutes,
        "summaryHour": chosen.summary_hour,
    }


def _limits() -> dict[str, object]:
    return {
        "maxItems": MAX_ITEMS,
        "maxText": MAX_TEXT,
        "maxLongText": MAX_LONG_TEXT,
        "numbers": {spec.name: {"min": spec.low, "max": spec.high} for spec in LIMITED},
    }


def _settings(profile: Profile, read: Reader) -> Settings:
    return replace(
        profile.settings,
        min_score=read.number(MIN_SCORE),
        max_job_age_days=read.number(JOB_AGE),
        company_search=read.choice(
            "companySearch", "Find new companies", CompanySearch, profile.settings.company_search
        ),
        auto_submit=read.flag("autoSubmit", "Auto-submit"),
        auto_submit_score=read.number(AUTO_SCORE),
        wellfound=read.flag("wellfound", "Check Wellfound"),
        wellfound_roles=read.items("wellfoundRoles", "Wellfound roles to read"),
        wellfound_titles=read.items("wellfoundTitles", "Wellfound titles to pull"),
        wellfound_skip=read.items("wellfoundSkip", "Wellfound titles to skip"),
        jobs_per_run=read.number(JOBS_PER_RUN),
        scores_per_run=read.number(SCORES_PER_RUN),
        linkedin_cap=read.number(LINKEDIN_CAP),
        ai_calls_per_day=read.number(AI_CALLS),
        run_every_minutes=read.number(EVERY_MINUTES),
        summary_hour=read.number(SUMMARY_HOUR),
    )


def _diversity_given(read: Reader) -> Diversity | None:
    given = {name: read.text(name, name.capitalize()) for name in DIVERSITY}
    return Diversity(**given) if any(given.values()) else None


def _about(profile: Profile, read: Reader) -> Profile:
    return replace(
        profile,
        name=read.text("name", "Name", required=True),
        email=read.text("email", "Email", required=True),
        phone=read.text("phone", "Phone"),
        city=read.text("city", "City", required=True),
        country=read.text("country", "Country", required=True),
        links=read.items("links", "Links"),
        current_company=read.text("currentCompany", "Current company"),
        years_experience=read.decimal(YEARS),
        citizenship=read.text("citizenship", "Citizenship"),
        work_without_visa=read.items("workWithoutVisa", "Countries you can work in without a visa"),
        needs_sponsorship_elsewhere=read.flag("needsSponsorship", "Needs visa sponsorship"),
        dob=read.day("dateOfBirth", "Date of birth"),
        diversity=_diversity_given(read),
        extra_facts=read.long_text("extraFacts", "Other true facts"),
    )


def _search(profile: Profile, read: Reader) -> Profile:
    places = replace(
        profile.work_places,
        onsite_city=read.flag("onsiteCity", "On-site in your city"),
        remote_country=read.flag("remoteCountry", "Remote in your country"),
        relocate=read.flag("relocate", "Moving cities"),
        remote_abroad=read.flag("remoteAbroad", "Remote abroad"),
        relocate_cities=read.items("relocateCities", "Cities you'd move to"),
    )
    return replace(
        profile,
        roles=read.items("roles", "Roles you want"),
        title_keywords=read.items("titleKeywords", "Title keywords"),
        title_exclude=read.items("titleExclude", "Titles to skip"),
        skip_companies=read.items("skipCompanies", "Companies to skip"),
        work_places=places,
    )


def _pay_and_answers(profile: Profile, read: Reader) -> Profile:
    low, high = read.number(SALARY_MIN), read.number(SALARY_MAX)
    if low > high:
        read.problems.append("Expected salary: the lowest can't be more than the highest.")
    salary = replace(
        profile.salary,
        currency=read.text("currency", "Currency", required=True).upper(),
        expected_min=low,
        expected_max=high,
        current=read.optional_number(SALARY_NOW),
    )
    return replace(
        profile,
        salary=salary,
        notice_period=read.text("noticePeriod", "Notice period"),
        unknown_questions=read.choice(
            "unknownQuestions",
            "Questions it can't answer",
            UnknownQuestions,
            profile.unknown_questions,
        ),
        cover_letter=read.choice("coverLetter", "Cover letters", CoverLetter, profile.cover_letter),
        daily_cap=read.optional_number(DAILY_CAP),
    )


def updated(profile: Profile, body: Body) -> tuple[Profile, list[str]]:
    read = Reader(body)
    changed = _pay_and_answers(_search(_about(profile, read), read), read)
    changed = replace(changed, settings=_settings(profile, read))
    return changed, read.problems or profile_problems(changed)


def _loaded(paths: Paths) -> Profile | Response:
    try:
        return load(paths)
    except ProfileMissingError:
        return problem(HTTPStatus.CONFLICT, MISSING)
    except ProfileInvalidError as error:
        return problem(HTTPStatus.CONFLICT, error.hint or str(error), error.problems)


def _shown(profile: Profile) -> Response:
    return ok(
        {
            "values": _values(profile),
            "limits": _limits(),
            "automatic": automatic.current(),
            "resume": {"format": profile.resume.format.value},
            "extension": install_info(),
        }
    )


def _show(_db: sqlite3.Connection, paths: Paths, _match: re.Match[str], _body: Body) -> Response:
    profile = _loaded(paths)
    return profile if isinstance(profile, Response) else _shown(profile)


def _save(db: sqlite3.Connection, paths: Paths, _match: re.Match[str], body: Body) -> Response:
    profile = _loaded(paths)
    if isinstance(profile, Response):
        return profile
    changed, found = updated(profile, body)
    if found:
        return bad_request(NOT_SAVED, found)
    save(paths, changed)
    if changed.settings.auto_submit and not profile.settings.auto_submit:
        autosend.turned_on(db, utc_now())
    try:
        automatic.follow(paths, changed.settings.run_every_minutes)
    except SatyaApplyError as error:
        return bad_request(f"Saved, but automatic runs didn't update: {error}")
    return _shown(changed)


GET: tuple[Route, ...] = (route("/settings", _show),)
POST: tuple[Route, ...] = (route("/settings", _save),)
