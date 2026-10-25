import logging
import sqlite3
from collections import Counter
from dataclasses import dataclass

from satyaapply.ai.replies import Score
from satyaapply.ai.tasks import score_job
from satyaapply.core.errors import AIError, UsageLimitError
from satyaapply.core.models import Job, Status
from satyaapply.run.context import RunContext
from satyaapply.store import jobs
from satyaapply.store.jobs import ScoreUpdate, StatusChange

DUPLICATE_NOTE = "duplicate of a job already in your queue"
NOTE_LIMIT = 90
AI_RULE_NOTE = "the employer doesn't accept AI-assisted applications"

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class Scoring:
    matched: int
    skipped: int
    failed: int


def decide(verdict: Score, min_score: int) -> tuple[Status, str]:
    if verdict.forbids_ai:
        return Status.SKIPPED, AI_RULE_NOTE
    if verdict.dealbreaker:
        return Status.SKIPPED, f"deal-breaker: {verdict.dealbreaker}"
    if verdict.score < min_score:
        return Status.SKIPPED, f"score {verdict.score}: {verdict.reason}"
    return Status.SCORED, verdict.reason


def _outcome(status: Status, score: int, note: str) -> str:
    if status is Status.SCORED:
        return f"{score}, good match"
    short = note if len(note) <= NOTE_LIMIT else note[: NOTE_LIMIT - 1].rstrip() + "…"
    return f"skipped, {short}"


def _score_one(db: sqlite3.Connection, run: RunContext, job: Job) -> tuple[str, str]:
    if job.id is None:
        return "failed", "no id"
    if jobs.is_duplicate(db, job):
        jobs.set_status(db, job.id, StatusChange(Status.SKIPPED, run.clock(), DUPLICATE_NOTE))
        return "skipped", f"skipped, {DUPLICATE_NOTE}"
    try:
        verdict = score_job(run.profile, run.resume_text, job)
    except UsageLimitError:
        raise
    except AIError as error:
        log.warning("couldn't score job %s yet: %s", job.id, error)
        return "failed", "couldn't score it, will retry next run"
    status, note = decide(verdict, run.profile.settings.min_score)
    jobs.save_score(db, job.id, ScoreUpdate(verdict.score, status, run.clock(), note))
    kind = "matched" if status is Status.SCORED else "skipped"
    return kind, _outcome(status, verdict.score, note)


def score_pending(db: sqlite3.Connection, run: RunContext, limit: int) -> Scoring:
    pending = jobs.next_to_score(db, limit)
    if pending:
        run.progress(f"Scoring {len(pending)} jobs with AI …")
    counts: Counter[str] = Counter()
    for number, job in enumerate(pending, 1):
        kind, outcome = _score_one(db, run, job)
        counts[kind] += 1
        run.progress(f"  {number}/{len(pending)} {job.company} · {job.title}: {outcome}")
    return Scoring(counts["matched"], counts["skipped"], counts["failed"])
