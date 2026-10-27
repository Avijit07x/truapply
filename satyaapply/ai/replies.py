from dataclasses import dataclass

from satyaapply.core.documents import ResumeData


@dataclass(frozen=True)
class Pong:
    ok: bool


@dataclass(frozen=True)
class ProfileDraft:
    name: str
    email: str
    phone: str
    city: str
    country: str
    links: tuple[str, ...]
    current_company: str
    current_title: str
    years_experience: float
    skills: tuple[str, ...]
    suggested_roles: tuple[str, ...]
    title_keywords: tuple[str, ...]
    title_exclude: tuple[str, ...]


@dataclass(frozen=True)
class LatexRewrite:
    body: str
    changes: tuple[str, ...]


@dataclass(frozen=True)
class StructuredRewrite:
    resume: ResumeData
    changes: tuple[str, ...]


@dataclass(frozen=True)
class ClaimReview:
    new_claims: tuple[str, ...]


@dataclass(frozen=True)
class Score:
    score: int
    reason: str
    dealbreaker: str | None
    forbids_ai: bool


@dataclass(frozen=True)
class FoundPostings:
    urls: tuple[str, ...]


@dataclass(frozen=True)
class Posting:
    title: str
    company: str
    location: str
    description: str
