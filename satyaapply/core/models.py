import re
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

LEGAL_SUFFIXES = frozenset(
    {
        "inc",
        "llc",
        "llp",
        "ltd",
        "limited",
        "pvt",
        "private",
        "corp",
        "corporation",
        "co",
        "gmbh",
        "plc",
        "ag",
        "sa",
        "bv",
    }
)
NON_WORD = re.compile(r"[^a-z0-9]+")
BOARD_ID_PARTS = 3


class Status(StrEnum):
    NEW = "new"
    SKIPPED = "skipped"
    SCORED = "scored"
    READY = "ready"
    APPROVED = "approved"
    DISMISSED = "dismissed"
    SUBMITTING = "submitting"
    APPLIED = "applied"
    UNCONFIRMED = "unconfirmed"
    NEEDS_INPUT = "needs_input"
    EXTERNAL = "external"
    FAILED = "failed"
    CLOSED = "closed"
    FINISH = "finish"


ACTIVE_STATUSES = (
    Status.READY,
    Status.APPROVED,
    Status.SUBMITTING,
    Status.APPLIED,
    Status.UNCONFIRMED,
)


class Ats(StrEnum):
    GREENHOUSE = "greenhouse"
    LEVER = "lever"
    ASHBY = "ashby"


@dataclass(frozen=True)
class Board:
    ats: Ats
    slug: str
    company: str = ""

    @property
    def key(self) -> str:
        return f"{self.ats}/{self.slug}"


class Source(StrEnum):
    CAREER_PAGES = "career_pages"
    LINKEDIN = "linkedin"
    NAUKRI = "naukri"
    INDEED = "indeed"
    WELLFOUND = "wellfound"
    MANUAL = "manual"


def normalize(text: str) -> str:
    return " ".join(NON_WORD.sub(" ", text.lower()).split())


def normalize_company(name: str) -> str:
    words = normalize(name).split()
    while len(words) > 1 and words[-1] in LEGAL_SUFFIXES:
        words.pop()
    return " ".join(words)


def make_dupe_key(company: str, title: str) -> str:
    return f"{normalize_company(company)}|{normalize(title)}"


@dataclass(frozen=True)
class Job:
    source: Source
    external_id: str
    url: str
    company: str
    title: str
    location: str = ""
    description: str = ""
    apply_url: str = ""
    posted_at: datetime | None = None
    status: Status = Status.NEW
    score: int | None = None
    id: int | None = None

    @property
    def key(self) -> str:
        return f"{self.source}:{self.external_id}"

    @property
    def board(self) -> Board | None:
        parts = self.external_id.split("/")
        if self.source is not Source.CAREER_PAGES or len(parts) != BOARD_ID_PARTS:
            return None
        try:
            return Board(Ats(parts[0]), parts[1], self.company)
        except ValueError:
            return None

    @property
    def posting_id(self) -> str:
        return self.external_id.rsplit("/", 1)[-1]

    @property
    def dupe_key(self) -> str:
        return make_dupe_key(self.company, self.title)
