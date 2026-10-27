import time
from contextlib import closing
from dataclasses import replace
from pathlib import Path

import pytest
from playwright.sync_api import BrowserContext, Page, Route, Worker, expect

from satyaapply.core.models import Source
from satyaapply.core.paths import Paths
from satyaapply.core.profile import load, save
from satyaapply.store import records
from satyaapply.store.db import connect
from satyaapply.tracker import runs
from tests.live.test_extension_live import BUILT, Guard, chrome_with_extension, seeded
from tests.unit.tracker_api import running

pytestmark = [
    pytest.mark.e2e,
    pytest.mark.skipif(not BUILT, reason="build the extension first: cd web && npm run build"),
]

SAVED_SEARCH = Path(__file__).resolve().parents[1] / "fixtures" / "linkedin" / "search.html"
SEARCH = "https://www.linkedin.com/jobs/search/?currentJobId=4483608650&keywords=frontend"
ADDED_TIMEOUT_MS = 60_000


def saved_page(route: Route) -> None:
    route.fulfill(path=SAVED_SEARCH, content_type="text/html; charset=utf-8")


def test_a_page_of_linkedin_jobs_goes_into_the_tracker(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    started: list[runs.Choice] = []
    monkeypatch.setattr(runs, "start", lambda _paths, choice: started.append(choice))
    paths = seeded(tmp_path, [])
    with (
        running(paths) as server,
        chrome_with_extension(server.server_address[1], Guard()) as context,
    ):
        context.route("https://www.linkedin.com/**", saved_page)
        page = context.new_page()
        page.goto(SEARCH)
        page.get_by_role("button", name="Add 3 jobs to SatyaApply").click()
        panel = page.locator("satyaapply-panel")
        expect(panel).to_contain_text("Added 3 new jobs", timeout=ADDED_TIMEOUT_MS)
    with closing(connect(paths.database)) as db:
        added = [record.job for record in (records.find(db, n) for n in (1, 2, 3)) if record]
    assert [job.source for job in added] == [Source.LINKEDIN] * 3
    assert [job.external_id for job in added] == ["4483608650", "4484015176", "4481458465"]
    assert [job.title for job in added] == [
        "Full Stack Engineer",
        "Product Engineer \u2013 UX & Frontend",
        "Salesforce UI Developer",
    ]
    assert [job.company for job in added] == ["GROVEDA", "thinkbridge", "Deloitte"]
    assert added[0].location == "Ahmedabad (On-site)"
    assert "Groveda" in added[0].description
    assert added[0].url == "https://www.linkedin.com/jobs/view/4483608650/"
    assert len(started) == 1


LAST_ROUND = "chrome.storage.local.get('linkedinLastRound').then(JSON.stringify)"
AWAKE_EVERY_S = 1


def keep_awake(worker: Worker) -> None:
    time.sleep(AWAKE_EVERY_S)
    worker.evaluate("0")


def reading_on(paths: Paths) -> None:
    profile = load(paths)
    chosen = replace(profile.settings, linkedin_reading=True)
    save(paths, replace(profile, settings=chosen))


def linkedin_tabs(context: BrowserContext) -> list[Page]:
    return [page for page in context.pages if "linkedin.com" in page.url]


def test_linkedin_jobs_are_read_on_their_own_when_turned_on(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(runs, "start", lambda _paths, _choice: None)
    paths = seeded(tmp_path, [])
    reading_on(paths)
    with (
        running(paths) as server,
        chrome_with_extension(server.server_address[1], Guard()) as context,
    ):
        context.route("https://www.linkedin.com/**", saved_page)
        worker = context.service_workers[0]
        worker.evaluate("chrome.alarms.create('linkedin-read', {when: Date.now() + 100})")
        deadline = time.monotonic() + ADDED_TIMEOUT_MS / 1000
        while time.monotonic() < deadline and (count(paths) < 3 or linkedin_tabs(context)):
            keep_awake(worker)
        assert count(paths) == 3
        assert linkedin_tabs(context) == []


def test_nothing_is_read_while_it_is_off(tmp_path: Path) -> None:
    paths = seeded(tmp_path, [])
    with (
        running(paths) as server,
        chrome_with_extension(server.server_address[1], Guard()) as context,
    ):
        context.route("https://www.linkedin.com/**", saved_page)
        worker = context.service_workers[0]
        worker.evaluate("chrome.alarms.create('linkedin-read', {when: Date.now() + 100})")
        for _ in range(3):
            keep_awake(worker)
        assert linkedin_tabs(context) == []
        assert "reading is off" in worker.evaluate(LAST_ROUND)
    assert count(paths) == 0


def count(paths: Paths) -> int:
    with closing(connect(paths.database)) as db:
        found: int = db.execute("select count(*) from jobs").fetchone()[0]
    return found
