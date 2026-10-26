import re
import sqlite3
from dataclasses import dataclass, replace
from http import HTTPStatus

from satyaapply.core.errors import ProfileInvalidError, ProfileMissingError
from satyaapply.core.paths import Paths
from satyaapply.core.profile import Profile, load, save
from satyaapply.core.profile import problems as profile_problems
from satyaapply.tracker.body import Body, flag, number, strings, text
from satyaapply.tracker.responses import Response, bad_request, ok, problem
from satyaapply.tracker.routes import Route, route

MAX_ITEMS = 50
MAX_TEXT = 200
MAX_JOB_AGE_DAYS = 365
MAX_DAILY_CAP = 500
MAX_SALARY = 100_000_000_000
LISTS = {
    "titleKeywords": "Title keywords",
    "titleExclude": "Titles to skip",
    "skipCompanies": "Companies to skip",
    "relocateCities": "Cities you'd move to",
}
PLACES = ("onsiteCity", "remoteCountry", "relocate", "remoteAbroad")
NOTICE_LABEL = "Notice period"
MISSING = "Run `satyaapply setup` first."
NOT_SAVED = "Nothing was saved. Fix these first."


@dataclass(frozen=True)
class Number:
    name: str
    label: str
    low: int
    high: int


JOB_AGE = Number("maxJobAgeDays", "Oldest job to consider, in days", 1, MAX_JOB_AGE_DAYS)
SALARY_MIN = Number("expectedMin", "Expected salary, lowest", 1, MAX_SALARY)
SALARY_MAX = Number("expectedMax", "Expected salary, highest", 1, MAX_SALARY)
DAILY_CAP = Number("dailyCap", "Applications per day", 1, MAX_DAILY_CAP)


def _min_score(profile: Profile) -> Number:
    return Number("minScore", "Minimum match score", 0, profile.settings.strong_score)


def _values(profile: Profile) -> dict[str, object]:
    places = profile.work_places
    return {
        "titleKeywords": list(profile.title_keywords),
        "titleExclude": list(profile.title_exclude),
        "skipCompanies": list(profile.skip_companies),
        "relocateCities": list(places.relocate_cities),
        "maxJobAgeDays": profile.settings.max_job_age_days,
        "minScore": profile.settings.min_score,
        "expectedMin": profile.salary.expected_min,
        "expectedMax": profile.salary.expected_max,
        "noticePeriod": profile.notice_period,
        "dailyCap": profile.daily_cap,
        "onsiteCity": places.onsite_city,
        "remoteCountry": places.remote_country,
        "relocate": places.relocate,
        "remoteAbroad": places.remote_abroad,
    }


def _view(profile: Profile) -> dict[str, object]:
    fixed = {
        "city": profile.city,
        "country": profile.country,
        "currency": profile.salary.currency,
        "strongScore": profile.settings.strong_score,
        "linkedinCap": profile.settings.linkedin_cap,
        "maxItems": MAX_ITEMS,
        "maxText": MAX_TEXT,
        "maxJobAgeDays": MAX_JOB_AGE_DAYS,
        "maxDailyCap": MAX_DAILY_CAP,
    }
    return {"values": _values(profile), "fixed": fixed}


def _items(body: Body, name: str, found: list[str]) -> tuple[str, ...]:
    given = strings(body, name)
    if given is None:
        found.append(f"{LISTS[name]}: send a list of words.")
        return ()
    kept: dict[str, str] = {}
    for part in given:
        words = " ".join(part.split())
        if words:
            kept.setdefault(words.casefold(), words)
    items = tuple(kept.values())
    if len(items) > MAX_ITEMS or any(len(item) > MAX_TEXT for item in items):
        found.append(f"{LISTS[name]}: up to {MAX_ITEMS} entries, each up to {MAX_TEXT} characters.")
    return items


def _number(body: Body, spec: Number, found: list[str]) -> int:
    value = number(body, spec.name)
    if value is not None and spec.low <= value <= spec.high:
        return value
    found.append(f"{spec.label}: enter a whole number from {spec.low:,} to {spec.high:,}.")
    return spec.low


def _daily_cap(body: Body, found: list[str]) -> int | None:
    return None if body.get(DAILY_CAP.name) is None else _number(body, DAILY_CAP, found)


def _notice(body: Body, found: list[str]) -> str:
    words = " ".join(text(body, "noticePeriod", MAX_TEXT + 1).split())
    if len(words) > MAX_TEXT:
        found.append(f"{NOTICE_LABEL}: up to {MAX_TEXT} characters.")
    return words


def _places(body: Body, found: list[str]) -> dict[str, bool]:
    chosen = {name: flag(body, name) for name in PLACES}
    if any(value is None for value in chosen.values()):
        found.append("Where you'll work: tick or untick each kind of place.")
    return {name: bool(value) for name, value in chosen.items()}


def _salary_order(low: int, high: int, found: list[str]) -> None:
    if low > high:
        found.append("Expected salary: the lowest can't be more than the highest.")


def updated(profile: Profile, body: Body) -> tuple[Profile, list[str]]:
    found: list[str] = []
    chosen = _places(body, found)
    places = replace(
        profile.work_places,
        onsite_city=chosen["onsiteCity"],
        remote_country=chosen["remoteCountry"],
        relocate=chosen["relocate"],
        remote_abroad=chosen["remoteAbroad"],
        relocate_cities=_items(body, "relocateCities", found),
    )
    low, high = _number(body, SALARY_MIN, found), _number(body, SALARY_MAX, found)
    _salary_order(low, high, found)
    settings = replace(
        profile.settings,
        min_score=_number(body, _min_score(profile), found),
        max_job_age_days=_number(body, JOB_AGE, found),
    )
    changed = replace(
        profile,
        title_keywords=_items(body, "titleKeywords", found),
        title_exclude=_items(body, "titleExclude", found),
        skip_companies=_items(body, "skipCompanies", found),
        work_places=places,
        salary=replace(profile.salary, expected_min=low, expected_max=high),
        settings=settings,
        notice_period=_notice(body, found),
        daily_cap=_daily_cap(body, found),
    )
    return changed, found or profile_problems(changed)


def _loaded(paths: Paths) -> Profile | Response:
    try:
        return load(paths)
    except ProfileMissingError:
        return problem(HTTPStatus.CONFLICT, MISSING)
    except ProfileInvalidError as error:
        return problem(HTTPStatus.CONFLICT, error.hint or str(error), error.problems)


def _show(_db: sqlite3.Connection, paths: Paths, _match: re.Match[str], _body: Body) -> Response:
    profile = _loaded(paths)
    return profile if isinstance(profile, Response) else ok(_view(profile))


def _save(_db: sqlite3.Connection, paths: Paths, _match: re.Match[str], body: Body) -> Response:
    profile = _loaded(paths)
    if isinstance(profile, Response):
        return profile
    changed, found = updated(profile, body)
    if found:
        return bad_request(NOT_SAVED, found)
    save(paths, changed)
    return ok(_view(changed))


GET: tuple[Route, ...] = (route("/settings", _show),)
POST: tuple[Route, ...] = (route("/settings", _save),)
