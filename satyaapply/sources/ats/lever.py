import re

from satyaapply.core.models import Ats, Board, Job, Source
from satyaapply.sources.ats.base import AtsReader, company_name, external_id
from satyaapply.sources.text import epoch_ms, html_to_text, identifier, items, mapping, text

BOARD_URL = re.compile(r"https?://jobs\.lever\.co/([\w.-]+)", re.IGNORECASE)
REMOTE_WORKPLACE = "remote"


def list_url(slug: str) -> str:
    return f"https://api.lever.co/v0/postings/{slug}?mode=json"


def posting_url(slug: str, posting_id: str) -> str:
    return f"https://api.lever.co/v0/postings/{slug}/{posting_id}"


def _description(posting: object) -> str:
    source = mapping(posting)
    sections = [text(source, "descriptionPlain")]
    for raw in items(source.get("lists")):
        section = mapping(raw)
        sections.append(f"{text(section, 'text')}\n{html_to_text(text(section, 'content'))}")
    sections.append(text(source, "additionalPlain"))
    return "\n\n".join(part for part in sections if part.strip())


def _location(posting: object) -> str:
    source = mapping(posting)
    place = text(mapping(source.get("categories")), "location")
    remote = text(source, "workplaceType").lower() == REMOTE_WORKPLACE
    return f"{place} (Remote)" if remote and place else "Remote" if remote else place


def _job(board: Board, raw: object) -> Job | None:
    posting = mapping(raw)
    posting_id, title = identifier(posting, "id"), text(posting, "text")
    page = text(posting, "hostedUrl")
    if not posting_id or not title or not page:
        return None
    return Job(
        source=Source.CAREER_PAGES,
        external_id=external_id(board, posting_id),
        url=page,
        company=company_name(board),
        title=title,
        location=_location(posting),
        description=_description(posting),
        apply_url=text(posting, "applyUrl") or f"{page}/apply",
        posted_at=epoch_ms(posting.get("createdAt")),
    )


def parse(board: Board, data: object) -> list[Job]:
    jobs = (_job(board, raw) for raw in items(data))
    return [job for job in jobs if job]


READER = AtsReader(Ats.LEVER, BOARD_URL, list_url, posting_url, parse)
