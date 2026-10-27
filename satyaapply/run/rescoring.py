import sqlite3
from collections.abc import Sequence

from satyaapply.core.errors import SatyaApplyError
from satyaapply.core.models import Job
from satyaapply.run.context import RunContext
from satyaapply.sources.ats import board_of
from satyaapply.sources.intake import take_in_link
from satyaapply.store import jobs


def _refetch(db: sqlite3.Connection, run: RunContext, job: Job, polled: set[str]) -> None:
    board = board_of(job.url)
    if board is None or board.key in polled:
        return
    polled.add(board.key)
    try:
        take_in_link(db, job.url, run.profile, run.clock())
    except SatyaApplyError as error:
        run.progress(f"  {job.company}: couldn't read the job board ({error})")


def with_descriptions(db: sqlite3.Connection, run: RunContext, ids: Sequence[int]) -> list[Job]:
    polled: set[str] = set()
    ready: list[Job] = []
    for job_id in ids:
        job = jobs.find(db, job_id)
        if job is not None and not job.description:
            _refetch(db, run, job, polled)
            job = jobs.find(db, job_id)
        if job is not None and job.description:
            ready.append(job)
        elif job is not None:
            run.progress(f"  {job.company} · {job.title}: no description found, not scored")
    return ready
