import json
import os
import re
from collections.abc import Iterator, Sequence
from contextlib import closing, contextmanager
from dataclasses import replace
from datetime import UTC, date, datetime, timedelta
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

from tests.unit import samples
from tests.unit.test_tracker_setup import DRAFT as SETUP_DRAFT
from tests.unit.tracker_api import fetch, get, ids_in, running, seed_every_group
from truapply.ai import tasks
from truapply.core import autorun
from truapply.core.documents import ResumeFormat
from truapply.core.models import Board, Source, Status
from truapply.core.notes import WELLFOUND_NOTE, WRONG_TITLE_NOTE
from truapply.core.paths import Paths
from truapply.core.profile import ResumeRef, load, save
from truapply.run.lock import run_lock
from truapply.sources import intake, lookup
from truapply.sources.ats import PollResult
from truapply.store import feedback, jobs, records, rules
from truapply.store.db import connect
from truapply.store.feedback import FeedbackKind
from truapply.store.groups import Group
from truapply.store.jobs import AttemptRecord, StatusChange
from truapply.tracker import automatic, resume_upload, runs

BUILT = resources.files("truapply.tracker").joinpath("static", "index.html").is_file()
pytestmark = [
    pytest.mark.e2e,
    pytest.mark.skipif(not BUILT, reason="build the app first: cd web && npm ci && npm run build"),
]

NOW = datetime(2026, 10, 25, 12, 0, tzinfo=UTC)
DESKTOP = ViewportSize(width=1440, height=900)
PHONE = ViewportSize(width=390, height=844)
THEME_KEY = "truapply-theme"
Theme = Literal["light", "dark"]
PAGES = (
    (
        "/",
        re.compile(r"^(You're all caught up|1 job is ready for you|\d+ jobs are ready for you)$"),
    ),
    ("/jobs", "Jobs"),
    ("/jobs/table", "All jobs"),
    ("/jobs?group=ready", "Ready for you to apply"),
    ("/jobs/9", "Frontend Engineer"),
    ("/companies", "Companies"),
    ("/runs", "Activity"),
    ("/learned", "What it learned"),
    ("/settings", "Settings"),
    ("/nowhere", "Page not found"),
)


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
    browser: Browser,
    theme: Theme = "light",
    viewport: ViewportSize = DESKTOP,
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


def test_an_unknown_page_highlights_no_sidebar_link(browser: Browser, home: Paths) -> None:
    with running(home) as server, opened(browser) as (page, _errors):
        page.goto(server.url + "/nowhere")
        page.get_by_role("heading", level=1, name="Page not found").wait_for()
        assert page.locator("nav [aria-current=page]").count() == 0
        page.goto(server.url + "/")
        assert page.locator("nav [aria-current=page]").inner_text() == "Today"


def test_each_pipeline_number_on_today_opens_the_jobs_it_counts(
    browser: Browser, home: Paths
) -> None:
    with closing(connect(home.database)) as db:
        seed_every_group(db, NOW)
    shown = (Group.FOUND, Group.NOT_A_FIT, Group.SCORED, Group.READY, Group.APPLIED)
    with running(home) as server, opened(browser) as (page, errors):
        counts = get(server, "/api/workflow")[1]["groups"]
        page.goto(server.url + "/")
        pipeline = page.get_by_role("region", name="Pipeline")
        for group in shown:
            expect(pipeline.locator(f'a[href="/jobs?group={group}"]')).to_contain_text(
                str(counts[group])
            )
        pipeline.locator(f'a[href="/jobs?group={Group.APPLIED}"]').click()
        listed = page.get_by_role("list", name="Jobs").get_by_role("button")
        expect(listed).to_have_count(len(ids_in(Group.APPLIED)))
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
        page.goto(server.url + "/jobs/table")
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
        back = page.get_by_role("link", name="Today", exact=True).and_(page.locator("main a"))
        back.click()
        expect(page).to_have_url(server.url + "/")
        page.goto(server.url + "/jobs/table?group=ready")
        page.locator('main a[href="/jobs/9"]').first.click()
        page.locator("main").get_by_role("link", name="All jobs", exact=True).click()
        expect(page).to_have_url(server.url + "/jobs/table?group=ready")
        page.goto(server.url + "/jobs/9")
        page.locator("main").get_by_role("link", name="Jobs", exact=True).click()
        expect(page).to_have_url(server.url + "/jobs")
        assert errors == []


SETTINGS_TABS = {
    "Profile": ("About you", "Work rights", "Personal details", "Other true facts"),
    "Job search": ("Job search", "Where you'll work", "Pay and notice"),
    "Applying": ("Form answers", "Your resume", "Runs and limits"),
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
        page.get_by_label("Years of experience", exact=True).fill("3.5")
        tabs.get_by_role("tab", name="Applying", exact=True).click()
        page.get_by_label("Jobs to get ready each run", exact=True).fill("12")
        page.get_by_role("combobox", name="Write a cover letter").click()
        page.get_by_role("option", name="Never", exact=True).click()
        page.get_by_role("combobox", name="For each job").click()
        page.get_by_role("option", name="Always send my resume as it is").click()
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
    assert not saved.settings.tailor_resume
    assert autorun.installed(agents) is not None


def test_an_info_button_explains_its_setting(browser: Browser, home: Paths) -> None:
    with running(home) as server, opened(browser) as (page, errors):
        page.goto(server.url + "/settings")
        page.get_by_role("tablist", name="Settings").get_by_role("tab", name="Job search").click()
        page.get_by_role("button", name="About Oldest job to consider, in days").click()
        expect(page.get_by_text("Jobs with no posting date are always kept.")).to_be_visible()
        expect(page.get_by_label("Oldest job to consider, in days", exact=True)).to_have_value("30")
        assert errors == []


def test_pasted_company_names_are_looked_up_and_added(
    browser: Browser, home: Paths, monkeypatch: pytest.MonkeyPatch
) -> None:
    def polled(tried: Sequence[Board]) -> PollResult:
        hit = [board for board in tried if board.key == "greenhouse/northwind"]
        found = [samples.job(external_id=f"{board.key}/7") for board in hit]
        return PollResult([replace(job, location="Bengaluru") for job in found], hit, [], [])

    monkeypatch.setattr(lookup, "poll", polled)
    monkeypatch.setattr(intake, "poll", polled)
    with running(home) as server, opened(browser) as (page, errors):
        page.goto(server.url + "/companies")
        page.get_by_role("button", name="Add companies").click()
        page.get_by_label("Company names or websites, one per line").fill("Northwind\nNobody")
        with answered(page, "/api/boards/names"):
            page.get_by_role("button", name="Add", exact=True).click()
        expect(page.get_by_text("Added Northwind, with 1 new job for you.")).to_be_visible()
        expect(page.get_by_role("cell", name="You named it")).to_be_visible()
        assert errors == []


def test_the_learned_list_lines_up_with_the_box_above_it(browser: Browser, home: Paths) -> None:
    with closing(connect(home.database)) as db:
        for text in ("no staffing agencies", "Pune is fine"):
            rules.add(db, rules.NewRule(rules.RuleKind.RULE, text, rules.RuleState.ACTIVE, NOW))
    wide = ViewportSize(width=1800, height=900)
    with running(home) as server, opened(browser, viewport=wide) as (page, errors):
        page.goto(server.url + "/learned")
        item = page.get_by_text("no staffing agencies", exact=True)
        item.wait_for()
        box = page.get_by_role("tabpanel").locator(":scope > *").first.bounding_box()
        listed = item.locator("xpath=ancestor::ul[1]").bounding_box()
        assert box is not None
        assert listed is not None
        assert abs(listed["x"] - box["x"]) <= 1
        assert abs(listed["width"] - box["width"]) <= 1
        assert errors == []


def test_the_tab_icon_shows_a_dot_while_a_run_is_going(browser: Browser, home: Paths) -> None:
    going = {"running": True}

    def live(route: Route) -> None:
        answer = route.fetch().json()
        answer["run"]["running"] = going["running"]
        route.fulfill(json=answer)

    with running(home) as server, opened(browser) as (page, errors):
        page.route("**/api/summary", live)
        page.goto(server.url + "/")
        icon = page.locator('link[rel="icon"]')
        expect(icon).to_have_attribute("href", "/favicon-running.svg")
        assert fetch(server, "/favicon-running.svg")[0] == 200
        going["running"] = False
        page.reload()
        expect(icon).to_have_attribute("href", "/favicon.svg")
        assert errors == []


def test_the_all_chip_shows_skipped_jobs_too(browser: Browser, home: Paths) -> None:
    with closing(connect(home.database)) as db:
        seed_every_group(db, NOW)
    with running(home) as server, opened(browser) as (page, errors):
        total = get(server, "/api/summary")[1]["total"]
        page.goto(server.url + "/jobs/table")
        page.get_by_role("button", name="Filter", exact=True).click()
        page.get_by_role("group", name="Show").get_by_role(
            "button", name=re.compile(r"^All ")
        ).click()
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
        page.goto(server.url + "/jobs/table")
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
        page.goto(server.url + "/jobs/table?show=all")
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
        page.goto(server.url + "/jobs/table?show=all")
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


def test_the_sidebar_shows_a_live_run_with_its_step_time_and_latest_line(
    browser: Browser, home: Paths
) -> None:
    home.runs.mkdir(parents=True, exist_ok=True)
    started = datetime.now(UTC) - timedelta(minutes=2, seconds=5)
    log = home.runs / f"{started:%Y%m%d-%H%M%S-%f}.log"
    log.write_text(
        "Checking company career pages\nScoring 3 jobs\nScoring Frontend Engineer at Northwind\n",
        encoding="utf-8",
    )
    with run_lock(home), running(home) as server, opened(browser) as (page, errors):
        page.goto(server.url + "/")
        box = page.get_by_role("link", name=re.compile("^Running"))
        expect(box).to_contain_text(re.compile(r"2m \d\ds"))
        expect(box.locator("[aria-current=step]")).to_have_text("Scoring")
        expect(box).to_contain_text("Scoring Frontend Engineer at Northwind")
        assert errors == []


def test_an_empty_site_table_spans_exactly_its_own_columns(browser: Browser, home: Paths) -> None:
    with running(home) as server, opened(browser) as (page, errors):
        page.goto(server.url + "/sites/wellfound/table")
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
        page.goto(server.url + "/sites/wellfound/table")
        page.locator('main a[href="/jobs/1"]').first.click()
        page.locator("main").get_by_role("link", name="Wellfound jobs", exact=True).click()
        expect(page).to_have_url(server.url + "/sites/wellfound/table")
        page.goto(server.url + "/jobs/1")
        page.locator("main").get_by_role("link", name="Wellfound jobs", exact=True).click()
        expect(page).to_have_url(server.url + "/sites/wellfound")
        page.wait_for_load_state("networkidle")
        assert errors == []


def test_the_sidebar_counts_new_jobs_until_you_open_them(browser: Browser, home: Paths) -> None:
    with running(home) as server, opened(browser) as (page, errors):
        page.goto(server.url + "/runs")
        nav = page.get_by_role("navigation", name="Main")
        nav.get_by_role("link", name=re.compile(r"^Jobs")).wait_for()
        page.wait_for_load_state("networkidle")
        found = datetime.now(UTC)
        with closing(connect(home.database)) as db:
            jobs.add_many(db, [samples.job(external_id=f"n{n}") for n in range(2)], found)
            listed = [samples.job(Source.WELLFOUND, str(n)) for n in range(3)]
            jobs.add_ready(db, listed, found, WELLFOUND_NOTE)
        page.reload()
        expect(nav.get_by_label("5 new")).to_be_visible()
        page.goto(server.url + "/sites/wellfound")
        expect(nav.get_by_label("2 new")).to_be_visible()
        nav.get_by_role("link", name="Activity").click()
        expect(nav.get_by_label("2 new")).to_be_visible()
        nav.get_by_role("link", name=re.compile(r"^Jobs")).click()
        expect(page).to_have_url(server.url + "/jobs")
        expect(nav.get_by_label(re.compile(r"\d+ new"))).to_have_count(0)
        page.wait_for_load_state("networkidle")
        assert errors == []


def test_the_jobs_list_shows_the_picked_job_beside_it(browser: Browser, home: Paths) -> None:
    picks = [samples.job(external_id=str(n), company=f"Co {n + 1}") for n in range(3)]
    with closing(connect(home.database)) as db:
        jobs.add_many(db, picks, NOW)
    with running(home) as server, opened(browser) as (page, errors):
        page.goto(server.url + "/jobs")
        beside = page.get_by_role("region", name="Selected job")
        items = page.get_by_role("list", name="Jobs").get_by_role("button")
        expect(items).to_have_count(3)
        expect(beside).to_contain_text(re.compile(r"Co \d"))
        items.nth(1).click()
        picked = items.nth(1).inner_text().split("\n")[1].split(" · ")[0]
        expect(beside.get_by_text(picked).first).to_be_visible()
        page.keyboard.press("j")
        expect(items.nth(2)).to_be_focused()
        expect(items.nth(2)).to_have_attribute("aria-current", "true")
        page.get_by_role("navigation", name="Main").get_by_role("link", name="All jobs").click()
        expect(page).to_have_url(server.url + "/jobs/table")
        expect(page.locator("main tbody tr")).to_have_count(3)
        assert errors == []


def test_the_jobs_list_shows_every_site_unless_you_pick_career_pages(
    browser: Browser, home: Paths
) -> None:
    with closing(connect(home.database)) as db:
        jobs.add_many(db, [samples.job(external_id="1")], NOW)
        jobs.add_ready(db, [samples.job(Source.WELLFOUND, "9", "Globex")], NOW, WELLFOUND_NOTE)
    with running(home) as server, opened(browser) as (page, errors):
        page.goto(server.url + "/jobs")
        items = page.get_by_role("list", name="Jobs").get_by_role("button")
        expect(items).to_have_count(2)
        expect(items.filter(has_text="Globex")).to_contain_text("Wellfound")
        page.get_by_role("button", name="Filter").click()
        sites = page.get_by_role("group", name="Site")
        sites.get_by_role("button", name=re.compile("^Career pages")).click()
        expect(page).to_have_url(server.url + "/jobs?sites=career")
        expect(items).to_have_count(1)
        assert errors == []


def months_between(earlier: date, later: date) -> int:
    return (later.year - earlier.year) * 12 + later.month - earlier.month


def day_name(day: date) -> str:
    return f"{day:%B} {day.day}, {day.year}"


def test_the_table_shows_only_jobs_updated_in_the_picked_dates(
    browser: Browser, home: Paths
) -> None:
    now = datetime.now(UTC)
    with closing(connect(home.database)) as db:
        jobs.add_many(
            db, [replace(samples.job(external_id="1"), title="Old role")], now - timedelta(days=40)
        )
        jobs.add_many(db, [replace(samples.job(external_id="2"), title="Fresh role")], now)
    with running(home) as server, opened(browser) as (page, errors):
        page.goto(server.url + "/jobs/table")
        rows = page.locator("main tbody tr")
        expect(rows).to_have_count(2)
        page.get_by_role("button", name="Updated: Any time").click()
        page.get_by_role("group", name="Updated").get_by_role("button", name="Today").click()
        expect(page).to_have_url(re.compile(r"when=today"))
        expect(rows).to_have_count(1)
        expect(rows.first).to_contain_text("Fresh role")
        page.get_by_role("button", name="Updated: Today").click()
        today = now.astimezone().date()
        start, end = today - timedelta(days=45), today - timedelta(days=30)
        dates = page.get_by_role("group", name="Dates")
        for _ in range(months_between(start, today)):
            page.get_by_role("button", name="Previous month").click()
        dates.get_by_role("button", name=day_name(start), exact=True).click()
        for _ in range(months_between(start, end)):
            page.get_by_role("button", name="Next month").click()
        dates.get_by_role("button", name=day_name(end), exact=True).click()
        page.get_by_role("button", name="Show these dates").click()
        expect(rows).to_have_count(1)
        expect(rows.first).to_contain_text("Old role")
        assert errors == []


def _keep_resume(paths: Paths, _resume: object) -> tuple[ResumeRef, int]:
    master = paths.resume_dir / "master.json"
    master.write_text("{}", encoding="utf-8")
    return ResumeRef(ResumeFormat.STRUCTURED, master), 1


def _setup_without_claude(monkeypatch: pytest.MonkeyPatch, agents: Path) -> None:
    monkeypatch.setattr(tasks, "draft_profile", lambda _document: SETUP_DRAFT)
    monkeypatch.setattr(resume_upload, "as_resume", lambda _document: None)
    monkeypatch.setattr(resume_upload, "kept", _keep_resume)
    monkeypatch.setattr(automatic, "agents", lambda: agents)
    monkeypatch.setattr(automatic, "runner", lambda _arguments: 0)
    monkeypatch.setattr(automatic, "supported", lambda: True)


def test_a_new_user_sets_up_from_the_page_and_nothing_else_opens_before(
    browser: Browser, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fresh = Paths(tmp_path / "fresh")
    resume = tmp_path / "resume.pdf"
    resume.write_bytes(b"%PDF-1.4 resume")
    _setup_without_claude(monkeypatch, tmp_path / "agents")
    with running(fresh) as server, opened(browser) as (page, errors):
        page.goto(server.url + "/runs")
        expect(page).to_have_url(server.url + "/setup")
        nav = page.get_by_role("navigation", name="Main")
        expect(nav.get_by_role("link")).to_have_count(0)
        page.get_by_label("Resume file").set_input_files(resume)
        expect(page.get_by_label("Full name")).to_have_value("Asha Rao")
        page.get_by_role("button", name="Next").click()
        page.get_by_label("Citizenship").fill("India")
        visa_free = page.get_by_label("Countries you can work in without a visa")
        visa_free.fill("India")
        visa_free.press("Enter")
        page.get_by_role("radio", name="Yes", exact=True).click()
        page.get_by_role("radio", name="30 days").click()
        page.get_by_label("Lowest salary you'd accept").fill("1200000")
        page.get_by_label("Highest you'd ask for").fill("1800000")
        page.get_by_role("button", name="Next").click()
        finish = page.get_by_role("button", name="Finish setup")
        expect(finish).to_be_disabled()
        page.get_by_role("radio", name="Send it as it is").click()
        page.get_by_role("radio", name="Only when I press Run").click()
        finish.click()
        expect(page).to_have_url(server.url + "/")
        expect(nav.get_by_role("link", name="Companies")).to_be_visible()
        assert errors == []
    profile = load(fresh)
    assert (profile.citizenship, profile.notice_period) == ("India", "30 days")
    assert profile.needs_sponsorship_elsewhere
    assert not profile.settings.tailor_resume
