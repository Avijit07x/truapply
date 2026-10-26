import threading
import urllib.request
from collections.abc import Iterator
from dataclasses import replace
from datetime import UTC, datetime
from email.message import Message
from pathlib import Path
from urllib.error import HTTPError

import pytest

from satyaapply.core.forms import Sent
from satyaapply.core.models import Status
from satyaapply.core.paths import Paths
from satyaapply.store import jobs
from satyaapply.store.db import connect
from satyaapply.store.jobs import AttemptRecord
from satyaapply.tracker.pages import LABELS
from satyaapply.tracker.server import TrackerServer
from tests.unit import samples

NOW = datetime(2026, 10, 25, 12, 0, tzinfo=UTC)
INJECTED = "<script>alert(1)</script>"


@pytest.fixture
def tracker(tmp_path: Path) -> Iterator[TrackerServer]:
    paths = Paths(tmp_path)
    paths.ensure()
    trusted_pdf = paths.resumes / "1.pdf"
    trusted_pdf.parent.mkdir(parents=True, exist_ok=True)
    trusted_pdf.write_bytes(b"%PDF-1.4 tailored")
    outside_pdf = tmp_path.parent / "outside.pdf"
    outside_pdf.write_bytes(b"%PDF-1.4 elsewhere")
    filled = replace(samples.job(), title=f"Engineer {INJECTED}", url="javascript:alert(1)")
    with connect(paths.database) as db:
        jobs.add_many(db, [filled, samples.job(external_id="b", company="C")], NOW)
        sent = (Sent("Why us?", INJECTED),)
        jobs.record_attempt(db, 1, AttemptRecord(Status.READY, NOW, "filled", sent, trusted_pdf))
        jobs.record_attempt(db, 2, AttemptRecord(Status.READY, NOW, "filled", (), outside_pdf))
    db.close()
    paths.shots.mkdir(parents=True, exist_ok=True)
    (paths.shots / "1.png").write_bytes(b"\x89PNG fake")
    server = TrackerServer(paths, 0)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield server
    server.shutdown()
    server.server_close()


def get(server: TrackerServer, path: str, host: str | None = None) -> tuple[int, Message, bytes]:
    headers = {"Host": host} if host else {}
    request = urllib.request.Request(server.url + path, headers=headers)  # noqa: S310
    try:
        with urllib.request.urlopen(request, timeout=5) as response:  # noqa: S310
            return response.status, response.headers, response.read()
    except HTTPError as error:
        return error.code, error.headers, error.read()


def post_status(server: TrackerServer, origin: str | None) -> int:
    headers = {"Origin": origin} if origin else {}
    url = server.url + "/"
    request = urllib.request.Request(url, data=b"", headers=headers, method="POST")  # noqa: S310
    try:
        with urllib.request.urlopen(request, timeout=5) as response:  # noqa: S310
            return int(response.status)
    except HTTPError as error:
        return error.code


def test_every_page_loads_and_every_status_can_be_filtered(tracker: TrackerServer) -> None:
    status, headers, body = get(tracker, "/")
    assert status == 200
    assert "default-src 'none'" in headers["Content-Security-Policy"]
    assert b"Waiting for your OK" in body
    for option in Status:
        code, _, listing = get(tracker, f"/jobs?status={option}")
        assert code == 200
        assert LABELS[option].encode() in listing
    assert get(tracker, "/style.css")[0] == 200


def test_job_text_is_escaped_and_unsafe_links_are_dropped(tracker: TrackerServer) -> None:
    status, _, body = get(tracker, "/jobs/1")
    assert status == 200
    assert INJECTED.encode() not in body
    assert b"&lt;script&gt;alert(1)&lt;/script&gt;" in body
    assert b"javascript:" not in body
    assert b"/jobs/1/screenshot.png" in body


def test_files_are_served_by_job_id_only_from_the_data_folder(tracker: TrackerServer) -> None:
    status, headers, body = get(tracker, "/jobs/1/screenshot.png")
    assert (status, headers["Content-Type"], body) == (200, "image/png", b"\x89PNG fake")
    assert get(tracker, "/jobs/1/resume.pdf")[2] == b"%PDF-1.4 tailored"
    assert get(tracker, "/jobs/2/resume.pdf")[0] == 404
    assert get(tracker, "/jobs/1/../../outside.pdf")[0] == 404
    assert get(tracker, "/jobs/99")[0] == 404


def test_requests_from_other_websites_are_rejected(tracker: TrackerServer) -> None:
    assert post_status(tracker, "https://evil.example") == 403
    assert post_status(tracker, None) == 403
    assert post_status(tracker, tracker.url) == 404
    assert get(tracker, "/", host="evil.example")[0] == 403
