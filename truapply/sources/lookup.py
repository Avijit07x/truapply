import re
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from urllib.parse import urlsplit

from truapply.core.models import Ats, Board, normalize
from truapply.core.profile import Profile
from truapply.sources.ats import poll
from truapply.sources.filters import in_country

WEBSITE = re.compile(r"(?:https?://)?(?:[\w-]+\.)+[a-z]{2,}(?:/\S*)?", re.IGNORECASE)
LOOSE_WORDS = frozenset(
    {"ai", "hq", "inc", "india", "labs", "limited", "ltd", "private", "pvt", "technologies"}
)


@dataclass(frozen=True)
class Lookup:
    found: list[Board]
    missing: list[str]


def _company(entry: str) -> tuple[str, list[str]]:
    if WEBSITE.fullmatch(entry):
        host = urlsplit(entry if "//" in entry else f"//{entry}").hostname or ""
        stem = host.removeprefix("www.").split(".")[0]
        return stem.title(), [stem]
    return entry, normalize(entry).split()


def slugs(entry: str) -> list[str]:
    _name, words = _company(entry)
    core = [word for word in words if word not in LOOSE_WORDS] or words
    tries = ("".join(words), "-".join(words), "".join(core), "-".join(core))
    return list(dict.fromkeys(slug for slug in tries if slug))


def entries_in(text: str) -> list[str]:
    parts = (part.strip() for part in re.split(r"[\n,;]", text))
    return list(dict.fromkeys(part for part in parts if part))


def look_up(entries: Sequence[str], profile: Profile) -> Lookup:
    tries = {
        entry: [Board(ats, slug, _company(entry)[0]) for slug in slugs(entry) for ats in Ats]
        for entry in entries
    }
    result = poll([board for tried in tries.values() for board in tried])
    local: defaultdict[str, bool] = defaultdict(bool)
    for job in result.jobs:
        if job.board:
            local[job.board.key] |= in_country(job.location, profile)
    found = {
        entry: next((board for board in tried if local[board.key]), None)
        for entry, tried in tries.items()
    }
    return Lookup(
        [board for board in found.values() if board],
        [entry for entry, board in found.items() if board is None],
    )
