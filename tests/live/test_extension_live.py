import json
import logging
import re
import shutil
import time
from collections.abc import Callable, Iterator, Sequence
from contextlib import closing, contextmanager, suppress
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime, timedelta
from importlib import resources
from pathlib import Path

import pytest
from playwright.sync_api import BrowserContext, Error, Page, Request, Route, sync_playwright

from satyaapply.ai.replies import Posting
from satyaapply.browser.fetch import fetch_json
from satyaapply.core.forms import RESUME_FILE, Answer, Field, FieldKind, FormAnswers, FormContext
from satyaapply.core.models import Ats, Board, Job, Status
from satyaapply.core.notes import UNCONFIRMED_NOTE
from satyaapply.core.paths import Paths
from satyaapply.core.profile import load, save
from satyaapply.sources.ats import poll
from satyaapply.sources.discover import shared_boards
from satyaapply.sources.text import items, mapping, text
from satyaapply.store import autosend, jobs, records
from satyaapply.store.db import connect
from satyaapply.store.jobs import AttemptRecord
from satyaapply.tracker import extension
from tests.unit import samples
from tests.unit.tracker_api import running

BUILT_FOLDER = str(resources.files("satyaapply").joinpath("extension"))
BUILT = (Path(BUILT_FOLDER) / "manifest.json").is_file()
pytestmark = [
    pytest.mark.network,
    pytest.mark.e2e,
    pytest.mark.skipif(not BUILT, reason="build the extension first: cd web && npm run build"),
]

NOW = datetime(2026, 10, 27, 12, 0, tzinfo=UTC)
JOBS_PER_SITE = 10
BOARDS_TRIED = 40
RESUME_NAME = "Asha_Rao_Resume.pdf"
FILLED_TIMEOUT_MS = 90_000
STAYS_MS = 5000
HOME = "India"
MOST_LIST_PX = 200
ANSWER_SAVED = "op=ApiSetFormValue"
FILLING = "/answers"
READS = frozenset({"GET", "HEAD", "OPTIONS"})
LOCAL = re.compile(r"^http://127\.0\.0\.1[:/]")
GRAPHQL_QUERY = re.compile(r'"query"\s*:\s*"\s*query\b')
SUBMISSION = re.compile(
    r"(greenhouse\.io|lever\.co)/\S*(applications?|apply)\b|ApiSubmit|/submit", re.IGNORECASE
)
CONSENT = re.compile(
    r"\b(i agree|agree to|consent|privacy|terms|acknowledge|i confirm|i certify|i declare|i attest"
    r"|i hereby)",
    re.IGNORECASE,
)
ANSWERS = {
    FieldKind.TEXT: "Test answer",
    FieldKind.EMAIL: "asha.rao@example.com",
    FieldKind.TEL: "+91 90000 00000",
    FieldKind.NUMBER: "3",
    FieldKind.URL: "https://github.com/asharao",
    FieldKind.DATE: "2026-11-02",
    FieldKind.TEXTAREA: "A short test answer.",
}


SEARCHED = (
    (re.compile(r"city|location", re.IGNORECASE), "Bengaluru"),
    (re.compile(r"school|university|college", re.IGNORECASE), "University of Mumbai"),
    (re.compile(r"degree", re.IGNORECASE), "Bachelor's Degree"),
    (re.compile(r"discipline|major|field of study", re.IGNORECASE), "Computer Science"),
)


def every_answer(_context: FormContext, fields: Sequence[Field]) -> FormAnswers:
    def value(item: Field) -> str:
        if item.kind is FieldKind.FILE:
            return RESUME_FILE
        if item.options:
            return next((option for option in item.options if HOME in option), item.options[0])
        searched = next((text for label, text in SEARCHED if label.search(item.label)), None)
        return searched or ANSWERS.get(item.kind, "India")

    found = tuple(Answer(item.id, value(item), reusable=False, guessed=False) for item in fields)
    return FormAnswers(found, (), None, None, None)


@dataclass
class Guard:
    blocked: list[str] = field(default_factory=list)

    def check(self, route: Route, request: Request) -> None:
        body = request.post_data or ""
        if LOCAL.match(request.url) and FILLING in request.url:
            self.blocked.append(f"MARK {request.url} filling starts")
        if request.method in READS or LOCAL.match(request.url) or GRAPHQL_QUERY.search(body):
            route.continue_()
            return
        self.blocked.append(f"{request.method} {request.url} {body[:20_000]}")
        with suppress(Error, TypeError):
            route.abort()


def real_jobs(ats: Ats) -> list[Job]:
    boards = [board for board in shared_boards() if board.ats is ats][:BOARDS_TRIED]
    picked: dict[str, Job] = {}
    for job in poll(boards).jobs:
        picked.setdefault(job.company, job)
    return list(picked.values())[:JOBS_PER_SITE]


def seeded(tmp_path: Path, found: Sequence[Job]) -> Paths:
    paths = Paths(tmp_path / "home")
    paths.ensure()
    master = tmp_path / "master.tex"
    master.write_text("\\begin{document}Asha Rao, React\\end{document}", encoding="utf-8")
    save(paths, samples.profile(master))
    pdf = paths.resumes / RESUME_NAME
    pdf.parent.mkdir(parents=True, exist_ok=True)
    pdf.write_bytes(b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n")
    with closing(connect(paths.database)) as db:
        jobs.add_many(db, found, NOW)
        for job_id in range(1, len(found) + 1):
            jobs.record_attempt(db, job_id, AttemptRecord(Status.READY, NOW, "", (), pdf))
    return paths


@contextmanager
def chrome_with_extension(
    port: int, guard: Guard, folder: str = BUILT_FOLDER
) -> Iterator[BrowserContext]:
    with sync_playwright() as playwright:
        context = playwright.chromium.launch_persistent_context(
            "",
            channel="chromium",
            headless=True,
            bypass_csp=True,
            args=[f"--disable-extensions-except={folder}", f"--load-extension={folder}"],
        )
        context.route("**/*", guard.check)
        worker = context.service_workers[0] if context.service_workers else None
        worker = worker or context.wait_for_event("serviceworker")
        worker.evaluate(f"chrome.storage.local.set({{port: {port}}})")
        try:
            yield context
        finally:
            context.close()


def report(page: Page) -> dict[str, object]:
    page.wait_for_function(
        "['filled', 'offline', 'unknown', 'broken']"
        ".includes(document.documentElement.dataset.satyaapply)",
        timeout=FILLED_TIMEOUT_MS,
    )
    state = page.evaluate("document.documentElement.dataset.satyaapply")
    raw = page.evaluate("document.documentElement.dataset.satyaapplyReport || '{}'")
    return {"state": state, **json.loads(raw)}


def problems(page: Page, job: Job, guard: Guard) -> list[str]:
    seen = report(page)
    found: list[str] = []
    if seen["state"] != "filled":
        return [f"{job.apply_url}: ended as {seen['state']}: {seen.get('error', '')}"]
    fields = seen.get("fields")
    assert isinstance(fields, list)
    for_you = seen.get("forYou") or []
    assert isinstance(for_you, list)
    left = set(for_you)
    found += [
        f"{job.apply_url}: required {item['kind']} not filled: {item['label']}"
        for item in fields
        if item["required"] and not item["filled"] and item["label"] not in left
    ]
    if not any(RESUME_NAME in item for item in guard.blocked):
        found.append(f"{job.apply_url}: the resume never reached the site's upload")
    found += [
        f"{job.apply_url}: answered a consent question: {item['label']}"
        for item in fields
        if CONSENT.search(item["label"]) and item["label"] not in left
    ]
    found += [
        f"{job.apply_url}: tried to send {item[:160]}"
        for item in guard.blocked
        if SUBMISSION.search(item.split(" ", 2)[1])
    ]
    return found + resume_first(job, guard) + phone_once(page, job) + panel_fits(page, job)


def panel_fits(page: Page, job: Job) -> list[str]:
    list_box = page.locator("satyaapply-panel").locator("ul").bounding_box()
    tall = list_box is not None and list_box["height"] > MOST_LIST_PX
    return [f"{job.apply_url}: the list for you is {list_box} tall"] if tall else []


SHOWN_CODE = """() => [...document.querySelectorAll("input[type=tel]")].map((phone) => {
  let row = phone.parentElement;
  for (let depth = 0; row && depth < 6; depth += 1, row = row.parentElement) {
    if (row.querySelectorAll("input, select, button, [role=combobox]").length > 8) break;
    const code = (row.innerText.match(/[+]\\d{1,4}/) || [""])[0];
    if (code) return [phone.value, code];
  }
  return [phone.value, ""];
})"""


def phone_once(page: Page, job: Job) -> list[str]:
    return [
        f"{job.apply_url}: phone repeats the shown country code {code}: {value}"
        for value, code in page.evaluate(SHOWN_CODE)
        if code and value.replace(" ", "").startswith(code)
    ]


def resume_first(job: Job, guard: Guard) -> list[str]:
    log = guard.blocked
    start = next((n for n, item in enumerate(log) if item.startswith("MARK ")), len(log))
    upload = next((n for n, item in enumerate(log) if RESUME_NAME in item), None)
    saves = [n for n, item in enumerate(log) if ANSWER_SAVED in item.split(" ", 2)[1]]
    early = [n for n in saves if upload is not None and start < n < upload]
    return [f"{job.apply_url}: answers were saved before the resume upload"] if early else []


@pytest.mark.parametrize("ats", list(Ats))
def test_the_extension_fills_real_application_forms(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, ats: Ats
) -> None:
    monkeypatch.setattr(extension, "answer_fields", every_answer)
    found = real_jobs(ats)
    assert len(found) >= JOBS_PER_SITE // 2, f"only {len(found)} open {ats} jobs"
    paths = seeded(tmp_path, found)
    failures: list[str] = []
    with running(paths) as server:
        port = server.server_address[1]
        for job in found:
            guard = Guard()
            with chrome_with_extension(port, guard) as context:
                page = context.new_page()
                page.goto(job.apply_url, wait_until="domcontentloaded")
                failures += problems(page, job, guard)
    assert not failures, "\n".join(failures)


@pytest.mark.ai
@pytest.mark.parametrize("ats", list(Ats))
def test_real_claude_answers_a_real_form_and_leaves_consent_to_you(
    tmp_path: Path, ats: Ats
) -> None:
    found = real_jobs(ats)[:1]
    paths = seeded(tmp_path, found)
    with (
        running(paths) as server,
        chrome_with_extension(server.server_address[1], Guard()) as context,
    ):
        guard = Guard()
        context.route("**/*", guard.check)
        page = context.new_page()
        page.goto(found[0].apply_url, wait_until="domcontentloaded")
        failures = problems(page, found[0], guard)
    assert not [item for item in failures if "required" not in item], "\n".join(failures)


WORKABLE = "https://apply.workable.com/api/v1/widget/accounts/{}"
WORKABLE_BOARDS = ("huggingface",)
SMARTRECRUITERS = "https://api.smartrecruiters.com/v1/companies/{}/postings?limit=1"
ADDED_TIMEOUT_MS = 180_000
SETTLED = "['filled', 'shown', 'broken'].includes(document.documentElement.dataset.satyaapply)"


@dataclass(frozen=True)
class RealPage:
    url: str
    title: str


def every_site_extension(tmp_path: Path) -> str:
    folder = tmp_path / "extension"
    shutil.copytree(BUILT_FOLDER, folder)
    manifest = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
    for script in manifest["content_scripts"]:
        script["matches"] = ["<all_urls>"]
    (folder / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return str(folder)


def json_at(url: str) -> object:
    return fetch_json([url])[0].data


def workable_pages() -> list[RealPage]:
    found = []
    for board in WORKABLE_BOARDS:
        listed = items(mapping(json_at(WORKABLE.format(board))).get("jobs"))
        found += [
            RealPage(text(mapping(item), "url"), text(mapping(item), "title"))
            for item in listed[:2]
        ]
    return found


def ats_pages() -> list[RealPage]:
    return [RealPage(job.url, job.title) for ats in Ats for job in real_jobs(ats)[:1]]


def no_claude(page_text: str) -> Posting:
    raise AssertionError(f"Claude was asked to read the page: {page_text[:200]}")


def ready_soon(paths: Paths) -> Callable[[Paths, int], bool]:
    pdf = paths.resumes / RESUME_NAME

    def prepare(_paths: Paths, job_id: int) -> bool:
        with closing(connect(paths.database)) as db:
            jobs.record_attempt(db, job_id, AttemptRecord(Status.READY, NOW, "", (), pdf))
        return True

    return prepare


def added_from_the_panel(context: BrowserContext, paths: Paths, page_seen: RealPage) -> list[str]:
    page = context.new_page()
    page.goto(page_seen.url, wait_until="domcontentloaded")
    page.get_by_role("button", name="Add to SatyaApply").click(timeout=FILLED_TIMEOUT_MS)
    page.wait_for_function(SETTLED, timeout=ADDED_TIMEOUT_MS)
    state = page.evaluate("document.documentElement.dataset.satyaapply")
    with closing(connect(paths.database)) as db:
        added = [
            record.job for record in map(lambda n: records.find(db, n), range(1, 200)) if record
        ]
    match = [job for job in added if job.title == page_seen.title]
    if state == "broken" or not match:
        return [f"{page_seen.url}: ended {state}; saved {[job.title for job in added][:5]}"]
    job = match[0]
    return [] if job.company and len(job.description) > 200 else [f"{page_seen.url}: thin {job}"]


def test_real_job_pages_from_any_site_are_added_from_the_panel(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    paths = seeded(tmp_path, [])
    monkeypatch.setattr(extension, "start_preparing", ready_soon(paths))
    monkeypatch.setattr(extension, "answer_fields", every_answer)
    monkeypatch.setattr(extension, "read_posting", no_claude)
    folder = every_site_extension(tmp_path)
    failures: list[str] = []
    with running(paths) as server:
        for page_seen in [*ats_pages(), *workable_pages()]:
            with chrome_with_extension(server.server_address[1], Guard(), folder) as context:
                failures += added_from_the_panel(context, paths, page_seen)
    assert not failures, "\n".join(failures)


@pytest.mark.ai
def test_claude_reads_a_job_page_that_has_no_job_data(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    posting = mapping(
        items(mapping(json_at(SMARTRECRUITERS.format("BoschGroup"))).get("content"))[0]
    )
    page_seen = RealPage(
        f"https://jobs.smartrecruiters.com/BoschGroup/{text(posting, 'id')}", text(posting, "name")
    )
    paths = seeded(tmp_path, [])
    monkeypatch.setattr(extension, "start_preparing", ready_soon(paths))
    folder = every_site_extension(tmp_path)
    with (
        running(paths) as server,
        chrome_with_extension(server.server_address[1], Guard(), folder) as context,
    ):
        failures = added_from_the_panel(context, paths, page_seen)
    assert not failures, "\n".join(failures)


def test_the_panel_stays_when_the_page_redraws_itself(tmp_path: Path) -> None:
    board = Board(Ats.GREENHOUSE, "headoutcareers")
    found = poll([board]).jobs[:1]
    assert found, "Headout has no open Greenhouse jobs right now"
    paths = seeded(tmp_path, [])
    with (
        running(paths) as server,
        chrome_with_extension(server.server_address[1], Guard()) as context,
    ):
        page = context.new_page()
        page.goto(found[0].apply_url, wait_until="commit")
        page.get_by_role("button", name="Add to SatyaApply").wait_for(timeout=FILLED_TIMEOUT_MS)
        page.wait_for_timeout(STAYS_MS)
        assert page.locator("satyaapply-panel").count() == 1
        assert page.evaluate("document.documentElement.dataset.satyaapply") == "unknown"


AUTO_JOBS_PER_SITE = 2
AUTO_WAIT_MS = 180_000
SEND_NOW = "chrome.alarms.create('send', { when: Date.now() })"


def auto_seeded(tmp_path: Path, found: Sequence[Job]) -> Paths:
    paths = seeded(tmp_path, found)
    profile = load(paths)
    chosen = replace(profile.settings, auto_submit=True, auto_submit_score=70)
    save(paths, replace(profile, settings=chosen))
    with closing(connect(paths.database)) as db:
        db.execute("update jobs set score = 90")
        db.commit()
        autosend.turned_on(db, NOW - timedelta(hours=1))
    return paths


def send_outcome(paths: Paths, context: BrowserContext, job_id: int) -> tuple[str, str]:
    worker = context.service_workers[0]
    with context.expect_page(timeout=AUTO_WAIT_MS):
        worker.evaluate(SEND_NOW)
    deadline = time.monotonic() + AUTO_WAIT_MS / 1000
    while time.monotonic() < deadline:
        with closing(connect(paths.database)) as db:
            row = db.execute(
                "select status, auto_send, note from jobs where id = ?", (job_id,)
            ).fetchone()
        if row["auto_send"] in {"held", "sent"} or row["status"] == Status.APPLIED:
            return str(row["auto_send"] or row["status"]), str(row["note"])
        time.sleep(1)
    return "stuck", ""


@pytest.mark.parametrize("ats", list(Ats))
def test_auto_submit_sends_nothing_real_and_holds_every_job_it_cannot_finish(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, ats: Ats
) -> None:
    monkeypatch.setattr(extension, "answer_fields", every_answer)
    found = real_jobs(ats)[:AUTO_JOBS_PER_SITE]
    paths = auto_seeded(tmp_path, found)
    failures: list[str] = []
    seen: list[str] = []
    with running(paths) as server:
        port = server.server_address[1]
        for job_id, job in enumerate(found, start=1):
            guard = Guard()
            with chrome_with_extension(port, guard) as context:
                outcome, note = send_outcome(paths, context, job_id)
            pressed = any(SUBMISSION.search(item.split(" ", 2)[1]) for item in guard.blocked)
            seen.append(f"{job.apply_url}: {outcome}, pressed Submit: {pressed}, {note}")
            logging.getLogger(__name__).info(seen[-1])
            if outcome != "held":
                failures.append(f"{job.apply_url}: ended {outcome}, not held for you")
            if pressed and note != UNCONFIRMED_NOTE:
                failures.append(f"{job.apply_url}: Submit was pressed but the note says {note}")
    assert not failures, "\n".join(failures + seen)
