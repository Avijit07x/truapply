from collections.abc import Mapping, Sequence

from satyaapply.core.models import Source, Status
from satyaapply.store.records import JobRecord
from satyaapply.tracker.html import e, joined, outside_link, when
from satyaapply.tracker.pages import TONES, Counts, status_pill

Stage = tuple[str, str, tuple[Status, ...]]

STAGES: tuple[Stage, ...] = (
    ("Found", "🔎", (Status.NEW,)),
    ("Scored", "🎯", (Status.SCORED,)),
    ("Filled", "📝", (Status.READY,)),
    ("Needs you", "✋", (Status.NEEDS_INPUT, Status.FINISH)),
    ("Approved", "👍", (Status.APPROVED, Status.SUBMITTING)),
    ("Applied", "📨", (Status.APPLIED, Status.UNCONFIRMED)),
)
NOT_A_FIT = (Status.SKIPPED, Status.DISMISSED, Status.CLOSED)
COLUMNS = (
    (Status.NEEDS_INPUT, "Needs your answer"),
    (Status.FINISH, "Finish these"),
    (Status.READY, "Waiting for your OK"),
    (Status.APPROVED, "Approved"),
    (Status.APPLIED, "Applied"),
    (Status.SCORED, "Good matches to fill"),
)
CARDS_PER_COLUMN = 8
SOURCES = {
    Source.CAREER_PAGES: "Company careers page",
    Source.LINKEDIN: "LinkedIn",
    Source.NAUKRI: "Naukri",
    Source.INDEED: "Indeed",
    Source.WELLFOUND: "Wellfound",
    Source.MANUAL: "Added by you",
}
ARROW = '<span class="arrow" aria-hidden="true">→</span>'


def _total(counts: Counts, statuses: Sequence[Status]) -> int:
    return sum(counts.get(status, 0) for status in statuses)


def _stage(stage: Stage, counts: Counts) -> str:
    label, icon, statuses = stage
    total = _total(counts, statuses)
    tone = TONES.get(statuses[0], "") if total else "zero"
    return (
        f'<a class="stage {tone}" href="/jobs?status={statuses[0]}">'
        f'<span class="stage-head"><span aria-hidden="true">{icon}</span>{e(label)}</span>'
        f"<strong>{total}</strong></a>"
    )


def pipeline(counts: Counts) -> str:
    stages = ARROW.join(_stage(stage, counts) for stage in STAGES)
    return (
        f'<nav class="pipeline" aria-label="Workflow">{stages}</nav>'
        f'<p class="pipeline-note"><a href="/jobs?status={NOT_A_FIT[0]}">'
        f"Not a fit · {_total(counts, NOT_A_FIT)}</a></p>"
    )


def _card(item: JobRecord) -> str:
    job = item.job
    place = " · ".join(part for part in (job.company, job.location) if part)
    score = "" if job.score is None else f'<span class="pill score">Score {job.score}</span>'
    return (
        f'<a class="card-job" href="/jobs/{job.id}"><strong>{e(job.title)}</strong>'
        f'<span class="muted">{e(place)}</span><span class="card-meta">{score}'
        f'<time datetime="{e(item.updated_at.isoformat())}">{e(when(item.updated_at))}</time>'
        "</span></a>"
    )


def _column(status: Status, name: str, items: Sequence[JobRecord], total: int) -> str:
    shown = items[:CARDS_PER_COLUMN]
    cards = joined(_card(item) for item in shown) or '<p class="empty">Nothing here</p>'
    more = (
        f'<a class="see-all" href="/jobs?status={status}">See all {total} →</a>'
        if total > len(shown)
        else ""
    )
    return (
        f'<section class="column" aria-labelledby="column-{status}"><header>'
        f'<span class="dot {TONES.get(status, "")}" aria-hidden="true"></span>'
        f'<h2 id="column-{status}">{e(name)}</h2><span class="count">{total}</span></header>'
        f'<div class="cards">{cards}</div>{more}</section>'
    )


def board(columns: Mapping[Status, Sequence[JobRecord]], counts: Counts) -> str:
    body = joined(
        _column(status, name, items, max(counts.get(status, 0), len(items)))
        for status, name in COLUMNS
        for items in (columns.get(status, ()),)
    )
    return f'<div class="board" role="region" aria-label="Board" tabindex="0">{body}</div>'


def properties(record: JobRecord) -> str:
    job = record.job
    links = outside_link(job.url, "Job post") + outside_link(job.apply_url, "Application form")
    rows = (
        ("⏳", "Status", status_pill(job.status)),
        ("🎯", "Score", e("—" if job.score is None else job.score)),
        ("🏢", "Company", e(job.company)),
        ("📍", "Location", e(job.location or "Not given")),
        ("🕒", "Updated", e(when(record.updated_at))),
        ("🔎", "Found on", e(SOURCES.get(job.source, job.source))),
        ("🔗", "Links", links or '<span class="muted">None</span>'),
    )
    body = joined(
        f'<div class="prop"><dt><span aria-hidden="true">{icon}</span>{e(label)}</dt>'
        f"<dd>{value}</dd></div>"
        for icon, label, value in rows
    )
    return f'<dl class="props">{body}</dl>'


def callout(emoji: str, text_html: str) -> str:
    return (
        f'<div class="callout"><span class="callout-icon" aria-hidden="true">{e(emoji)}</span>'
        f"<div>{text_html}</div></div>"
    )
