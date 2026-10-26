from collections.abc import Iterator, Sequence
from contextlib import closing
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from pathlib import Path

import pytest
from playwright.sync_api import Page, sync_playwright

from satyaapply.apply.flow import apply
from satyaapply.core.forms import Field, FormAnswers, FormContext
from satyaapply.core.models import Status
from satyaapply.core.paths import Paths
from satyaapply.store import answers, jobs
from satyaapply.store.db import connect
from satyaapply.store.jobs import StatusChange
from tests.e2e.test_form_filler import FakeAnswerer, request_for, submission
from tests.unit import samples
from tests.unit.tracker_api import post, running

pytestmark = pytest.mark.e2e

NOW = datetime(2026, 10, 25, 12, 0, tzinfo=UTC)
NOTICE = "notice period"


@dataclass
class NeverAsksNotice(FakeAnswerer):
    def __call__(self, context: FormContext, fields: Sequence[Field]) -> FormAnswers:
        asked = {answers.question_key(item.label) for item in fields}
        if NOTICE in asked:
            raise AssertionError("the AI was asked a question you already answered")
        return super().__call__(context, fields)


@pytest.fixture
def browser_page() -> Iterator[Page]:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        yield browser.new_page()
        browser.close()


def answer_on_the_tracker(paths: Paths, question: str, answer: str) -> None:
    given = {"answers": [{"question": question, "answer": answer}]}
    with running(paths) as server:
        assert post(server, "/api/jobs/1/questions", given)[0] == 200


def test_an_answer_given_on_the_tracker_fills_the_next_form(
    browser_page: Page, tmp_path: Path
) -> None:
    paths = Paths(tmp_path / "home")
    paths.ensure()
    with closing(connect(paths.database)) as db:
        jobs.add_many(db, [samples.job()], NOW)
        jobs.set_status(db, 1, StatusChange(Status.NEEDS_INPUT, NOW, "needs you"))
        answers.open_questions(db, ["Notice period *"], 1, NOW)
    answer_on_the_tracker(paths, NOTICE, "60 days")
    with closing(connect(paths.database)) as db:
        known = answers.all_answers(db)
        assert [job.id for job in jobs.next_to_apply(db, 10)] == [1]
    resume_pdf = tmp_path / "Asha_Rao_Resume.pdf"
    resume_pdf.write_bytes(b"%PDF-1.4 test resume")
    request = replace(request_for(tmp_path, resume_pdf), known=known)
    attempt = apply(browser_page, request, NeverAsksNotice())
    assert attempt.status is Status.APPLIED
    found = submission(browser_page)
    assert found is not None
    assert found["notice"] == "60 days"
