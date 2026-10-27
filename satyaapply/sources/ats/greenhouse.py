import re

from satyaapply.core.models import Ats, Board, Job, Source
from satyaapply.sources.ats.base import AtsReader, company_name, external_id
from satyaapply.sources.text import html_to_text, identifier, iso_time, items, mapping, text

BOARD_URL = re.compile(
    r"https?://(?:job-boards|boards)\.greenhouse\.io/(?:embed/job_(?:board|app)(?:/confirmation)?\?for=)?([\w-]+)",
    re.IGNORECASE,
)


def list_url(slug: str) -> str:
    return f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true"


def posting_url(slug: str, posting_id: str) -> str:
    return f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs/{posting_id}"


def job_page(slug: str, posting_id: str) -> str:
    return f"https://job-boards.greenhouse.io/{slug}/jobs/{posting_id}"


def application_form(slug: str, posting_id: str) -> str:
    return f"https://job-boards.greenhouse.io/embed/job_app?for={slug}&token={posting_id}"


DATES = ("first_published", "updated_at")


def _job(board: Board, raw: object) -> Job | None:
    posting = mapping(raw)
    posting_id, title = identifier(posting, "id"), text(posting, "title")
    if not posting_id or not title:
        return None
    page = job_page(board.slug, posting_id)
    stamps = [stamp for key in DATES if (stamp := iso_time(text(posting, key)))]
    return Job(
        source=Source.CAREER_PAGES,
        external_id=external_id(board, posting_id),
        url=page,
        company=text(posting, "company_name") or company_name(board),
        title=title,
        location=text(mapping(posting.get("location")), "name"),
        description=html_to_text(text(posting, "content")),
        apply_url=application_form(board.slug, posting_id),
        posted_at=max(stamps, default=None),
    )


def parse(board: Board, data: object) -> list[Job]:
    jobs = (_job(board, raw) for raw in items(mapping(data).get("jobs")))
    return [job for job in jobs if job]


READER = AtsReader(Ats.GREENHOUSE, BOARD_URL, list_url, posting_url, parse)
