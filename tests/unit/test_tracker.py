from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

import pytest

from tests.unit import samples
from tests.unit.tracker_api import JSON_TYPE, fetch, get, running
from truapply.core.forms import Sent
from truapply.core.models import Status
from truapply.core.paths import Paths
from truapply.store import jobs
from truapply.store.db import connect
from truapply.store.jobs import AttemptRecord
from truapply.tracker import static
from truapply.tracker.server import FOREVER, MAX_BODY_BYTES, NO_STORE, TrackerServer

NOW = datetime(2026, 10, 25, 12, 0, tzinfo=UTC)
INJECTED = "<script>alert(1)</script>"
INDEX = b"<!doctype html><div id=root></div>"
SCRIPT = b"console.log(1)"
BURST = 48


@pytest.fixture(autouse=True)
def built(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    root = tmp_path / "static"
    (root / "assets").mkdir(parents=True)
    (root / "index.html").write_bytes(INDEX)
    (root / "assets" / "index-a1B2.js").write_bytes(SCRIPT)
    monkeypatch.setattr(static, "_root", lambda: root)
    return root


@pytest.fixture
def tracker(tmp_path: Path) -> Iterator[TrackerServer]:
    paths = Paths(tmp_path / "home")
    paths.ensure()
    trusted_pdf = paths.resumes / "1.pdf"
    trusted_pdf.parent.mkdir(parents=True, exist_ok=True)
    trusted_pdf.write_bytes(b"%PDF-1.4 tailored")
    outside_pdf = tmp_path / "outside.pdf"
    outside_pdf.write_bytes(b"%PDF-1.4 elsewhere")
    filled = replace(samples.job(), title=f"Engineer {INJECTED}", url="javascript:alert(1)")
    with closing(connect(paths.database)) as db:
        jobs.add_many(db, [filled, samples.job(external_id="b", company="C")], NOW)
        sent = (Sent("Why us?", INJECTED),)
        jobs.record_attempt(db, 1, AttemptRecord(Status.READY, NOW, "filled", sent, trusted_pdf))
        jobs.record_attempt(db, 2, AttemptRecord(Status.READY, NOW, "filled", (), outside_pdf))
    with running(paths) as server:
        yield server


def send(server: TrackerServer, headers: dict[str, str], data: bytes = b"{}") -> int:
    return fetch(server, "/api/jobs/1/thumbs", data, headers)[0]


def test_the_api_answers_json_with_strict_headers(tracker: TrackerServer) -> None:
    status, headers, _ = fetch(tracker, "/api/summary")
    assert status == 200
    assert headers["Content-Type"].startswith(JSON_TYPE)
    assert headers["Cache-Control"] == NO_STORE
    policy = headers["Content-Security-Policy"]
    assert "default-src 'none'" in policy
    assert "script-src 'self';" in policy
    assert "frame-ancestors 'none'" in policy
    assert headers["X-Content-Type-Options"] == "nosniff"


def test_job_text_comes_back_as_plain_strings_and_unsafe_links_are_dropped(
    tracker: TrackerServer,
) -> None:
    status, job = get(tracker, "/api/jobs/1")
    assert status == 200
    assert job["title"] == f"Engineer {INJECTED}"
    assert job["url"] is None
    assert job["applyUrl"] is None
    assert job["sent"] == [{"question": "Why us?", "answer": INJECTED}]
    assert job["hasResume"]
    assert get(tracker, "/api/jobs/99")[0] == 404


def test_files_are_served_by_job_id_only_from_the_data_folder(tracker: TrackerServer) -> None:
    status, headers, body = fetch(tracker, "/jobs/1/resume.pdf")
    assert (status, headers["Content-Type"], body) == (200, "application/pdf", b"%PDF-1.4 tailored")
    assert fetch(tracker, "/jobs/2/resume.pdf")[0] == 404
    assert get(tracker, "/api/jobs/2")[1]["hasResume"] is False
    assert b"elsewhere" not in fetch(tracker, "/jobs/1/../../outside.pdf")[2]
    assert fetch(tracker, "/jobs/99/resume.pdf")[0] == 404


def test_requests_from_other_websites_are_refused(tracker: TrackerServer) -> None:
    own = {"Origin": tracker.url, "Content-Type": JSON_TYPE}
    assert send(tracker, own | {"Origin": "https://evil.example"}) == 403
    assert send(tracker, {"Content-Type": JSON_TYPE}) == 403
    assert send(tracker, own | {"Content-Type": "application/x-www-form-urlencoded"}) == 403
    assert send(tracker, own | {"Content-Type": "text/plain"}) == 403
    assert send(tracker, own | {"Host": "evil.example"}) == 403
    assert send(tracker, own | {"Content-Length": str(MAX_BODY_BYTES + 1)}) == 403
    assert fetch(tracker, "/api/summary", headers={"Host": "evil.example"})[0] == 403
    assert fetch(tracker, "/", headers={"Host": "evil.example"})[0] == 403


def test_a_post_must_be_a_json_object(tracker: TrackerServer) -> None:
    own = {"Origin": tracker.url, "Content-Type": JSON_TYPE}
    assert send(tracker, own, b"not json") == 400
    assert send(tracker, own, b"[1, 2]") == 400
    assert send(tracker, own, b'{"value": 1}') == 200
    assert fetch(tracker, "/api/nothing", b"{}", own)[0] == 404
    assert fetch(tracker, "/jobs/1", b"{}", own)[0] == 404


def test_every_other_page_gets_the_app_and_assets_are_cached(tracker: TrackerServer) -> None:
    for path in ("/", "/runs", "/jobs/1", "/settings?x=1"):
        status, headers, body = fetch(tracker, path)
        assert (status, body) == (200, INDEX)
        assert headers["Content-Type"].startswith("text/html")
        assert headers["Cache-Control"] == NO_STORE
    status, headers, body = fetch(tracker, "/assets/index-a1B2.js")
    assert (status, body) == (200, SCRIPT)
    assert headers["Content-Type"].startswith("text/javascript")
    assert headers["Cache-Control"] == FOREVER
    assert fetch(tracker, "/assets/missing.js")[0] == 404
    assert fetch(tracker, "/assets/index.html")[0] == 404
    assert fetch(tracker, "/assets/.hidden.js")[2] == INDEX


def test_an_unbuilt_app_says_how_to_build_it(tracker: TrackerServer, built: Path) -> None:
    (built / "index.html").unlink()
    status, _, body = fetch(tracker, "/")
    assert status == 503
    assert b"npm run build" in body
    assert get(tracker, "/api/summary")[0] == 200


def test_a_burst_of_requests_is_all_answered(tracker: TrackerServer) -> None:
    def load(_: int) -> int:
        return fetch(tracker, "/assets/index-a1B2.js")[0]

    with ThreadPoolExecutor(BURST) as pool:
        assert set(pool.map(load, range(BURST * 4))) == {200}
