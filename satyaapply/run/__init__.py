from contextlib import closing
from dataclasses import dataclass

from satyaapply.core.clock import Clock, utc_now
from satyaapply.core.paths import Paths
from satyaapply.core.profile import load
from satyaapply.resume.master import load_resume, master_pdf
from satyaapply.run.applying import Prepared, prepare
from satyaapply.run.context import Progress, RunContext, quiet
from satyaapply.run.discovery import Discovery, discover
from satyaapply.run.scoring import Scoring, score_pending
from satyaapply.store.db import connect


@dataclass(frozen=True)
class RunOptions:
    limit: int = 5
    score_limit: int = 40
    search: bool = True
    show: bool = False
    progress: Progress = quiet


@dataclass(frozen=True)
class RunReport:
    discovery: Discovery
    scoring: Scoring
    prepared: list[Prepared]


def run(paths: Paths, options: RunOptions, clock: Clock = utc_now) -> RunReport:
    profile = load(paths)
    resume = load_resume(profile)
    say = options.progress
    context = RunContext(paths, profile, resume, master_pdf(paths, resume), clock, progress=say)
    with closing(connect(paths.database)) as db:
        say("Checking company career pages …")
        found = discover(db, profile, clock(), options.search)
        say(f"  {found.found:,} open jobs · {found.added} new ones fit your titles and places")
        scored = score_pending(db, context, options.score_limit)
        prepared = prepare(db, context, options.limit, options.show)
    return RunReport(found, scored, prepared)
