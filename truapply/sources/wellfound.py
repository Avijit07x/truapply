import html
import json
import re
import sqlite3
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from http import HTTPStatus

from truapply.browser.fetch import fetch_pages
from truapply.core.models import Job, Source, Status, normalize
from truapply.core.notes import DOESNT_FIT_NOTE, WELLFOUND_NOTE
from truapply.core.profile import Profile
from truapply.sources.filters import ListingFit, worth_listing
from truapply.sources.skills import skills_in
from truapply.store import jobs, meta
from truapply.store.jobs import StatusChange

SITE = "https://wellfound.com"
IN_PLACE = SITE + "/role/l/{role}/{place}"
REMOTE = SITE + "/role/r/{role}"
PAGE = "{search}?page={page}"
JOB_PAGE = SITE + "/jobs/{id}-{slug}"
MAX_PAGES = 5
PAGES_AT_ONCE = 2
WAIT_KEY = "wellfound_wait_until"
COOL_DOWN = timedelta(hours=1)
NEXT_DATA = re.compile(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', re.S)
ASIDE = re.compile(r"\(.*?\)")
LISTING = "JobListingSearchResult"
COMPANY = "StartupResult"
DEVELOPER, ENGINEER = "developer", "engineer"

State = dict[str, dict[str, object]]


@dataclass(frozen=True)
class Listing:
    job: Job
    min_years: int | None


@dataclass(frozen=True)
class Checked:
    listed: int
    waiting_until: datetime | None = None


def _slug(text: str) -> str:
    return normalize(ASIDE.sub(" ", text)).replace(" ", "-")


def role_slugs(profile: Profile) -> list[str]:
    found: dict[str, None] = {}
    for role in profile.settings.wellfound_roles or profile.roles:
        slug = _slug(role)
        if slug:
            found[slug] = None
            found[slug.replace(DEVELOPER, ENGINEER)] = None
    return list(found)


def searches(profile: Profile) -> list[str]:
    place = _slug(profile.country)
    found = []
    for role in role_slugs(profile):
        if place:
            found.append(IN_PLACE.format(role=role, place=place))
        if profile.work_places.remote_abroad:
            found.append(REMOTE.format(role=role))
    return found


def _state(page: str) -> State:
    found = NEXT_DATA.search(page)
    if not found:
        return {}
    try:
        data = json.loads(found.group(1))
    except json.JSONDecodeError:
        return {}
    for key in ("props", "pageProps", "apolloState", "data"):
        data = data.get(key) if isinstance(data, dict) else None
    return data if isinstance(data, dict) else {}


def _texts(value: object) -> list[str]:
    return [item for item in value if isinstance(item, str)] if isinstance(value, list) else []


def _companies(state: State) -> dict[str, str]:
    names = {}
    for item in state.values():
        if item.get("__typename") != COMPANY:
            continue
        refs = item.get("highlightedJobListings")
        for ref in refs if isinstance(refs, list) else []:
            if isinstance(ref, dict) and isinstance(ref.get("__ref"), str):
                names[ref["__ref"]] = str(item.get("name") or "")
    return names


def _place(item: dict[str, object]) -> str:
    places = ", ".join(_texts(item.get("locationNames")))
    if item.get("remote") is not True:
        return places
    accepted = ", ".join(_texts(item.get("acceptedRemoteLocationNames")))
    remote = f"Remote ({accepted})" if accepted else "Remote"
    return f"{remote}, {places}" if places else remote


def _posted(value: object) -> datetime | None:
    return datetime.fromtimestamp(value, UTC) if isinstance(value, int) else None


def _job(item: dict[str, object], company: str) -> Job | None:
    job_id, title = str(item.get("id") or ""), str(item.get("title") or "")
    if not job_id.isdigit() or not title or not company:
        return None
    return Job(
        source=Source.WELLFOUND,
        external_id=job_id,
        url=JOB_PAGE.format(id=job_id, slug=item.get("slug") or "job"),
        company=company,
        title=html.unescape(title),
        location=_place(item),
        description=html.unescape(str(item.get("description") or "")),
        posted_at=_posted(item.get("liveStartAt")),
        status=Status.READY,
    )


def listings(page: str) -> Iterator[Listing]:
    state = _state(page)
    companies = _companies(state)
    for key, item in state.items():
        if item.get("__typename") == LISTING:
            job = _job(item, companies.get(key, ""))
            years = item.get("yearsExperienceMin")
            if job:
                yield Listing(job, years if isinstance(years, int) else None)


def _read(urls: list[str], found: dict[str, Listing]) -> tuple[set[str], bool]:
    answered, slowed = set(), False
    for response in fetch_pages(urls, PAGES_AT_ONCE):
        slowed = slowed or response.status == HTTPStatus.TOO_MANY_REQUESTS
        listed = list(listings(response.data)) if isinstance(response.data, str) else []
        if listed:
            answered.add(response.url)
        found.update((item.job.key, item) for item in listed)
    return answered, slowed


def _waiting(db: sqlite3.Connection, now: datetime) -> datetime | None:
    saved = meta.get(db, WAIT_KEY)
    until = datetime.fromisoformat(saved) if saved else None
    return until if until and until > now else None


def _pages(profile: Profile, found: dict[str, Listing]) -> bool:
    first = {PAGE.format(search=search, page=1): search for search in searches(profile)}
    answered, slowed = _read(list(first), found)
    if slowed:
        return True
    later = range(2, MAX_PAGES + 1)
    urls = [PAGE.format(search=first[url], page=page) for url in answered for page in later]
    return _read(urls, found)[1]


def _fit(profile: Profile, known: frozenset[str], item: Listing) -> ListingFit:
    chosen = profile.settings
    return ListingFit(known, item.min_years, chosen.wellfound_titles, chosen.wellfound_skip)


def check(db: sqlite3.Connection, profile: Profile, resume: str, now: datetime) -> Checked:
    waiting = _waiting(db, now)
    if waiting:
        return Checked(0, waiting)
    found: dict[str, Listing] = {}
    slowed = _pages(profile, found)
    if slowed:
        meta.put(db, WAIT_KEY, (now + COOL_DOWN).isoformat())
    known = skills_in([resume, *profile.title_keywords, *profile.roles])
    wanted = {
        key: item.job
        for key, item in found.items()
        if worth_listing(item.job, profile, now, _fit(profile, known, item))
    }
    skip = StatusChange(Status.SKIPPED, now, DOESNT_FIT_NOTE)
    jobs.unlist(db, (key for key in found if key not in wanted), WELLFOUND_NOTE, skip)
    listed = jobs.add_ready(db, wanted.values(), now, WELLFOUND_NOTE)
    return Checked(listed, now + COOL_DOWN if slowed else None)
