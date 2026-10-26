from dataclasses import replace
from datetime import UTC, datetime

from satyaapply.core.models import Status
from satyaapply.store.records import JobRecord
from satyaapply.tracker.board import board, callout, pipeline, properties
from satyaapply.tracker.layout import shell
from satyaapply.tracker.pages import LABELS
from tests.unit import samples

NOW = datetime(2026, 10, 25, 12, 0, tzinfo=UTC)
INJECTED = "<script>x</script>"


def record(job_id: int, status: Status, title: str = "Frontend Engineer") -> JobRecord:
    job = replace(samples.job(), id=job_id, status=status, title=title, score=81)
    return JobRecord(job, "", "", NOW, (), None)


def test_pipeline_sums_each_stage_and_links_to_its_first_status() -> None:
    html = pipeline({Status.NEEDS_INPUT: 2, Status.FINISH: 3, Status.SKIPPED: 4})
    assert '<a class="stage warn" href="/jobs?status=needs_input">' in html
    assert "Needs you</span><strong>5</strong>" in html
    assert '<a class="stage zero" href="/jobs?status=new">' in html
    assert html.count('class="arrow" aria-hidden="true">→</span>') == 5
    assert "Not a fit · 4" in html


def test_board_lists_columns_cards_and_escapes_titles() -> None:
    html = board({Status.READY: [record(7, Status.READY, INJECTED)]}, {Status.READY: 1})
    assert html.count('<section class="column"') == 6
    assert '<a class="card-job" href="/jobs/7">' in html
    assert INJECTED not in html
    assert "&lt;script&gt;x&lt;/script&gt;" in html
    assert "Northwind" in html
    assert "Score 81" in html
    assert html.count("Nothing here") == 5
    assert "See all" not in html


def test_board_caps_cards_and_links_to_the_rest() -> None:
    items = [record(job_id, Status.APPLIED) for job_id in range(1, 13)]
    html = board({Status.APPLIED: items}, {Status.APPLIED: 12})
    assert html.count('class="card-job"') == 8
    assert '<a class="see-all" href="/jobs?status=applied">See all 12 →</a>' in html


def test_shell_marks_the_active_page_and_links_both_stylesheets() -> None:
    html = shell("Board", "<p>hi</p>", "/board")
    assert '<a href="/board" class="active" aria-current="page">' in html
    assert html.count('aria-current="page"') == 1
    assert '<link rel="stylesheet" href="/style.css">' in html
    assert '<link rel="stylesheet" href="/theme.css">' in html
    assert "<title>Board · SatyaApply</title>" in html
    assert '<main class="content" id="content"><p>hi</p></main>' in html


def test_properties_escape_text_and_show_the_status_label() -> None:
    item = record(3, Status.NEEDS_INPUT)
    item = replace(item, job=replace(item.job, company=INJECTED))
    html = properties(item)
    assert INJECTED not in html
    assert LABELS[Status.NEEDS_INPUT] in html
    assert "Company careers page" in html
    assert 'href="https://jobs.example.com/42"' in html


def test_callout_escapes_the_icon_and_keeps_given_html() -> None:
    assert callout("<b>", "<p>ok</p>") == (
        '<div class="callout"><span class="callout-icon" aria-hidden="true">&lt;b&gt;</span>'
        "<div><p>ok</p></div></div>"
    )
