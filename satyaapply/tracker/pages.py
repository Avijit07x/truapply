from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from satyaapply.core.models import Status
from satyaapply.store.records import JobRecord
from satyaapply.tracker.html import e, empty, joined, outside_link, page, section, when

LABELS = {
    Status.NEW: "Waiting to be scored",
    Status.SKIPPED: "Not a fit",
    Status.SCORED: "Good match, not filled yet",
    Status.READY: "Filled, waiting for your OK",
    Status.APPROVED: "Approved, sends on the next run",
    Status.DISMISSED: "Dismissed",
    Status.SUBMITTING: "Sending",
    Status.APPLIED: "Applied",
    Status.UNCONFIRMED: "Sent, not confirmed",
    Status.NEEDS_INPUT: "Needs your answer",
    Status.EXTERNAL: "Apply on their site",
    Status.FAILED: "Something broke",
    Status.CLOSED: "Job closed",
    Status.FINISH: "Finish it yourself",
}
TONES = {
    Status.SCORED: "good",
    Status.READY: "good",
    Status.APPROVED: "good",
    Status.APPLIED: "good",
    Status.NEEDS_INPUT: "warn",
    Status.UNCONFIRMED: "warn",
    Status.EXTERNAL: "warn",
    Status.FAILED: "bad",
    Status.FINISH: "warn",
}
HOME_TILES = (
    (Status.NEEDS_INPUT, "Need your answer"),
    (Status.FINISH, "Finish these"),
    (Status.READY, "Waiting for your OK"),
    (Status.SCORED, "Good matches to fill"),
    (Status.APPLIED, "Applied"),
)
TABLE_HEAD = (
    "<tr><th>Job</th><th>Company</th><th>Location</th><th>Score</th>"
    "<th>Status</th><th>Updated</th></tr>"
)

Counts = Mapping[Status, int]


def status_pill(status: Status) -> str:
    return f'<span class="pill {TONES.get(status, "")}">{e(LABELS[status])}</span>'


def _row(item: JobRecord) -> str:
    job = item.job
    score = "" if job.score is None else job.score
    return (
        f'<tr><td><a href="/jobs/{job.id}">{e(job.title)}</a></td><td>{e(job.company)}</td>'
        f'<td>{e(job.location)}</td><td class="num">{e(score)}</td>'
        f"<td>{status_pill(job.status)}</td><td>{e(when(item.updated_at))}</td></tr>"
    )


def job_table(items: Sequence[JobRecord], nothing: str) -> str:
    if not items:
        return empty(nothing)
    rows = joined(_row(item) for item in items)
    table = f"<table><thead>{TABLE_HEAD}</thead><tbody>{rows}</tbody></table>"
    return f'<div class="table-wrap">{table}</div>'


def home(
    counts: Counts,
    lists: Mapping[Status, Sequence[JobRecord]],
    recent: Sequence[JobRecord],
    panels: Sequence[str] = (),
) -> str:
    tiles = joined(
        f'<a class="tile" href="/jobs?status={status}"><strong>{counts.get(status, 0)}</strong>'
        f"{e(text)}</a>"
        for status, text in HOME_TILES
    )
    body = (
        "<h1>Your applications</h1>"
        f'<p class="muted">{sum(counts.values())} jobs saved.</p>'
        f'<div class="tiles">{tiles}</div>'
        + joined(panels)
        + section(
            "Needs your answer",
            job_table(lists.get(Status.NEEDS_INPUT, ()), "Nothing needs you right now."),
        )
        + section(
            "Waiting for your OK", job_table(lists.get(Status.READY, ()), "Nothing is waiting.")
        )
        + section(
            "Recently updated",
            job_table(recent, "No jobs yet. Run `satyaapply run` to find some."),
        )
    )
    return page("Home", body)


def _chip(href: str, text: str, count: int, on: bool) -> str:
    classes = " ".join(name for name, wanted in (("on", on), ("zero", not count)) if wanted)
    return f'<a class="chip {classes}" href="{href}">{e(text)} · {count}</a>'


def jobs_list(counts: Counts, status: Status | None, items: Sequence[JobRecord]) -> str:
    chips = _chip("/jobs", "All", sum(counts.values()), status is None) + joined(
        _chip(f"/jobs?status={option}", LABELS[option], counts.get(option, 0), option is status)
        for option in Status
    )
    title = LABELS[status] if status else "All jobs"
    body = f'<h1>{e(title)}</h1><nav class="chips">{chips}</nav>' + job_table(
        items, "No jobs here."
    )
    return page(title, body)


def _changes(changes: Sequence[str] | None, has_resume: bool) -> str:
    if changes is None and not has_resume:
        return empty("Not tailored: this job hasn't been filled in.")
    if changes is None:
        return empty("No tailored version: your original resume was used.")
    if not changes:
        return empty("Tailored, but nothing changed from your original.")
    lines = joined(
        f'<span class="{"add" if line.startswith("+") else "del"}">{e(line)}</span>\n'
        for line in changes
    )
    return f'<pre class="diff">{lines}</pre>'


def _resume(record: JobRecord, changes: Sequence[str] | None, has_resume: bool) -> str:
    link = (
        f'<p><a href="/jobs/{record.job.id}/resume.pdf">Open the resume PDF</a></p>'
        if has_resume
        else ""
    )
    return section("Resume", link + "<h3>What changed</h3>" + _changes(changes, has_resume))


def _sent(record: JobRecord) -> str:
    if not record.sent:
        return section("What was filled in", empty("Nothing filled in yet."))
    pairs = joined(f"<dt>{e(item.question)}</dt><dd>{e(item.answer)}</dd>" for item in record.sent)
    return section("What was filled in", f'<dl class="sent">{pairs}</dl>')


@dataclass(frozen=True)
class JobView:
    record: JobRecord
    changes: Sequence[str] | None
    has_shot: bool
    has_resume: bool
    controls: str = ""


def job_detail(view: JobView) -> str:
    record, changes, has_shot, has_resume = (
        view.record,
        view.changes,
        view.has_shot,
        view.has_resume,
    )
    job = record.job
    score = f" Score <strong>{job.score}</strong>" if job.score is not None else ""
    reason = f"<p><strong>Why this score:</strong> {e(record.reason)}</p>" if record.reason else ""
    last = record.note if record.note != record.reason else ""
    note = f'<p class="muted">Last step: {e(last)}</p>' if last else ""
    links = outside_link(job.url, "Job post") + outside_link(job.apply_url, "Application form")
    shot = (
        section("Screenshot", f'<img class="shot" src="/jobs/{job.id}/screenshot.png" alt="">')
        if has_shot
        else ""
    )
    body = (
        '<p><a href="/jobs">← All jobs</a></p>'
        f"<h1>{e(job.title)}</h1>"
        f'<p class="muted">{e(job.company)} · {e(job.location or "Location not given")}</p>'
        f'<div class="card"><p>{status_pill(job.status)}{score}'
        f' <span class="muted">· updated {e(when(record.updated_at))}</span></p>{reason}{note}'
        f'<div class="links">{links}</div></div>'
        + view.controls
        + _sent(record)
        + _resume(record, changes, has_resume)
        + shot
        + section(
            "Job description",
            f"<details><summary>Show</summary><pre>{e(job.description)}</pre></details>",
        )
    )
    return page(f"{job.title} · {job.company}", body)
