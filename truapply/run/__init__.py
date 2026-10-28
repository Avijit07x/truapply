import sqlite3
from contextlib import closing
from dataclasses import dataclass

from truapply.ai.budget import Budget, metered
from truapply.core.clock import Clock, utc_now
from truapply.core.models import RunStage, Status
from truapply.core.paths import Paths
from truapply.core.profile import load
from truapply.report.summary import summarize
from truapply.resume.master import load_resume, master_pdf
from truapply.run.context import Progress, RunContext, quiet
from truapply.run.discovery import CompanySearchNow, Discovery, discover
from truapply.run.lock import run_lock
from truapply.run.rescoring import with_descriptions
from truapply.run.scoring import Scoring, score_pending, score_these
from truapply.run.tailoring import Prepared, prepare, prepare_one, tailor_all
from truapply.sources import wellfound
from truapply.store import jobs, rules, usage
from truapply.store.db import connect

RULE = "rule"
TAILORING_NOTE = "tailoring_note"
NOTHING_FOUND = Discovery(0, 0, 0, 0, 0, 0, 0)
NOTHING_SCORED = Scoring(0, 0, 0)
UNSCORED = frozenset({Status.NEW, Status.SKIPPED})


@dataclass(frozen=True)
class RunOptions:
    limit: int | None = None
    score_limit: int | None = None
    search: bool = True
    search_now: bool = False
    find: bool = True
    job: int | None = None
    score: tuple[int, ...] = ()
    only: RunStage | None = None
    progress: Progress = quiet


@dataclass(frozen=True)
class RunReport:
    discovery: Discovery
    scoring: Scoring
    prepared: list[Prepared]


def run(paths: Paths, options: RunOptions, clock: Clock = utc_now) -> RunReport:
    with run_lock(paths):
        return _locked_run(paths, options, clock)


def _score_and_tailor(
    db: sqlite3.Connection, context: RunContext, job_ids: tuple[int, ...]
) -> RunReport:
    chosen = with_descriptions(db, context, job_ids)
    scored = score_these(db, context, [job for job in chosen if job.status in UNSCORED])
    after = (jobs.find(db, job.id) for job in chosen if job.id is not None)
    good = [job for job in after if job is not None and job.status is Status.SCORED]
    return RunReport(NOTHING_FOUND, scored, tailor_all(db, context, good))


def _company_search(options: RunOptions) -> CompanySearchNow:
    if options.search_now:
        return CompanySearchNow.NOW
    return CompanySearchNow.WHEN_DUE if options.search else CompanySearchNow.SKIP


def _steps(db: sqlite3.Connection, context: RunContext, options: RunOptions) -> RunReport:
    if options.job is not None:
        return RunReport(NOTHING_FOUND, NOTHING_SCORED, prepare_one(db, context, options.job))
    if options.score:
        return RunReport(
            NOTHING_FOUND,
            score_these(db, context, with_descriptions(db, context, options.score)),
            [],
        )
    say = context.progress
    found = NOTHING_FOUND
    wanted = {options.only} if options.only else set(RunStage)
    if options.find and RunStage.FIND in wanted:
        say("Checking company career pages …")
        found = discover(db, context.profile, context.clock(), _company_search(options))
        say(f"  {found.found:,} open jobs · {found.added} new ones fit your titles and places")
        if context.profile.settings.wellfound:
            say("Checking Wellfound …")
            checked = wellfound.check(db, context.profile, context.resume_text, context.clock())
            say(f"  {checked.listed} new Wellfound jobs fit you · listed for you to apply")
            if checked.waiting_until:
                again = checked.waiting_until.astimezone().strftime("%H:%M")
                say(f"  Wellfound asked to slow down · next check after {again}")
    settings = context.profile.settings
    scored = NOTHING_SCORED
    if RunStage.SCORE in wanted:
        scored = score_pending(db, context, options.score_limit or settings.scores_per_run)
    prepared: list[Prepared] = []
    if RunStage.TAILOR in wanted:
        prepared = prepare(db, context, options.limit or settings.jobs_per_run)
    return RunReport(found, scored, prepared)


def _locked_run(paths: Paths, options: RunOptions, clock: Clock) -> RunReport:
    profile = load(paths)
    resume = load_resume(profile)
    with closing(connect(paths.database)) as db:
        context = RunContext(
            paths,
            profile,
            resume,
            master_pdf(paths, resume),
            clock,
            progress=options.progress,
            notes=rules.active_texts(db, TAILORING_NOTE),
            preferences=rules.active_texts(db, RULE),
        )
        today = clock().astimezone().date()
        budget = Budget(profile.settings.ai_calls_per_day - usage.ai_calls_on(db, today))
        try:
            with metered(budget):
                report = _steps(db, context, options)
        finally:
            usage.add_ai_calls(db, today, budget.used)
        summarize(db, paths, clock(), profile.settings)
    return report
