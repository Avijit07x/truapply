import re
from dataclasses import dataclass
from datetime import datetime

from satyaapply.core.models import Job, normalize, normalize_company
from satyaapply.core.notes import (
    SKIPPED_COMPANY_NOTE,
    TOO_OLD_NOTE,
    WRONG_PLACE_NOTE,
    WRONG_TITLE_NOTE,
)
from satyaapply.core.profile import Profile
from satyaapply.sources.skills import skills_fit, skills_in

REMOTE = re.compile(r"\b(remote|anywhere|distributed|work from home|wfh)\b", re.IGNORECASE)
COUNTRY_PLACES = {
    "india": (
        "bengaluru",
        "bangalore",
        "hyderabad",
        "pune",
        "mumbai",
        "delhi",
        "new delhi",
        "gurugram",
        "gurgaon",
        "noida",
        "chennai",
        "kolkata",
        "ahmedabad",
        "jaipur",
        "kochi",
        "chandigarh",
        "indore",
        "coimbatore",
        "thiruvananthapuram",
        "trivandrum",
        "mysuru",
        "mysore",
    ),
    "united states": ("us", "usa", "u s", "u s a", "america"),
    "united kingdom": ("uk", "u k", "england", "britain"),
}
REGIONS = {"india": ("apac", "asia", "asia pacific", "south asia")}
ANYWHERE_WORDS = frozenset(
    {
        "worldwide",
        "global",
        "anywhere",
        "international",
        "first",
        "only",
        "fully",
        "100",
        "friendly",
    }
)
PARTS = re.compile(r"[/;|]")
MOST_JOINED = 3
ROLE_WORDS = frozenset({"engineer", "developer", "programmer"})
COMMON_WORDS = frozenset({"software", "design", "ui", "web", "product", "application"})
EXPERIENCE_STRETCH = 1
GENERAL_TITLES = (
    "software engineer",
    "software developer",
    "software development engineer",
    "sde",
    "web developer",
    "web engineer",
    "product engineer",
    "application developer",
    "application engineer",
    "member of technical staff",
    "programmer",
)
CITY_ALIASES = {
    "bengaluru": ("bangalore",),
    "bangalore": ("bengaluru",),
    "gurugram": ("gurgaon",),
    "gurgaon": ("gurugram",),
    "mumbai": ("bombay",),
    "chennai": ("madras",),
    "thiruvananthapuram": ("trivandrum",),
}


@dataclass(frozen=True)
class ListingFit:
    known: frozenset[str]
    min_years: int | None
    titles: tuple[str, ...] = ()
    skip: tuple[str, ...] = ()


def mentions(phrase: str, text: str) -> bool:
    wanted = normalize(phrase)
    return bool(wanted) and f" {wanted} " in f" {normalize(text)} "


def says(phrase: str, text: str) -> bool:
    wanted = normalize(phrase).replace(" ", "")
    words = normalize(text).split()
    longest = max(MOST_JOINED, len(normalize(phrase).split()) + 1)
    return bool(wanted) and any(
        "".join(words[start : start + size]) == wanted
        for size in range(1, longest + 1)
        for start in range(len(words))
    )


def _excluded(title: str, profile: Profile) -> bool:
    return any(says(word, title) for word in profile.title_exclude)


def title_fits(title: str, profile: Profile) -> bool:
    if _excluded(title, profile):
        return False
    keywords = [keyword for keyword in profile.title_keywords if normalize(keyword)]
    return not keywords or any(says(keyword, title) for keyword in keywords)


def _stack_terms(profile: Profile) -> list[str]:
    terms = []
    for keyword in profile.title_keywords:
        words = [word for word in normalize(keyword).split() if word not in ROLE_WORDS]
        term = " ".join(words)
        if term and term not in COMMON_WORDS:
            terms.append(term)
    return terms


def role_fits(job: Job, profile: Profile) -> bool:
    if title_fits(job.title, profile):
        return True
    if _excluded(job.title, profile) or not any(says(t, job.title) for t in GENERAL_TITLES):
        return False
    return any(says(term, job.description) for term in _stack_terms(profile))


def in_your_field(job: Job, profile: Profile) -> bool:
    phrases = (*profile.title_keywords, *profile.roles, *GENERAL_TITLES)
    return any(says(phrase, job.title) for phrase in phrases if normalize(phrase))


def _city_names(city: str) -> tuple[str, ...]:
    return (city, *CITY_ALIASES.get(normalize(city), ()))


def _in_country(location: str, profile: Profile) -> bool:
    places = (profile.country, *COUNTRY_PLACES.get(normalize(profile.country), ()))
    return any(mentions(place, location) for place in places)


def _relocation_fits(location: str, profile: Profile) -> bool:
    places = profile.work_places
    if not places.relocate:
        return False
    if not places.relocate_cities:
        return True
    return any(
        mentions(name, location) for city in places.relocate_cities for name in _city_names(city)
    )


def _is_anywhere(location: str) -> bool:
    rest = normalize(REMOTE.sub(" ", location)).split()
    return all(word in ANYWHERE_WORDS for word in rest)


def _in_home_region(location: str, profile: Profile) -> bool:
    return any(mentions(region, location) for region in REGIONS.get(normalize(profile.country), ()))


def _place_fits(place: str, profile: Profile) -> bool:
    places = profile.work_places
    home_city = any(mentions(name, place) for name in _city_names(profile.city))
    in_country = home_city or _in_country(place, profile)
    if REMOTE.search(place) or _is_anywhere(place):
        if in_country or _in_home_region(place, profile):
            return places.remote_country
        return _is_anywhere(place) and (places.remote_country or places.remote_abroad)
    if home_city:
        return places.onsite_city
    return in_country and _relocation_fits(place, profile)


def location_fits(location: str, profile: Profile) -> bool:
    places = [place for place in PARTS.split(location) if place.strip()]
    return not places or any(_place_fits(place, profile) for place in places)


def is_fresh(job: Job, now: datetime, max_age_days: int) -> bool:
    return job.posted_at is None or (now - job.posted_at).days <= max_age_days


def company_skipped(job: Job, profile: Profile) -> bool:
    skipped = {normalize_company(name) for name in profile.skip_companies}
    return normalize_company(job.company) in skipped


def _place_and_time_fit(job: Job, profile: Profile, now: datetime) -> bool:
    return (
        location_fits(job.location, profile)
        and is_fresh(job, now, profile.settings.max_job_age_days)
        and not company_skipped(job, profile)
    )


def why_skipped(job: Job, profile: Profile, now: datetime) -> str | None:
    if not role_fits(job, profile):
        return WRONG_TITLE_NOTE
    if not location_fits(job.location, profile):
        return WRONG_PLACE_NOTE
    if not is_fresh(job, now, profile.settings.max_job_age_days):
        return TOO_OLD_NOTE
    if company_skipped(job, profile):
        return SKIPPED_COMPANY_NOTE
    return None


def worth_scoring(job: Job, profile: Profile, now: datetime) -> bool:
    return why_skipped(job, profile, now) is None


def _title_listed(job: Job, profile: Profile, fit: ListingFit) -> bool:
    if any(says(word, job.title) for word in (*fit.skip, *profile.title_exclude)):
        return False
    if fit.titles:
        return any(says(title, job.title) for title in fit.titles)
    return role_fits(job, profile)


def worth_listing(job: Job, profile: Profile, now: datetime, fit: ListingFit) -> bool:
    asked = skills_in([job.title, job.description])
    stretch = profile.years_experience + EXPERIENCE_STRETCH
    experienced = fit.min_years is None or fit.min_years <= stretch
    skilled = bool(asked) and skills_fit(asked, fit.known)
    listed = _title_listed(job, profile, fit) and _place_and_time_fit(job, profile, now)
    return listed and experienced and skilled
