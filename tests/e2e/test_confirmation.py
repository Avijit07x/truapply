from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path

import pytest
from playwright.sync_api import Route, expect

from satyaapply.core.models import Job, Source, Status
from satyaapply.store import records
from satyaapply.store.db import connect
from tests.live.test_extension_live import BUILT, Guard, chrome_with_extension, seeded
from tests.unit.tracker_api import running

pytestmark = [
    pytest.mark.e2e,
    pytest.mark.skipif(not BUILT, reason="build the extension first: cd web && npm run build"),
]

NOW = datetime(2026, 10, 27, 12, 0, tzinfo=UTC)
FORM = "https://job-boards.greenhouse.io/embed/job_app?for=northwind&token=7001"
THANKS = "https://job-boards.greenhouse.io/embed/job_app/confirmation?for=northwind&token=7001"
THANKS_PAGE = """<!doctype html><html><body><main>
<h1>Thank you for applying.</h1>
<p>Your application has been received. If there is a fit, someone will be getting back to you.</p>
<a href="#">View more jobs at Northwind</a> <a href="#">Back to job post</a>
</main></body></html>"""
JOB = Job(
    Source.CAREER_PAGES,
    "greenhouse/northwind/7001",
    "https://job-boards.greenhouse.io/northwind/jobs/7001",
    "Northwind",
    "Frontend Engineer",
    apply_url=FORM,
)


def thanks(route: Route) -> None:
    route.fulfill(body=THANKS_PAGE, content_type="text/html; charset=utf-8")


def test_a_thank_you_page_on_its_own_address_marks_the_job_applied(tmp_path: Path) -> None:
    paths = seeded(tmp_path, [JOB])
    with (
        running(paths) as server,
        chrome_with_extension(server.server_address[1], Guard()) as context,
    ):
        context.route(THANKS, thanks)
        page = context.new_page()
        page.goto(THANKS)
        expect(page.locator("satyaapply-panel")).to_contain_text("Saved as applied")
    with closing(connect(paths.database)) as db:
        record = records.find(db, 1)
    assert record is not None
    assert record.job.status is Status.APPLIED
