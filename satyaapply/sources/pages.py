import hashlib
import re
from dataclasses import dataclass
from urllib.parse import urlsplit

from satyaapply.core.models import Source

DIGEST_CHARS = 16


@dataclass(frozen=True)
class Site:
    host: re.Pattern[str]
    source: Source
    job_id: re.Pattern[str]
    page: str


@dataclass(frozen=True)
class PageJob:
    source: Source
    external_id: str
    url: str


SITES = (
    Site(
        re.compile(r"(^|\.)linkedin\.com$"),
        Source.LINKEDIN,
        re.compile(r"/jobs/view/(?:[^/?#]*-)?(\d+)|[?&]currentJobId=(\d+)"),
        "https://www.linkedin.com/jobs/view/{}/",
    ),
    Site(
        re.compile(r"(^|\.)naukri\.com$"),
        Source.NAUKRI,
        re.compile(r"-(\d{9,})(?:[/?#]|$)"),
        "",
    ),
    Site(
        re.compile(r"(^|\.)indeed\.[a-z.]+$"),
        Source.INDEED,
        re.compile(r"[?&](?:jk|vjk)=([0-9a-f]+)"),
        "https://www.indeed.com/viewjob?jk={}",
    ),
    Site(
        re.compile(r"(^|\.)wellfound\.com$"),
        Source.WELLFOUND,
        re.compile(r"/jobs/(\d+)"),
        "",
    ),
)


def _plain(url: str) -> str:
    parts = urlsplit(url)
    return f"{parts.scheme}://{parts.netloc}{parts.path.rstrip('/')}"


def _found_id(site: Site, url: str) -> str | None:
    match = site.job_id.search(url)
    return next((group for group in match.groups() if group), None) if match else None


def page_job(url: str) -> PageJob:
    host = (urlsplit(url).hostname or "").removeprefix("www.")
    for site in SITES:
        posting = _found_id(site, url) if site.host.search(host) else None
        if posting:
            page = site.page.format(posting) if site.page else _plain(url)
            return PageJob(site.source, posting, page)
    digest = hashlib.sha256(_plain(url).lower().encode()).hexdigest()[:DIGEST_CHARS]
    return PageJob(Source.MANUAL, f"{host}/{digest}", _plain(url))
