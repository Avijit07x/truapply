import logging
import sqlite3
from collections import Counter
from collections.abc import Sequence
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from functools import partial

from satyaapply.ai.replies import Score
from satyaapply.ai.tasks import score_job
from satyaapply.core.errors import AIError, UsageLimitError
from satyaapply.core.models import Job, Status
from satyaapply.core.profile import Profile
from satyaapply.run.context import PARALLEL_AI_CALLS, RunContext
from satyaapply.store import jobs
from satyaapply.store.jobs import ScoreUpdate, StatusChange

DUPLICATE_NOTE = "duplicate of a job already in your queue"
NOTE_LIMIT = 90

Outcome = tuple[str, str]
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


def _verdict(profile: Profile, resume_text: str, job: Job) -> Score | AIError:
    try:
        return score_job(profile, resume_text, job)
    except UsageLimitError:
        raise
    except AIError as error:
        return error


def _save(db: sqlite3.Connection, run: RunContext, job: Job, verdict: Score | AIError) -> Outcome:
    if job.id is None or isinstance(verdict, AIError):
        log.warning("couldn't score job %s yet: %s", job.id, verdict)
        return "failed", "couldn't score it, will retry next run"
    status, note = decide(verdict, run.profile.settings.min_score)
    jobs.save_score(db, job.id, ScoreUpdate(verdict.score, status, run.clock(), note))
    kind = "matched" if status is Status.SCORED else "skipped"
    return kind, _outcome(status, verdict.score, note)


def _batch(
    db: sqlite3.Connection, run: RunContext, candidates: Sequence[Job]
) -> tuple[list[Job], int]:
    batch: list[Job] = []
    seen: set[str] = set()
    duplicates = 0
    for job in candidates:
        if job.id is None or job.dupe_key in seen:
            continue
        if jobs.is_duplicate(db, job):
            jobs.set_status(db, job.id, StatusChange(Status.SKIPPED, run.clock(), DUPLICATE_NOTE))
            run.progress(f"  {job.company} · {job.title}: skipped, {DUPLICATE_NOTE}")
            duplicates += 1
            continue
        seen.add(job.dupe_key)
        batch.append(job)
    return batch, duplicates


def score_pending(db: sqlite3.Connection, run: RunContext, limit: int) -> Scoring:
    batch, duplicates = _batch(db, run, jobs.next_to_score(db, limit))
    counts: Counter[str] = Counter(skipped=duplicates)
    if batch:
        run.progress(f"Scoring {len(batch)} {'job' if len(batch) == 1 else 'jobs'} with AI …")
    score = partial(_verdict, run.profile, run.resume_text)
    with ThreadPoolExecutor(PARALLEL_AI_CALLS) as pool:
        try:
            verdicts = zip(batch, pool.map(score, batch), strict=True)
            for number, (job, verdict) in enumerate(verdicts, 1):
                kind, outcome = _save(db, run, job, verdict)
                counts[kind] += 1
                run.progress(f"  {number}/{len(batch)} {job.company} · {job.title}: {outcome}")
        except UsageLimitError:
            pool.shutdown(cancel_futures=True)
            raise
    return Scoring(counts["matched"], counts["skipped"], counts["failed"])
