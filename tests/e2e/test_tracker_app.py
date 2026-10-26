import json
import re
from collections.abc import Iterator
from contextlib import closing, contextmanager
from datetime import UTC, datetime
from importlib import resources
from pathlib import Path
from typing import Literal

import pytest
from playwright.sync_api import (
    Browser,
    ConsoleMessage,
    Error,
    Page,
    ViewportSize,
    expect,
    sync_playwright,
)

from satyaapply.core.models import Status
from satyaapply.core.paths import Paths
from satyaapply.core.profile import save
from satyaapply.store import feedback, jobs, records
from satyaapply.store.db import connect
from satyaapply.store.feedback import FeedbackKind
from satyaapply.store.groups import Group
from satyaapply.store.jobs import AttemptRecord
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
    ("/", re.compile(r"^Good (morning|afternoon|evening)$")),
    ("/board", "Board"),
    ("/workflow", "Workflow"),
    ("/jobs", "All jobs"),
    ("/jobs?group=ready", "Waiting for your OK"),
    ("/jobs/13", "Frontend Engineer"),
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
    "approved": Group.APPROVED,
    "applied": Group.APPLIED,
}
OUTCOME_BOXES = {f"o-{group}": group for group in Group if group not in STEP_BOXES.values()}


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
        for node, group in (STEP_BOXES | OUTCOME_BOXES).items():
            page.locator(f'.react-flow__node[data-id="{node}"]').click()
            link = page.get_by_role("link", name=f"See all {counts[group]}", exact=True)
            expect(link).to_have_attribute("href", f"/jobs?group={group}")
            page.get_by_role("button", name="Close", exact=True).click()
        for group in Group:
            page.goto(server.url + f"/jobs?group={group}")
            expect(page.locator('main a[href^="/jobs/"]')).to_have_count(len(ids_in(group)))
        assert errors == []


def test_dragging_on_the_board_does_what_the_job_page_buttons_do(
    browser: Browser, home: Paths
) -> None:
    picks = [samples.job(external_id=str(n), company=f"Co {n}") for n in range(4)]
    with closing(connect(home.database)) as db:
        jobs.add_many(db, picks, NOW)
        for job_id in range(1, 5):
            jobs.record_attempt(db, job_id, AttemptRecord(Status.READY, NOW, "filled", (), None))
    with running(home) as server, opened(browser) as (page, errors):
        page.goto(server.url + "/board")
        approved = page.get_by_role("region", name="Approved", exact=True)
        with answered(page, "/api/jobs/1/approve"):
            page.locator('a[href="/jobs/1"]').drag_to(approved)
        page.goto(server.url + "/jobs/2")
        with answered(page, "/api/jobs/2/approve"):
            page.get_by_role("button", name="Approve", exact=True).click()
        page.goto(server.url + "/board")
        page.locator('a[href="/jobs/3"]').hover()
        page.mouse.down()
        page.mouse.move(0, 0, steps=4)
        page.get_by_role("region", name="Dismiss", exact=True).hover()
        page.mouse.up()
        with answered(page, "/api/jobs/3/dismiss"):
            page.get_by_role("dialog").get_by_role("button", name="Dismiss", exact=True).click()
        page.goto(server.url + "/jobs/4")
        page.get_by_role("button", name="Dismiss", exact=True).click()
        with answered(page, "/api/jobs/4/dismiss"):
            page.get_by_role("dialog").get_by_role("button", name="Dismiss", exact=True).click()
        assert errors == []
    assert [status_of(home, job_id) for job_id in range(1, 5)] == [
        Status.APPROVED,
        Status.APPROVED,
        Status.DISMISSED,
        Status.DISMISSED,
    ]
    assert kinds(home, 1) == kinds(home, 2) == [(FeedbackKind.APPROVE, "clean")]
    assert kinds(home, 3) == kinds(home, 4) == [(FeedbackKind.DISMISS, "wrong role")]
