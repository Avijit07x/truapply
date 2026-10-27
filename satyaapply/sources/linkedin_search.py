from urllib.parse import urlencode

from satyaapply.core.profile import Profile

SEARCH = "https://www.linkedin.com/jobs/search/"
PAST_DAY = "r86400"
REMOTE = "2"
NEWEST = "DD"
ANYWHERE = "Worldwide"
MOST_ROLES = 6


def _url(role: str, place: str, remote: bool) -> str:
    query = {
        "keywords": role,
        "location": place,
        "f_TPR": PAST_DAY,
        "f_AL": "true",
        "sortBy": NEWEST,
    }
    if remote:
        query["f_WT"] = REMOTE
    return f"{SEARCH}?{urlencode(query)}"


def search_urls(profile: Profile) -> list[str]:
    places = profile.work_places
    wanted: list[tuple[str, bool]] = []
    if places.onsite_city or places.remote_country or places.relocate:
        wanted.append((profile.country, False))
    if places.remote_abroad:
        wanted.append((ANYWHERE, True))
    return [
        _url(role, place, remote) for role in profile.roles[:MOST_ROLES] for place, remote in wanted
    ]
