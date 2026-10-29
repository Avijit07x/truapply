import json
import re
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from http import HTTPStatus
from pathlib import Path

from truapply.ai import tasks
from truapply.ai.replies import ProfileDraft
from truapply.core.clock import utc_now
from truapply.core.codec import decode, encode
from truapply.core.errors import TruApplyError
from truapply.core.files import write_private
from truapply.core.paths import Paths
from truapply.core.profile import (
    NOTICE_PERIODS,
    CoverLetter,
    Profile,
    ResumeRef,
    Salary,
    UnknownQuestions,
    WorkPlaces,
    currency_for,
    save,
)
from truapply.core.profile import problems as profile_problems
from truapply.sources.discover import shared_boards
from truapply.store import boards
from truapply.store.boards import BoardOrigin
from truapply.tracker import automatic, resume_upload
from truapply.tracker.body import Body
from truapply.tracker.extension import install_info
from truapply.tracker.responses import Response, bad_request, ok, problem
from truapply.tracker.routes import Route, route
from truapply.tracker.settings import EVERY_MINUTES, JOBS_PER_RUN, SALARY_MAX, SALARY_MIN
from truapply.tracker.settings_fields import Reader

DONE = "You're already set up. Change anything in Settings."
NO_RESUME = "Add your resume first."
NOT_SAVED = "Setup isn't finished yet. Fix these first."
NO_SCHEDULE = "You're set up, but automatic runs didn't start. Turn them on in Settings."
DAILY_CAP = 20
WHERE = "Where you'll work"


def _draft_file(paths: Paths) -> Path:
    return paths.root / "setup.json"


def needed(paths: Paths) -> bool:
    return not paths.profile.is_file()


def _saved(paths: Paths) -> tuple[ProfileDraft, ResumeRef, int] | None:
    try:
        raw = json.loads(_draft_file(paths).read_text(encoding="utf-8"))
        return (
            decode(ProfileDraft, raw["draft"]),
            decode(ResumeRef, raw["resume"]),
            int(raw["pages"]),
        )
    except (OSError, ValueError, KeyError, TypeError, TruApplyError):
        return None


def _draft_view(draft: ProfileDraft, pages: int) -> dict[str, object]:
    return {
        "name": draft.name,
        "email": draft.email,
        "phone": draft.phone,
        "city": draft.city,
        "country": draft.country,
        "roles": list(draft.suggested_roles),
        "titleKeywords": list(draft.title_keywords),
        "currency": currency_for(draft.country),
        "pages": pages,
    }


def _view(paths: Paths) -> dict[str, object]:
    saved = _saved(paths) if needed(paths) else None
    return {
        "needed": needed(paths),
        "draft": _draft_view(saved[0], saved[2]) if saved else None,
        "noticePeriods": list(NOTICE_PERIODS),
        "automatic": automatic.current(paths),
        "extension": install_info(),
    }


def _read_resume(paths: Paths, suffix: str, data: bytes) -> None:
    paths.ensure()
    with resume_upload.opened(paths, suffix, data) as document, ThreadPoolExecutor(2) as pool:
        draft = pool.submit(tasks.draft_profile, document)
        resume = pool.submit(resume_upload.as_resume, document)
        found, stored = draft.result(), resume.result()
    ref, pages = resume_upload.kept(paths, stored)
    record = {"draft": encode(found), "resume": encode(ref), "pages": pages}
    write_private(_draft_file(paths), json.dumps(record, ensure_ascii=False))


def _start(draft: ProfileDraft, resume: ResumeRef) -> Profile:
    current = draft.current_company
    return Profile(
        name=draft.name,
        email=draft.email,
        phone=draft.phone,
        city=draft.city,
        country=draft.country,
        links=draft.links,
        current_company=current,
        years_experience=draft.years_experience,
        resume=resume,
        roles=draft.suggested_roles,
        title_keywords=draft.title_keywords,
        title_exclude=draft.title_exclude,
        work_places=WorkPlaces(True, True, False, (), False),
        unknown_questions=UnknownQuestions.SKIP,
        daily_cap=DAILY_CAP,
        cover_letter=CoverLetter.REQUIRED,
        skip_companies=(current,) if current else (),
        notice_period="",
        citizenship="",
        work_without_visa=(),
        needs_sponsorship_elsewhere=True,
        salary=Salary(currency_for(draft.country), 1, 1, None),
        dob=None,
        diversity=None,
        extra_facts="",
    )


def _answered(read: Reader, start: Profile) -> Profile:
    places = WorkPlaces(
        onsite_city=read.flag("onsiteCity", WHERE),
        remote_country=read.flag("remoteCountry", WHERE),
        relocate=read.flag("relocate", WHERE),
        relocate_cities=(),
        remote_abroad=read.flag("remoteAbroad", WHERE),
    )
    if not any((places.onsite_city, places.remote_country, places.relocate, places.remote_abroad)):
        read.problems.append("Where you'll work: pick at least one.")
    low, high = read.number(SALARY_MIN), read.number(SALARY_MAX)
    if low > high:
        read.problems.append("Expected salary: the lowest can't be more than the highest.")
    sponsorship = read.body.get("needsSponsorship")
    if not isinstance(sponsorship, bool):
        read.problems.append("Visa sponsorship: answer yes or no.")
    settings = replace(
        start.settings,
        tailor_resume=read.flag("tailorResume", "Your resume"),
        jobs_per_run=read.number(JOBS_PER_RUN),
        run_every_minutes=read.optional_number(EVERY_MINUTES) or start.settings.run_every_minutes,
    )
    keywords = read.items("titleKeywords", "Title words")
    if not keywords:
        read.problems.append("Title words: add at least one.")
    visa_free = read.items("workWithoutVisa", "Countries you can work in without a visa")
    if not visa_free:
        read.problems.append("Countries you can work in without a visa: add at least one.")
    return replace(
        start,
        name=read.text("name", "Name", required=True),
        email=read.text("email", "Email", required=True),
        phone=read.text("phone", "Phone"),
        city=read.text("city", "City", required=True),
        country=read.text("country", "Country", required=True),
        roles=read.items("roles", "Job titles"),
        title_keywords=keywords,
        work_places=places,
        citizenship=read.text("citizenship", "Citizenship", required=True),
        work_without_visa=visa_free,
        needs_sponsorship_elsewhere=sponsorship is True,
        notice_period=read.text("noticePeriod", "Notice period", required=True),
        salary=Salary(read.text("currency", "Currency", required=True).upper(), low, high, None),
        settings=settings,
    )


def _get(_db: sqlite3.Connection, paths: Paths, _match: re.Match[str], _body: Body) -> Response:
    return ok(_view(paths))


def _resume(_db: sqlite3.Connection, paths: Paths, _match: re.Match[str], body: Body) -> Response:
    if not needed(paths):
        return problem(HTTPStatus.CONFLICT, DONE)
    given = resume_upload.uploaded(body)
    if isinstance(given, str):
        return bad_request(given)
    try:
        _read_resume(paths, *given)
    except TruApplyError as error:
        return bad_request(" ".join(part for part in (str(error), error.hint) if part))
    return ok(_view(paths))


def _finish(db: sqlite3.Connection, paths: Paths, _match: re.Match[str], body: Body) -> Response:
    if not needed(paths):
        return problem(HTTPStatus.CONFLICT, DONE)
    saved = _saved(paths)
    if saved is None:
        return bad_request(NO_RESUME)
    read = Reader(body)
    profile = _answered(read, _start(saved[0], saved[1]))
    found = read.problems or profile_problems(profile)
    if found:
        return bad_request(NOT_SAVED, found)
    save(paths, profile)
    boards.add_many(db, shared_boards(), BoardOrigin.SHARED, utc_now())
    _draft_file(paths).unlink(missing_ok=True)
    if body.get(EVERY_MINUTES.name) is not None:
        try:
            automatic.turn_on(paths, profile.settings.run_every_minutes)
        except TruApplyError as error:
            return ok(_view(paths) | {"warning": f"{NO_SCHEDULE} {error}"})
    return ok(_view(paths))


GET: tuple[Route, ...] = (route(r"/setup", _get),)
POST: tuple[Route, ...] = (
    route(resume_upload.SETUP_PATH, _resume),
    route(r"/setup", _finish),
)
