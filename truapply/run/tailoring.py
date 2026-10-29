import sqlite3
from collections.abc import Sequence
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from functools import partial

from truapply.core.clock import Clock, start_of_local_day
from truapply.core.errors import UsageLimitError
from truapply.core.models import Job, Source, Status
from truapply.core.notes import LOW_SCORE_PREFIX
from truapply.core.profile import Profile
from truapply.resume.tailor import Tailored, TailorRequest, file_name_for, tailor
from truapply.run.context import PARALLEL_AI_CALLS, RunContext
from truapply.run.scoring import score_one
from truapply.sources.ats import still_open
from truapply.store import jobs, records
from truapply.store.jobs import AttemptRecord, StatusChange

CLOSED_NOTE = "the job was removed from the company's board or its deadline passed"
READY_NOTE = "ready for you to apply in your Chrome"
KEPT_NOTE = "ready for you to apply in your Chrome, with your original resume"


@dataclass(frozen=True)
class Prepared:
    job: Job
    resume: Tailored


def allowance(db: sqlite3.Connection, profile: Profile, clock: Clock, limit: int) -> int:
    if profile.daily_cap is None:
        return limit
    prepared = jobs.prepared_since(db, start_of_local_day(clock()))
    return max(0, min(limit, profile.daily_cap - prepared))


def site_caps(profile: Profile) -> dict[Source, int]:
    return {Source.LINKEDIN: profile.settings.linkedin_cap}


def within_site_caps(
    db: sqlite3.Connection, profile: Profile, clock: Clock, picks: Sequence[Job]
) -> list[Job]:
    since = start_of_local_day(clock())
    left = {
        source: cap - jobs.prepared_since(db, since, source)
        for source, cap in site_caps(profile).items()
    }
    kept: list[Job] = []
    for job in picks:
        room = left.get(job.source)
        if room is not None:
            if room <= 0:
                continue
            left[job.source] = room - 1
        kept.append(job)
    return kept


def _drop_closed(db: sqlite3.Connection, picks: Sequence[Job], clock: Clock) -> list[Job]:
    still = []
    for job, state in zip(picks, still_open(picks, clock()), strict=True):
        if state is False and job.id is not None:
            jobs.set_status(db, job.id, StatusChange(Status.CLOSED, clock(), CLOSED_NOTE))
        else:
            still.append(job)
    return still


def _tailored(run: RunContext, job: Job) -> Prepared:
    job_id = job.id or 0
    request = TailorRequest(
        job, run.notes, run.paths.job_dir(job_id), file_name_for(run.profile.name), run.master
    )
    return Prepared(job, tailor(run.resume, request))


def _record(db: sqlite3.Connection, run: RunContext, item: Prepared) -> None:
    note = KEPT_NOTE if item.resume.used_original else READY_NOTE
    record = AttemptRecord(Status.READY, run.clock(), note, (), item.resume.pdf)
    jobs.record_attempt(db, item.job.id or 0, record)


def tailor_all(db: sqlite3.Connection, run: RunContext, picks: Sequence[Job]) -> list[Prepared]:
    ready = [job for job in picks if job.id is not None]
    if ready:
        run.progress(
            f"Tailoring your resume for {len(ready)} {'job' if len(ready) == 1 else 'jobs'} …"
        )
    done: list[Prepared] = []
    with ThreadPoolExecutor(PARALLEL_AI_CALLS) as pool:
        try:
            for item in pool.map(partial(_tailored, run), ready):
                kept = "kept your original resume" if item.resume.used_original else "tailored"
                run.progress(f"  {item.job.company} · {item.job.title}: {kept}")
                _record(db, run, item)
                done.append(item)
        except UsageLimitError:
            pool.shutdown(cancel_futures=True)
            raise
    return done


def prepare(db: sqlite3.Connection, run: RunContext, limit: int) -> list[Prepared]:
    budget = allowance(db, run.profile, run.clock, limit)
    picks = within_site_caps(db, run.profile, run.clock, jobs.next_to_apply(db, budget))
    return tailor_all(db, run, _drop_closed(db, picks, run.clock))


def _chosen(db: sqlite3.Connection, job_id: int) -> Job | None:
    record = records.find(db, job_id)
    if record is None:
        return None
    low = record.job.status is Status.SKIPPED and record.note.startswith(LOW_SCORE_PREFIX)
    return record.job if record.job.status is Status.SCORED or low else None


def prepare_one(db: sqlite3.Connection, run: RunContext, job_id: int) -> list[Prepared]:
    job = jobs.find(db, job_id)
    if job is not None and job.status is Status.NEW:
        score_one(db, run, job)
    chosen = _chosen(db, job_id)
    return tailor_all(db, run, [chosen]) if chosen else []
