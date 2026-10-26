import re
import sqlite3
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from http import HTTPStatus

from satyaapply.core.errors import ProfileInvalidError, ProfileMissingError
from satyaapply.core.paths import Paths
from satyaapply.core.profile import Profile, load, save
from satyaapply.core.profile import problems as profile_problems
from satyaapply.store.records import JobRecord
from satyaapply.tracker.html import e, joined, page, section
from satyaapply.tracker.responses import Response, back_to, html
from satyaapply.tracker.routes import Form, route

SETTINGS = "/settings"
TITLE = "Settings"
MAX_ITEMS = 50
MAX_TEXT = 200
MAX_JOB_AGE_DAYS = 365
MAX_DAILY_CAP = 500
MAX_SALARY = 100_000_000_000
NUMBER = re.compile(r"[0-9]{1,12}")
LISTS = {
    "title_keywords": "Title keywords",
    "title_exclude": "Titles to skip",
    "skip_companies": "Companies to skip",
    "relocate_cities": "Cities you'd move to",
}
PLACES = ("onsite_city", "remote_country", "relocate", "remote_abroad")
TEXTS = (
    *LISTS,
    "max_job_age_days",
    "min_score",
    "expected_min",
    "expected_max",
    "notice_period",
    "daily_cap",
)
NOTICE_LABEL = "Notice period"
MISSING = f"<h1>{TITLE}</h1><p>Run <code>satyaapply setup</code> first.</p>"

Values = Mapping[str, str]


@dataclass(frozen=True)
class Number:
    name: str
    label: str
    low: int
    high: int


@dataclass(frozen=True)
class View:
    profile: Profile
    values: Values
    problems: Sequence[str] = ()
    saved: bool = False


JOB_AGE = Number("max_job_age_days", "Oldest job to consider, in days", 1, MAX_JOB_AGE_DAYS)
SALARY_MIN = Number("expected_min", "Expected salary, lowest", 1, MAX_SALARY)
SALARY_MAX = Number("expected_max", "Expected salary, highest", 1, MAX_SALARY)
DAILY_CAP = Number("daily_cap", "Applications per day", 1, MAX_DAILY_CAP)


def _min_score(profile: Profile) -> Number:
    return Number("min_score", "Minimum match score", 0, profile.settings.strong_score)


def _on(flag: bool) -> str:
    return "on" if flag else ""


def _joined(items: Sequence[str]) -> str:
    return ", ".join(items)


def _values(profile: Profile) -> dict[str, str]:
    places = profile.work_places
    return {
        "title_keywords": _joined(profile.title_keywords),
        "title_exclude": _joined(profile.title_exclude),
        "skip_companies": _joined(profile.skip_companies),
        "relocate_cities": _joined(places.relocate_cities),
        "max_job_age_days": str(profile.settings.max_job_age_days),
        "min_score": str(profile.settings.min_score),
        "expected_min": str(profile.salary.expected_min),
        "expected_max": str(profile.salary.expected_max),
        "notice_period": profile.notice_period,
        "daily_cap": "" if profile.daily_cap is None else str(profile.daily_cap),
        "onsite_city": _on(places.onsite_city),
        "remote_country": _on(places.remote_country),
        "relocate": _on(places.relocate),
        "remote_abroad": _on(places.remote_abroad),
    }


def _submitted(form: Form) -> dict[str, str]:
    typed = {name: form.get(name, "") for name in TEXTS}
    return typed | {name: _on(name in form) for name in PLACES}


def _items(form: Form, name: str, found: list[str]) -> tuple[str, ...]:
    kept: dict[str, str] = {}
    for part in form.get(name, "").split(","):
        text = " ".join(part.split())
        if text:
            kept.setdefault(text.casefold(), text)
    items = tuple(kept.values())
    if len(items) > MAX_ITEMS or any(len(item) > MAX_TEXT for item in items):
        found.append(f"{LISTS[name]}: up to {MAX_ITEMS} entries, each up to {MAX_TEXT} characters.")
    return items


def _number(form: Form, spec: Number, found: list[str]) -> int:
    raw = form.get(spec.name, "").replace(",", "").strip()
    if NUMBER.fullmatch(raw) and spec.low <= int(raw) <= spec.high:
        return int(raw)
    found.append(f"{spec.label}: enter a whole number from {spec.low:,} to {spec.high:,}.")
    return spec.low


def _daily_cap(form: Form, found: list[str]) -> int | None:
    return _number(form, DAILY_CAP, found) if form.get("daily_cap", "").strip() else None


def _notice(form: Form, found: list[str]) -> str:
    text = " ".join(form.get("notice_period", "").split())
    if len(text) > MAX_TEXT:
        found.append(f"{NOTICE_LABEL}: up to {MAX_TEXT} characters.")
    return text


def _salary_order(low: int, high: int, found: list[str]) -> None:
    if low > high:
        found.append("Expected salary: the lowest can't be more than the highest.")


def _updated(profile: Profile, form: Form) -> tuple[Profile, list[str]]:
    found: list[str] = []
    places = replace(
        profile.work_places,
        onsite_city="onsite_city" in form,
        remote_country="remote_country" in form,
        relocate="relocate" in form,
        remote_abroad="remote_abroad" in form,
        relocate_cities=_items(form, "relocate_cities", found),
    )
    low, high = _number(form, SALARY_MIN, found), _number(form, SALARY_MAX, found)
    _salary_order(low, high, found)
    settings = replace(
        profile.settings,
        min_score=_number(form, _min_score(profile), found),
        max_job_age_days=_number(form, JOB_AGE, found),
    )
    updated = replace(
        profile,
        title_keywords=_items(form, "title_keywords", found),
        title_exclude=_items(form, "title_exclude", found),
        skip_companies=_items(form, "skip_companies", found),
        work_places=places,
        salary=replace(profile.salary, expected_min=low, expected_max=high),
        settings=settings,
        notice_period=_notice(form, found),
        daily_cap=_daily_cap(form, found),
    )
    return updated, found or profile_problems(updated)


def _hint(text: str) -> str:
    return f'<p class="muted">{e(text)}</p>'


def _input(view: View, name: str, label: str) -> str:
    value = e(view.values.get(name, ""))
    return f'<label>{e(label)}<input type="text" name="{name}" value="{value}"></label>'


def _list_input(view: View, name: str) -> str:
    return _input(view, name, f"{LISTS[name]} (comma-separated)")


def _checkbox(view: View, name: str, label: str) -> str:
    checked = " checked" if view.values.get(name) else ""
    box = f'<input type="checkbox" name="{name}" value="on"{checked}>'
    return f'<p><label class="inline">{box} {e(label)}</label></p>'


def _search(view: View) -> str:
    score = _min_score(view.profile)
    fields = (
        _list_input(view, "title_keywords"),
        _list_input(view, "title_exclude"),
        _list_input(view, "skip_companies"),
        _input(view, JOB_AGE.name, JOB_AGE.label),
        _input(view, score.name, f"{score.label} ({score.low} to {score.high})"),
    )
    hint = "Which jobs to look for. Jobs scoring below the minimum match score are skipped."
    return section("Job search", _hint(hint) + joined(fields))


def _places(view: View) -> str:
    city, country = view.profile.city, view.profile.country
    fields = (
        _checkbox(view, "onsite_city", f"On-site or hybrid in {city}"),
        _checkbox(view, "remote_country", f"Remote in {country}"),
        _checkbox(view, "relocate", f"Moving to another city in {country}"),
        _checkbox(view, "remote_abroad", "Remote for companies abroad"),
        _list_input(view, "relocate_cities"),
    )
    hint = "Tick every kind of place you're happy to work. Jobs anywhere else are skipped."
    return section("Where you'll work", _hint(hint) + joined(fields))


def _pay(view: View) -> str:
    currency = view.profile.salary.currency
    fields = (
        _input(view, SALARY_MIN.name, f"{SALARY_MIN.label} ({currency})"),
        _input(view, SALARY_MAX.name, f"{SALARY_MAX.label} ({currency})"),
        _input(view, "notice_period", NOTICE_LABEL),
    )
    hint = (
        "Used to answer pay and notice questions on forms. "
        f"The currency ({currency}) is set in setup."
    )
    return section("Pay and notice", _hint(hint) + joined(fields))


def _limit(view: View) -> str:
    linkedin = view.profile.settings.linkedin_cap
    hint = (
        "The most applications to prepare in a day. Leave it empty for no limit. "
        f"LinkedIn stays at {linkedin} a day whatever you put here."
    )
    return section("Daily limit", _hint(hint) + _input(view, DAILY_CAP.name, DAILY_CAP.label))


def _banner(view: View) -> str:
    if view.problems:
        items = joined(f"<li>{e(problem)}</li>" for problem in view.problems)
        lead = "<p>Nothing was saved. Fix these:</p>"
        return f'<div class="card" role="alert">{lead}<ul>{items}</ul></div>'
    return '<p class="card" role="status">Saved.</p>' if view.saved else ""


def _form_page(view: View) -> str:
    parts = (
        f"<h1>{TITLE}</h1>",
        _banner(view),
        f'<form method="post" action="{SETTINGS}">',
        _search(view),
        _places(view),
        _pay(view),
        _limit(view),
        '<div class="button-row"><button>Save settings</button></div></form>',
    )
    return page(TITLE, joined(parts), "/settings")


def _broken(error: ProfileInvalidError) -> str:
    items = joined(f"<li>{e(problem)}</li>" for problem in error.problems)
    return (
        f"<h1>{TITLE}</h1><p>Your profile has problems:</p><ul>{items}</ul><p>{e(error.hint)}</p>"
    )


def _loaded(paths: Paths) -> Profile | Response:
    try:
        return load(paths)
    except ProfileMissingError:
        return html(page(TITLE, MISSING, "/settings"))
    except ProfileInvalidError as error:
        return html(page(TITLE, _broken(error), "/settings"))


def _show(_db: sqlite3.Connection, paths: Paths, _match: re.Match[str], form: Form) -> Response:
    profile = _loaded(paths)
    if isinstance(profile, Response):
        return profile
    return html(_form_page(View(profile, _values(profile), saved=form.get("saved") == "1")))


def _save(_db: sqlite3.Connection, paths: Paths, _match: re.Match[str], form: Form) -> Response:
    profile = _loaded(paths)
    if isinstance(profile, Response):
        return profile
    updated, found = _updated(profile, form)
    if found:
        view = View(profile, _submitted(form), found)
        return html(_form_page(view), HTTPStatus.BAD_REQUEST)
    save(paths, updated)
    return back_to(f"{SETTINGS}?saved=1")


def home_panel(_db: sqlite3.Connection, _paths: Paths) -> str:
    return ""


def job_controls(_db: sqlite3.Connection, _record: JobRecord) -> str:
    return ""


GET = (route(SETTINGS, _show),)
POST = (route(SETTINGS, _save),)
