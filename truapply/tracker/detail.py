import sqlite3
from datetime import datetime
from enum import StrEnum
from pathlib import Path
from urllib.parse import urlsplit

from truapply.core.errors import TruApplyError
from truapply.core.models import Status
from truapply.core.paths import Paths
from truapply.core.profile import load
from truapply.resume.diff import changed_lines
from truapply.resume.master import load_resume
from truapply.store import feedback
from truapply.store.records import JobRecord
from truapply.tracker.plain import readable_changes

WEB_SCHEMES = frozenset({"http", "https"})
CLOSED_REASON = "job is closed"
DISMISS_REASONS = (
    "wrong role",
    "too senior",
    "too junior",
    "location",
    "salary",
    "company",
    CLOSED_REASON,
    "other",
)
DISMISSABLE = frozenset({Status.READY, Status.SCORED})


class Action(StrEnum):
    DISMISS = "dismiss"
    THUMBS = "thumbs"
    FINISHED = "finished"
    REVERT = "revert"
    SCORE = "score"
    TAILOR = "tailor"


SCORABLE = frozenset({Status.NEW, Status.SKIPPED})
ALLOWED: dict[Action, frozenset[Status]] = {
    Action.DISMISS: DISMISSABLE,
    Action.THUMBS: frozenset(Status),
    Action.FINISHED: frozenset({Status.READY}),
    Action.REVERT: frozenset({Status.READY}),
    Action.SCORE: SCORABLE,
    Action.TAILOR: frozenset({Status.SCORED}),
}


def iso(moment: datetime) -> str:
    return moment.isoformat()


def web_link(url: str) -> str | None:
    return url if urlsplit(url).scheme in WEB_SCHEMES else None


def job_id(record: JobRecord) -> int:
    return record.job.id or 0


def job_row(record: JobRecord) -> dict[str, object]:
    job = record.job
    return {
        "id": job_id(record),
        "title": job.title,
        "company": job.company,
        "location": job.location,
        "score": job.score,
        "status": job.status.value,
        "source": job.source.value,
        "autoSubmitted": record.auto_submitted,
        "updatedAt": iso(record.updated_at),
    }


def inside(path: Path | None, root: Path) -> Path | None:
    if path is None or not path.is_file():
        return None
    return path if path.resolve().is_relative_to(root.resolve()) else None


def resume_pdf(paths: Paths, record: JobRecord) -> Path | None:
    return inside(record.resume_pdf, paths.root)


def resume_to_send(paths: Paths, record: JobRecord) -> Path | None:
    return resume_pdf(paths, record) or (paths.master_pdf if paths.master_pdf.is_file() else None)


def changes(paths: Paths, record: JobRecord) -> list[str] | None:
    try:
        resume = load_resume(load(paths))
    except TruApplyError:
        return None
    tailored = paths.job_dir(job_id(record)) / f"tailored{resume.suffix}"
    if not tailored.is_file():
        return None
    original = resume.readable(resume.source)
    lines = changed_lines(original, resume.readable(tailored.read_text(encoding="utf-8")))
    return readable_changes(lines)


def _actions(status: Status, tailored: bool) -> list[str]:
    return [
        action.value
        for action, allowed in ALLOWED.items()
        if status in allowed and (tailored or action is not Action.REVERT)
    ]


def job_detail(db: sqlite3.Connection, paths: Paths, record: JobRecord) -> dict[str, object]:
    job = record.job
    changed = changes(paths, record)
    sent = [{"question": item.question, "answer": item.answer} for item in record.sent]
    return job_row(record) | {
        "reason": record.reason,
        "note": record.note,
        "source": job.source.value,
        "url": web_link(job.url),
        "applyUrl": web_link(job.apply_url),
        "description": job.description,
        "sent": sent,
        "changes": changed,
        "hasResume": resume_pdf(paths, record) is not None,
        "feedback": feedback.thumbs(db, job_id(record)),
        "actions": _actions(job.status, changed is not None),
        "dismissReasons": list(DISMISS_REASONS),
    }
