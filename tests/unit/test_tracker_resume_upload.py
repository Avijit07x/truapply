import base64
from pathlib import Path

import pytest

from satyaapply.ai import tasks
from satyaapply.core.documents import ResumeData, ResumeDocument, ResumeFormat
from satyaapply.core.paths import Paths
from satyaapply.core.profile import load, save
from satyaapply.tracker import resume_upload
from tests.unit import samples
from tests.unit.tracker_api import JSON_TYPE, fetch, post, running

URL = "/api/settings/resume"


@pytest.fixture
def paths(tmp_path: Path) -> Paths:
    paths = Paths(tmp_path / "home")
    paths.ensure()
    resume = paths.resume_dir / "master.tex"
    resume.write_text("old resume", encoding="utf-8")
    save(paths, samples.profile(resume))
    return paths


@pytest.fixture
def claude(monkeypatch: pytest.MonkeyPatch) -> list[ResumeDocument]:
    asked: list[ResumeDocument] = []

    def convert(document: ResumeDocument) -> ResumeData:
        asked.append(document)
        return samples.resume_data()

    monkeypatch.setattr(tasks, "convert_resume", convert)
    monkeypatch.setattr(resume_upload, "find_pdflatex", lambda: None)
    return asked


def upload(name: str, data: bytes) -> dict[str, object]:
    return {"name": name, "data": base64.b64encode(data).decode()}


@pytest.mark.e2e
def test_a_new_resume_replaces_the_old_one(paths: Paths, claude: list[ResumeDocument]) -> None:
    with running(paths) as server:
        status, answer = post(server, URL, upload("Asha CV.md", b"# Asha Rao\nFrontend engineer"))
    assert status == 200
    assert answer == {"format": "structured", "pages": 1}
    assert claude[0].text == "# Asha Rao\nFrontend engineer"
    saved = load(paths)
    assert saved.resume.format is ResumeFormat.STRUCTURED
    assert saved.resume.path == paths.resume_dir / "master.json"
    assert paths.master_pdf.is_file()
    assert not list(paths.resume_dir.glob("upload*"))
    assert saved.name == samples.profile(saved.resume.path).name


@pytest.mark.parametrize(
    ("body", "error"),
    [
        (upload("notes.exe", b"x"), resume_upload.WRONG_KIND),
        ({"name": "cv.md", "data": "not base64!"}, resume_upload.NOT_READ),
        (upload("cv.md", b""), resume_upload.NOT_READ),
        (upload("cv.md", b"x" * (resume_upload.MAX_RESUME_BYTES + 1)), None),
    ],
)
def test_bad_uploads_change_nothing(
    paths: Paths, claude: list[ResumeDocument], body: dict[str, object], error: str | None
) -> None:
    before = load(paths)
    with running(paths) as server:
        status, answer = post(server, URL, body)
    assert status in (400, 403)
    if error:
        assert answer["error"] == error
    assert load(paths) == before
    assert claude == []


def test_a_broken_latex_resume_is_refused(paths: Paths, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(resume_upload, "find_pdflatex", lambda: Path("/usr/bin/pdflatex"))
    before = load(paths)
    with running(paths) as server:
        status, answer = post(server, URL, upload("cv.tex", b"\\documentclass{article}"))
    assert status == 400
    assert str(answer["error"]).startswith("Your resume wasn't changed.")
    assert load(paths) == before


@pytest.mark.usefixtures("claude")
def test_only_the_upload_takes_big_bodies(paths: Paths) -> None:
    big = upload("notes.exe", b"x" * 300_000)
    declared = {"Origin": "", "Content-Type": JSON_TYPE, "Content-Length": "300000"}
    with running(paths) as server:
        assert post(server, URL, big)[0] == 400
        claimed = declared | {"Origin": server.url}
        assert fetch(server, "/api/settings", b"{}", claimed)[0] == 403
