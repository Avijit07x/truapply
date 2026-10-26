import logging
import sqlite3
import time
from collections.abc import Mapping, Sequence
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from functools import partial
from pathlib import Path
from random import SystemRandom

from playwright.sync_api import BrowserContext
from playwright.sync_api import Error as PlaywrightError

from satyaapply.apply.fill import Files
from satyaapply.apply.flow import ApplyRequest, Attempt, apply
from satyaapply.browser.page import screenshot
from satyaapply.browser.session import browser_session
from satyaapply.core.clock import Clock, start_of_local_day
from satyaapply.core.errors import AIError, UsageLimitError
from satyaapply.core.forms import FormContext
from satyaapply.core.models import Job, Source, Status
from satyaapply.core.profile import Profile
from satyaapply.resume.tailor import Tailored, TailorRequest, file_name_for, tailor
from satyaapply.run.context import PARALLEL_AI_CALLS, RunContext
from satyaapply.sources.ats import still_open
from satyaapply.store import answers, jobs
from satyaapply.store.answers import AnswerSource, SavedAnswer
from satyaapply.store.jobs import AttemptRecord, StatusChange

PAUSE_RANGE_S = {Source.CAREER_PAGES: (4.0, 12.0)}
DEFAULT_PAUSE_RANGE_S = (30.0, 90.0)
CLOSED_NOTE = "the job was removed from the company's board"
COVER_LETTER_NAME = "Cover_Letter.pdf"

log = logging.getLogger(__name__)
randomness = SystemRandom()


@dataclass(frozen=True)
class Queued:
    job_id: int
    job: Job
    resume: Tailored


@dataclass(frozen=True)
class Prepared:
    job: Job
    attempt: Attempt
    resume: Tailored
    shot: Path | None


def allowance(db: sqlite3.Connection, profile: Profile, clock: Clock, limit: int) -> int:
    if profile.daily_cap is None:
        return limit
    prepared = jobs.prepared_since(db, start_of_local_day(clock()))
    return max(0, min(limit, profile.daily_cap - prepared))


def _drop_closed(db: sqlite3.Connection, picks: Sequence[Job], clock: Clock) -> list[Job]:
    still = []
    for job, state in zip(picks, still_open(picks), strict=True):
        if state is False and job.id is not None:
            jobs.set_status(db, job.id, StatusChange(Status.CLOSED, clock(), CLOSED_NOTE))
        else:
            still.append(job)
    return still


def _tailored(run: RunContext, pick: tuple[int, Job]) -> Queued:
    job_id, job = pick
    request = TailorRequest(
        job, run.notes, run.paths.job_dir(job_id), file_name_for(run.profile.name), run.master
    )
    return Queued(job_id, job, tailor(run.resume, request))


def tailor_all(run: RunContext, picks: Sequence[Job]) -> list[Queued]:
    ready = [(job.id, job) for job in picks if job.id is not None]
    if ready:
        run.progress(
            f"Tailoring your resume for {len(ready)} {'job' if len(ready) == 1 else 'jobs'} …"
        )
    queued: list[Queued] = []
    with ThreadPoolExecutor(PARALLEL_AI_CALLS) as pool:
        try:
            for item in pool.map(partial(_tailored, run), ready):
                kept = "kept your original resume" if item.resume.used_original else "tailored"
                run.progress(f"  {item.job.company} · {item.job.title}: {kept}")
                queued.append(item)
        except UsageLimitError:
            pool.shutdown(cancel_futures=True)
            raise
    return queued


def _request(run: RunContext, item: Queued, known: Mapping[str, str]) -> ApplyRequest:
    return ApplyRequest(
        context=FormContext(run.profile, run.resume_text, item.job),
        files=Files(resume=None if run.dry_run else item.resume.pdf, cover_letter=None),
        known=known,
        dry_run=run.dry_run,
        cover_letter_target=run.paths.job_dir(item.job_id) / COVER_LETTER_NAME,
    )


def _pause(source: Source) -> None:
    low, high = PAUSE_RANGE_S.get(source, DEFAULT_PAUSE_RANGE_S)
    time.sleep(randomness.uniform(low, high))


def _attempt(
    context: BrowserContext, request: ApplyRequest, shot: Path
) -> tuple[Attempt, Path | None]:
    page = context.new_page()
    try:
        attempt = apply(page, request)
    except UsageLimitError:
        page.close()
        raise
    except (AIError, PlaywrightError) as error:
        attempt = Attempt(Status.FAILED, f"stopped: {error}")
    taken = screenshot(page, shot)
    page.close()
    return attempt, taken


def _record(db: sqlite3.Connection, run: RunContext, item: Queued, attempt: Attempt) -> None:
    now = run.clock()
    record = AttemptRecord(attempt.status, now, attempt.note, attempt.sent, item.resume.pdf)
    jobs.record_attempt(db, item.job_id, record)
    learned = [SavedAnswer(sent.question, sent.answer, AnswerSource.AI) for sent in attempt.learned]
    answers.save_many(db, learned, now)
    answers.open_questions(db, attempt.questions, item.job_id, now)


def prepare(db: sqlite3.Connection, run: RunContext, limit: int, show: bool) -> list[Prepared]:
    picks = jobs.next_to_apply(db, allowance(db, run.profile, run.clock, limit))
    queue = tailor_all(run, _drop_closed(db, picks, run.clock))
    if not queue:
        return []
    known = answers.all_answers(db)
    results: list[Prepared] = []
    with browser_session(run.paths.browser, show) as context:
        for index, item in enumerate(queue):
            if index:
                _pause(item.job.source)
            shot = run.paths.shots / f"{item.job_id}.png"
            run.progress(f"Filling the form for {item.job.company} · {item.job.title} …")
            attempt, taken = _attempt(context, _request(run, item, known), shot)
            _record(db, run, item, attempt)
            results.append(Prepared(item.job, attempt, item.resume, taken))
    return results
