import re
from collections.abc import Mapping

from truapply.core.models import Ats, Board, Job, Source
from truapply.sources.ats.base import AtsReader, company_name, external_id
from truapply.sources.text import identifier, iso_time, items, mapping, text

REMOTE = "Remote"
BOARD_URL = re.compile(r"https?://jobs\.ashbyhq\.com/([\w.%-]+)", re.IGNORECASE)


def list_url(slug: str) -> str:
    return f"https://api.ashbyhq.com/posting-api/job-board/{slug}"


def posting_url(_slug: str, _posting_id: str) -> str | None:
    return None


def _is_remote(source: Mapping[str, object]) -> bool:
    workplace = text(source, "workplaceType")
    return workplace == REMOTE if workplace else source.get("isRemote") is True


def _location(posting: object) -> str:
    source = mapping(posting)
    places = [text(source, "location")]
    places += [
        text(mapping(extra), "location") for extra in items(source.get("secondaryLocations"))
    ]
    places = list(dict.fromkeys(place for place in places if place))
    if not _is_remote(source):
        return " / ".join(places)
    tied = [place if REMOTE.lower() in place.lower() else f"{REMOTE} - {place}" for place in places]
    return " / ".join([place for place in tied if place.lower() != REMOTE.lower()] or [REMOTE])


def _job(board: Board, raw: object) -> Job | None:
    posting = mapping(raw)
    posting_id, title, page = (
        identifier(posting, "id"),
        text(posting, "title"),
        text(posting, "jobUrl"),
    )
    if not posting_id or not title or not page or posting.get("isListed") is False:
        return None
    published = text(posting, "publishedAt")
    return Job(
        source=Source.CAREER_PAGES,
        external_id=external_id(board, posting_id),
        url=page,
        company=company_name(board),
        title=title,
        location=_location(posting),
        description=text(posting, "descriptionPlain"),
        apply_url=text(posting, "applyUrl") or f"{page}/application",
        posted_at=iso_time(published) if published else None,
    )


def parse(board: Board, data: object) -> list[Job]:
    jobs = (_job(board, raw) for raw in items(mapping(data).get("jobs")))
    return [job for job in jobs if job]


READER = AtsReader(Ats.ASHBY, BOARD_URL, list_url, posting_url, parse)
