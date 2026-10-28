import json
import os
import re
from collections.abc import Iterator
from contextlib import closing, contextmanager
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from importlib import resources
from pathlib import Path
from typing import Literal

import pytest
from playwright.sync_api import (
    Browser,
    ConsoleMessage,
    Error,
    Page,
    Route,
    ViewportSize,
    expect,
    sync_playwright,
)

from satyaapply.core import schedule
from satyaapply.core.models import Source, Status
from satyaapply.core.notes import WELLFOUND_NOTE, WRONG_TITLE_NOTE
from satyaapply.core.paths import Paths
from satyaapply.core.profile import load, save
from satyaapply.store import feedback, jobs, records, rules
from satyaapply.store.db import connect
from satyaapply.store.feedback import FeedbackKind
from satyaapply.store.groups import Group
from satyaapply.store.jobs import AttemptRecord, StatusChange
from satyaapply.tracker import automatic, runs
from tests.unit import samples
from tests.unit.tracker_api import get, ids_in, running, seed_every_group

BUILT = resources.files("satyaapply.tracker").joinpath("static", "index.html").is_file()
pytestmark = [
    pytest.mark.e2e,
    pytest.mark.skipif(not BUILT, reason="build the app first: cd web && npm ci && npm run build"),
]

NOW = datetime(2026, 10, 25, 12, 0, tzinfo=UTC)
DESKTOP = ViewportSize(width=1440, height=900)
PHONE = ViewportSize(width=390, height=844)
THEME_KEY = "satyaapply-theme"
Theme = Literal["light", "dark"]
PAGES = (
    (
        "/",
        re.compile(r"^(You're all caught up|1 job is ready for you|\d+ jobs are ready for you)$"),
    ),
    ("/workflow", "Workflow"),
    ("/jobs", "Career jobs"),
    ("/jobs?group=ready", "Ready for you to apply"),
    ("/jobs/9", "Frontend Engineer"),
    ("/companies", "Companies"),
    ("/runs", "Run"),
    ("/learned", "What it learned"),
    ("/settings", "Settings"),
    ("/nowhere", "Page not found"),
)
STEP_BOXES = {
    "find": Group.FOUND,
    "score": Group.WAITING_SCORE,
    "scored": Group.SCORED,
    "ready": Group.READY,
    "applied": Group.APPLIED,
}
SKIP_REASONS = (Group.WRONG_TITLE, Group.WRONG_PLACE, Group.TOO_OLD, Group.SKIPPED_COMPANY)
OUTCOME_BOXES = {
    f"o-{group}": group
    for group in Group
    if group not in STEP_BOXES.values() and group not in SKIP_REASONS
}
OVERLAPPING_BOXES = """() => {
  const boxes = [...document.querySelectorAll('.react-flow__node:not(.react-flow__node-lane)')]
    .map((node) => [node.dataset.id, node.getBoundingClientRect()]);
  return boxes.flatMap(([id, a], index) => boxes.slice(index + 1)
    .filter(([, b]) => a.left < b.right && b.left < a.right && a.top < b.bottom && b.top < a.bottom)
    .map(([other]) => `${id} overlaps ${other}`));
}"""


@pytest.fixture(scope="module")
def browser() -> Iterator[Browser]:
    with sync_playwright() as playwright:
        launched = playwright.chromium.launch(headless=True)
        yield launched
        launched.close()


@pytest.fixture
def home(tmp_path: Path) -> Paths:
    paths = Paths(tmp_path / "home")
    paths.ensure()
    resume = tmp_path / "master.tex"
    resume.write_text("resume", encoding="utf-8")
    save(paths, samples.profile(resume))
    return paths


@contextmanager
def opened(
    browser: Browser, theme: Theme = "light", viewport: ViewportSize = DESKTOP
) -> Iterator[tuple[Page, list[str]]]:
    context = browser.new_context(viewport=viewport, color_scheme=theme)
    stored = json.dumps({"state": {"theme": theme}, "version": 0})
    context.add_init_script(f"localStorage.setItem('{THEME_KEY}', {json.dumps(stored)})")
    page = context.new_page()
    errors: list[str] = []

    def on_console(message: ConsoleMessage) -> None:
        if message.type == "error":
            errors.append(message.text)

    def on_error(error: Error) -> None:
        errors.append(str(error))

    page.on("console", on_console)
    page.on("pageerror", on_error)
    try:
        yield page, errors
    finally:
        context.close()


@contextmanager
def answered(page: Page, path: str) -> Iterator[None]:
    with page.expect_response(lambda response: response.url.endswith(path)) as reply:
        yield
    assert reply.value.ok, path


def status_of(paths: Paths, job_id: int) -> Status:
    with closing(connect(paths.database)) as db:
        record = records.find(db, job_id)
    assert record is not None
    return record.job.status


def kinds(paths: Paths, job_id: int) -> list[tuple[FeedbackKind, str]]:
    with closing(connect(paths.database)) as db:
        return [(item.kind, item.value) for item in feedback.for_job(db, job_id)]


@pytest.mark.parametrize(("theme", "viewport"), [("light", DESKTOP), ("dark", PHONE)])
def test_every_page_renders_without_errors_or_sideways_scrolling(
    browser: Browser, home: Paths, theme: Theme, viewport: ViewportSize
) -> None:
    with closing(connect(home.database)) as db:
        seed_every_group(db, NOW)
    with running(home) as server, opened(browser, theme, viewport) as (page, errors):
        for path, title in PAGES:
            page.goto(server.url + path)
            heading = page.get_by_role("heading", level=1, name=title, exact=True)
            heading.wait_for(state="attached")
            overflow = page.evaluate("document.documentElement.scrollWidth - window.innerWidth")
            assert overflow <= 0, path
            assert page.evaluate("document.documentElement.dataset.theme") == theme
        assert errors == []


def test_each_workflow_box_opens_exactly_the_jobs_it_counts(browser: Browser, home: Paths) -> None:
    with closing(connect(home.database)) as db:
        seed_every_group(db, NOW)
    with running(home) as server, opened(browser) as (page, errors):
        counts = get(server, "/api/workflow")[1]["groups"]
        page.goto(server.url + "/workflow")
        page.locator('.react-flow__node[data-id="applied"]').wait_for()
        assert page.evaluate(OVERLAPPING_BOXES) == []
        for node, group in (STEP_BOXES | OUTCOME_BOXES).items():
            page.locator(f'.react-flow__node[data-id="{node}"]').click()
            link = page.get_by_role("link", name=f"See all {counts[group]}", exact=True)
            expect(link).to_have_attribute("href", f"/jobs?group={group}")
            if group is Group.SKIPPED:
                reasons = page.get_by_role("list", name="Why they were skipped")
                for reason in SKIP_REASONS:
                    link = reasons.locator(f'a[href="/jobs?group={reason}"]')
                    expect(link).to_contain_text(str(counts[reason]))
            page.get_by_role("button", name="Close", exact=True).click()
        for group in Group:
            page.goto(server.url + f"/jobs?group={group}")
            expect(page.locator('main a[href^="/jobs/"]')).to_have_count(len(ids_in(group)))
        assert errors == []


def test_the_job_page_buttons_mark_it_applied_or_dismiss_it(browser: Browser, home: Paths) -> None:
    picks = [samples.job(external_id=str(n), company=f"Co {n}") for n in range(2)]
    with closing(connect(home.database)) as db:
        jobs.add_many(db, picks, NOW)
        for job_id in range(1, 3):
            jobs.record_attempt(db, job_id, AttemptRecord(Status.READY, NOW, "filled", (), None))
    with running(home) as server, opened(browser) as (page, errors):
        page.goto(server.url + "/jobs/1")
        with answered(page, "/api/jobs/1/finished"):
            page.get_by_role("button", name="I submitted it", exact=True).click()
        page.goto(server.url + "/jobs/2")
        page.get_by_role("button", name="Dismiss", exact=True).click()
        with answered(page, "/api/jobs/2/dismiss"):
            page.get_by_role("dialog").get_by_role("button", name="Dismiss", exact=True).click()
        assert errors == []
    assert [status_of(home, 1), status_of(home, 2)] == [Status.APPLIED, Status.DISMISSED]
    assert kinds(home, 1) == [(FeedbackKind.FINISHED, "")]
    assert kinds(home, 2) == [(FeedbackKind.DISMISS, "wrong role")]


def test_the_jobs_grid_moves_by_keys_filters_and_dismisses_many(
    browser: Browser, home: Paths
) -> None:
    picks = [samples.job(external_id=str(n), company=f"Co {n + 1}") for n in range(4)]
    with closing(connect(home.database)) as db:
        jobs.add_many(db, picks, NOW)
        for job_id in range(1, 4):
            at = NOW + timedelta(minutes=job_id)
            jobs.record_attempt(db, job_id, AttemptRecord(Status.READY, at, "filled", (), None))
        jobs.set_status(db, 4, StatusChange(Status.APPLIED, NOW, "sent"))
    with running(home) as server, opened(browser) as (page, errors):
        page.goto(server.url + "/jobs")
        expect(page.locator("main tbody tr")).to_have_count(4)
        page.locator('main a[href="/jobs/3"]').focus()
        page.keyboard.press("x")
        page.keyboard.press("ArrowDown")
        expect(page.locator('main a[href="/jobs/2"]')).to_be_focused()
        page.keyboard.press("x")
        page.keyboard.press("ArrowDown")
        page.keyboard.press("ArrowDown")
        page.keyboard.press("x")
        applied = page.get_by_role("checkbox", name="Select Frontend Engineer at Co 4")
        expect(applied).to_be_disabled()
        bar = page.get_by_role("toolbar", name="Selected jobs")
        expect(bar).to_contain_text("2 jobs selected")
        bar.get_by_role("button", name="Dismiss", exact=True).click()
        with answered(page, "/api/jobs/dismiss"):
            page.get_by_role("dialog").get_by_role("button", name="Dismiss", exact=True).click()
        expect(bar).to_have_count(0)
        page.get_by_role("button", name="Filter by company").click()
        page.get_by_role("searchbox", name="Company contains").fill("co 1")
        expect(page.locator("main tbody tr")).to_have_count(1)
        expect(page.get_by_role("link", name="Remove filter Company: co 1")).to_be_visible()
        assert errors == []
    assert [status_of(home, job_id) for job_id in range(1, 5)] == [
        Status.READY,
        Status.DISMISSED,
        Status.DISMISSED,
        Status.APPLIED,
    ]
    assert kinds(home, 2) == kinds(home, 3) == [(FeedbackKind.DISMISS, "wrong role")]


def test_the_dismiss_reasons_open_above_the_dialog(browser: Browser, home: Paths) -> None:
    with closing(connect(home.database)) as db:
        jobs.add_many(db, [samples.job()], NOW)
        jobs.record_attempt(db, 1, AttemptRecord(Status.READY, NOW, "tailored", (), None))
    with running(home) as server, opened(browser) as (page, errors):
        page.goto(server.url + "/jobs/1")
        page.get_by_role("button", name="Dismiss", exact=True).click()
        trigger = page.get_by_role("dialog").get_by_role("combobox")
        trigger.click()
        choice = page.get_by_role("option", name="salary", exact=True)
        choice.wait_for()
        expect(page.get_by_role("option", name="job is closed", exact=True)).to_be_visible()
        box, below = choice.bounding_box(), trigger.bounding_box()
        assert box is not None
        assert below is not None
        assert box["y"] >= below["y"] + below["height"]
        x, y = box["x"] + box["width"] / 2, box["y"] + box["height"] / 2
        on_top = page.evaluate(
            "([x, y]) => document.elementFromPoint(x, y)?.closest('[role=option]')?.textContent",
            [x, y],
        )
        assert on_top == "salary"
        choice.click()
        with answered(page, "/api/jobs/1/dismiss"):
            page.get_by_role("dialog").get_by_role("button", name="Dismiss", exact=True).click()
        assert errors == []
    assert kinds(home, 1) == [(FeedbackKind.DISMISS, "salary")]


def test_the_back_link_returns_to_where_you_opened_the_job(browser: Browser, home: Paths) -> None:
    with closing(connect(home.database)) as db:
        seed_every_group(db, NOW)
    with running(home) as server, opened(browser) as (page, errors):
        page.goto(server.url + "/")
        page.locator('main a[href="/jobs/9"]').first.click()
        back = page.get_by_role("link", name="Home", exact=True).and_(page.locator("main a"))
        back.click()
        expect(page).to_have_url(server.url + "/")
        page.goto(server.url + "/jobs?group=ready")
        page.locator('main a[href="/jobs/9"]').first.click()
        page.locator("main").get_by_role("link", name="Career jobs", exact=True).click()
        expect(page).to_have_url(server.url + "/jobs?group=ready")
        page.goto(server.url + "/jobs/9")
        page.locator("main").get_by_role("link", name="Career jobs", exact=True).click()
        expect(page).to_have_url(server.url + "/jobs")
        assert errors == []


SETTINGS_TABS = {
    "Profile": ("About you", "Work rights", "Personal details", "Other true facts"),
    "Job search": ("Job search", "Where you'll work", "Pay and notice"),
    "Applying": ("Form answers", "Runs and limits"),
    "Automation": ("Automatic runs",),
    "Resume and extension": ("Resume", "Chrome extension"),
}


def test_every_setting_is_changed_from_the_settings_page(
    browser: Browser, home: Paths, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    agents = tmp_path / "agents"
    monkeypatch.setattr(automatic, "agents", lambda: agents)
    monkeypatch.setattr(automatic, "runner", lambda _arguments: 0)
    monkeypatch.setattr(automatic, "supported", lambda: True)
    with running(home) as server, opened(browser) as (page, errors):
        page.goto(server.url + "/settings")
        tabs = page.get_by_role("tablist", name="Settings")
        for tab, titles in SETTINGS_TABS.items():
            tabs.get_by_role("tab", name=tab, exact=True).click()
            for title in titles:
                heading = page.get_by_role("heading", level=2, name=title, exact=True)
                expect(heading).to_be_visible()
        tabs.get_by_role("tab", name="Profile", exact=True).click()
        page.get_by_label("Years of experience").fill("3.5")
        tabs.get_by_role("tab", name="Applying", exact=True).click()
        page.get_by_label("Jobs to get ready each run").fill("12")
        page.get_by_role("combobox", name="Write a cover letter").click()
        page.get_by_role("option", name="Never", exact=True).click()
        with answered(page, "/api/settings"):
            page.get_by_role("button", name="Save settings").click()
        tabs.get_by_role("tab", name="Automation", exact=True).click()
        page.get_by_role("switch").click()
        expect(page.get_by_text("On, every 3 h")).to_be_visible()
        page.goto(server.url + "/runs")
        expect(page.get_by_label("How many jobs")).to_have_value("12")
        assert errors == []
    saved = load(home)
    assert saved.settings.jobs_per_run == 12
    assert saved.years_experience == 3.5
    assert saved.cover_letter == "never"
    assert schedule.plist_path(agents).is_file()


def test_the_learned_list_lines_up_with_its_heading(browser: Browser, home: Paths) -> None:
    with closing(connect(home.database)) as db:
        for text in ("no staffing agencies", "Pune is fine"):
            rules.add(db, rules.NewRule(rules.RuleKind.RULE, text, rules.RuleState.ACTIVE, NOW))
    wide = ViewportSize(width=1800, height=900)
    with running(home) as server, opened(browser, viewport=wide) as (page, errors):
        page.goto(server.url + "/learned")
        item = page.get_by_text("no staffing agencies", exact=True)
        item.wait_for()
        heading = page.get_by_role("heading", level=1).bounding_box()
        row = page.locator("main li").first.bounding_box()
        assert heading is not None
        assert row is not None
        assert abs(row["x"] - heading["x"]) <= 8
        assert errors == []


def test_the_workflow_legend_stays_on_one_line_during_a_run(browser: Browser, home: Paths) -> None:
    def live(route: Route) -> None:
        answer = route.fetch().json()
        answer["run"]["running"] = True
        route.fulfill(json=answer)

    with running(home) as server, opened(browser) as (page, errors):
        page.route("**/api/summary", live)
        page.goto(server.url + "/workflow")
        legend = page.get_by_label("How to read the map")
        expect(legend).to_contain_text("Live: a run is going")
        box = legend.bounding_box()
        assert box is not None
        assert box["height"] < 40
        assert errors == []


def test_the_all_chip_shows_skipped_jobs_too(browser: Browser, home: Paths) -> None:
    with closing(connect(home.database)) as db:
        seed_every_group(db, NOW)
    with running(home) as server, opened(browser) as (page, errors):
        total = get(server, "/api/summary")[1]["total"]
        page.goto(server.url + "/jobs")
        chips = page.get_by_role("navigation", name="Filter by status")
        chips.get_by_role("link", name=re.compile(r"^All ")).click()
        expect(page).to_have_url(re.compile(r"show=all"))
        expect(page.get_by_text(f"{total} jobs", exact=True)).to_be_visible()
        expect(page.locator("main").get_by_text("Skipped", exact=True).first).to_be_visible()
        assert errors == []


def test_row_checkboxes_scroll_under_the_table_header(browser: Browser, home: Paths) -> None:
    many = [
        replace(samples.job(external_id=f"greenhouse/x/{n}"), title=f"Role {n}") for n in range(40)
    ]
    with closing(connect(home.database)) as db:
        jobs.add_many(db, many, NOW)
    with running(home) as server, opened(browser) as (page, errors):
        page.goto(server.url + "/jobs")
        header = page.locator("thead th").first
        header.wait_for()
        page.locator("tbody tr").nth(30).scroll_into_view_if_needed()
        box = header.bounding_box()
        assert box is not None
        x, y = box["x"] + box["width"] / 2, box["y"] + box["height"] / 2
        on_top = page.evaluate(
            "([x, y]) => document.elementFromPoint(x, y)?.closest('thead, tbody')?.tagName",
            [x, y],
        )
        assert on_top == "THEAD"
        scroller = page.locator("tbody").locator("xpath=ancestor::div[1]")
        assert scroller.evaluate("el => el.scrollTop") > 0
        assert scroller.evaluate("el => el.offsetWidth - el.clientWidth - 2") == 0
        assert scroller.evaluate("el => getComputedStyle(el).scrollbarWidth") == "none"
        assert errors == []


def test_score_from_the_table_shows_a_spinner_then_the_score(
    browser: Browser, home: Paths, monkeypatch: pytest.MonkeyPatch
) -> None:
    asked: list[list[int]] = []
    monkeypatch.setattr(runs, "score", lambda _paths, job_ids: asked.append(job_ids))
    monkeypatch.setattr(runs, "scoring_now", lambda: [job for ids in asked for job in ids])
    senior = replace(samples.job(external_id="greenhouse/x/1"), title="Senior Frontend Engineer")
    with closing(connect(home.database)) as db:
        jobs.add_outside_search(db, [(senior, WRONG_TITLE_NOTE)], NOW)
    with running(home) as server, opened(browser) as (page, errors):
        page.goto(server.url + "/jobs?show=all")
        page.get_by_role("button", name="Score Senior Frontend Engineer at Northwind").click()
        expect(page.locator("tbody").get_by_role("status")).to_have_text("Scoring")
        with closing(connect(home.database)) as db:
            jobs.save_score(db, 1, jobs.ScoreUpdate(86, Status.SCORED, NOW, "strong React fit"))
        asked.clear()
        page.reload()
        expect(page.locator("tbody").get_by_text("86", exact=True)).to_be_visible()
        assert errors == []


def test_a_column_filter_stays_open_while_you_type(browser: Browser, home: Paths) -> None:
    with closing(connect(home.database)) as db:
        seed_every_group(db, NOW)
    with running(home) as server, opened(browser) as (page, errors):
        page.goto(server.url + "/jobs?show=all")
        page.get_by_role("button", name="Filter by location").click()
        box = page.get_by_role("searchbox", name="Location contains")
        for letter in "zqx":
            box.press_sequentially(letter)
            page.wait_for_timeout(600)
            expect(box).to_be_visible()
            expect(box).to_be_focused()
        expect(page).to_have_url(re.compile(r"location=zqx"))
        expect(page.get_by_text("No jobs match these filters.")).to_be_visible()
        box.fill("")
        page.wait_for_timeout(600)
        expect(page.locator("tbody tr").first).not_to_have_text("No jobs match these filters.")
        assert errors == []


def test_the_clock_setting_changes_every_time_shown(browser: Browser, home: Paths) -> None:
    home.runs.mkdir(parents=True, exist_ok=True)
    log = home.runs / "20261027-170000-000000.log"
    log.write_text("Automatic run\n", encoding="utf-8")
    afternoon = datetime(2026, 10, 27, 17, 18).timestamp()
    os.utime(log, (afternoon, afternoon))
    with running(home) as server, opened(browser) as (page, errors):
        page.goto(server.url + "/settings?tab=automation")
        clock = page.get_by_role("combobox", name="Clock")
        clock.click()
        page.get_by_role("option", name="24-hour (17:18)").click()
        page.goto(server.url + "/runs")
        recent = page.get_by_role("region", name="Recent runs")
        expect(recent).to_contain_text("17:18")
        expect(recent).to_contain_text("Automatic")
        page.goto(server.url + "/settings?tab=automation")
        page.get_by_role("combobox", name="Clock").click()
        page.get_by_role("option", name="12-hour (5:18 pm)").click()
        page.goto(server.url + "/runs")
        expect(page.get_by_role("region", name="Recent runs")).to_contain_text("05:18")
        assert errors == []


def test_how_long_ago_keeps_counting_while_the_page_stays_open(
    browser: Browser, home: Paths
) -> None:
    home.runs.mkdir(parents=True, exist_ok=True)
    log = home.runs / "20261027-170000-000000.log"
    log.write_text("Automatic run\n", encoding="utf-8")
    finished = (datetime.now(UTC) - timedelta(minutes=10)).timestamp()
    os.utime(log, (finished, finished))
    with running(home) as server, opened(browser) as (page, errors):
        page.clock.install()
        page.goto(server.url + "/runs")
        recent = page.get_by_role("region", name="Recent runs")
        expect(recent).to_contain_text(re.compile(r"10 ?m(in)? ago"))
        page.clock.fast_forward("05:00")
        expect(recent).to_contain_text(re.compile(r"15 ?m(in)? ago"))
        assert errors == []


def test_an_empty_site_table_spans_exactly_its_own_columns(browser: Browser, home: Paths) -> None:
    with running(home) as server, opened(browser) as (page, errors):
        page.goto(server.url + "/sites/wellfound")
        empty = page.locator("tbody td[colspan]")
        empty.wait_for()
        headers = page.locator("thead th")
        assert empty.get_attribute("colspan") == str(headers.count())
        assert page.get_by_role("columnheader", name="Score").count() == 0
        page.wait_for_load_state("networkidle")
        assert errors == []


def test_a_wellfound_job_goes_back_to_the_wellfound_tab(browser: Browser, home: Paths) -> None:
    with closing(connect(home.database)) as db:
        jobs.add_ready(db, [samples.job(Source.WELLFOUND, "9")], NOW, WELLFOUND_NOTE)
    with running(home) as server, opened(browser) as (page, errors):
        page.goto(server.url + "/sites/wellfound")
        page.locator('main a[href="/jobs/1"]').first.click()
        page.locator("main").get_by_role("link", name="Wellfound jobs", exact=True).click()
        expect(page).to_have_url(server.url + "/sites/wellfound")
        page.goto(server.url + "/jobs/1")
        page.locator("main").get_by_role("link", name="Wellfound jobs", exact=True).click()
        expect(page).to_have_url(server.url + "/sites/wellfound")
        page.wait_for_load_state("networkidle")
        assert errors == []


def test_the_sidebar_counts_new_jobs_per_tab_until_you_open_it(
    browser: Browser, home: Paths
) -> None:
    with running(home) as server, opened(browser) as (page, errors):
        page.goto(server.url + "/runs")
        nav = page.get_by_role("navigation", name="Main")
        nav.get_by_role("link", name="Wellfound").wait_for()
        page.wait_for_load_state("networkidle")
        found = datetime.now(UTC)
        with closing(connect(home.database)) as db:
            jobs.add_many(db, [samples.job(external_id=f"n{n}") for n in range(2)], found)
            listed = [samples.job(Source.WELLFOUND, str(n)) for n in range(3)]
            jobs.add_ready(db, listed, found, WELLFOUND_NOTE)
        page.reload()
        expect(nav.get_by_label("2 new")).to_be_visible()
        expect(nav.get_by_label("3 new")).to_be_visible()
        nav.get_by_role("link", name="Wellfound").click()
        expect(page).to_have_url(server.url + "/sites/wellfound")
        expect(nav.get_by_label("3 new")).to_have_count(0)
        nav.get_by_role("link", name="Run").click()
        expect(nav.get_by_label("2 new")).to_be_visible()
        expect(nav.get_by_label("3 new")).to_have_count(0)
        page.wait_for_load_state("networkidle")
        assert errors == []
