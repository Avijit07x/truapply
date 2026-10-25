import re
from datetime import datetime

from satyaapply.core.models import Job, normalize, normalize_company
from satyaapply.core.profile import Profile

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
CITY_ALIASES = {
    "bengaluru": ("bangalore",),
    "bangalore": ("bengaluru",),
    "gurugram": ("gurgaon",),
    "gurgaon": ("gurugram",),
    "mumbai": ("bombay",),
    "chennai": ("madras",),
    "thiruvananthapuram": ("trivandrum",),
}


def mentions(phrase: str, text: str) -> bool:
    wanted = normalize(phrase)
    return bool(wanted) and f" {wanted} " in f" {normalize(text)} "


def title_fits(title: str, profile: Profile) -> bool:
    if any(mentions(word, title) for word in profile.title_exclude):
        return False
    keywords = [keyword for keyword in profile.title_keywords if normalize(keyword)]
    return not keywords or any(mentions(keyword, title) for keyword in keywords)


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
    if REMOTE.search(place):
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


def worth_scoring(job: Job, profile: Profile, now: datetime) -> bool:
    return (
        title_fits(job.title, profile)
        and location_fits(job.location, profile)
        and is_fresh(job, now, profile.settings.max_job_age_days)
        and not company_skipped(job, profile)
    )
