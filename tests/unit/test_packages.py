from pathlib import Path

import pytest

from truapply.core.errors import LatexFailedError
from truapply.resume import packages
from truapply.resume.contract import Rendered
from truapply.resume.packages import render_installing, tlmgr

SEARCH_OUTPUT = (
    "tlmgr: package repository https://example.org (not verified)\n"
    "microtype:\n\ttexmf-dist/tex/latex/microtype/microtype.sty\n"
)


def fake_tlmgr(tmp_path: Path, exit_code: int, output: str) -> Path:
    script = tmp_path / "tlmgr"
    script.write_text(f"#!/bin/sh\nprintf '%s\\n' '{output}'\nexit {exit_code}\n")
    script.chmod(0o755)
    return script


def test_a_failing_tlmgr_raises_a_clear_error_not_a_crash(tmp_path: Path) -> None:
    script = fake_tlmgr(tmp_path, 255, "tlmgr itself needs to be updated.")
    with pytest.raises(LatexFailedError, match="tlmgr itself needs to be updated"):
        tlmgr(script, "install", "microtype")


def test_tlmgr_output_is_returned_on_success(tmp_path: Path) -> None:
    assert tlmgr(fake_tlmgr(tmp_path, 0, "ok"), "search").strip() == "ok"


class Builds:
    def __init__(self, failures: list[str | None]) -> None:
        self.failures = failures
        self.calls = 0

    def __call__(self, _source: str, target: Path, _pdflatex: Path) -> Rendered:
        self.calls += 1
        if self.failures:
            raise LatexFailedError("missing", self.failures.pop(0))
        return Rendered(target, 1)


@pytest.fixture
def pdflatex(tmp_path: Path) -> Path:
    (tmp_path / "tlmgr").touch()
    return tmp_path / "pdflatex"


def test_missing_package_is_installed_after_updating_tlmgr_once(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, pdflatex: Path
) -> None:
    commands: list[tuple[str, ...]] = []

    def record(_executable: Path, *arguments: str) -> str:
        commands.append(arguments)
        if arguments[0] != "search":
            return ""
        package = arguments[-1].strip("/").removesuffix(".sty")
        return f"tlmgr: package repository https://example.org\n{package}:\n\tpath/{package}.sty\n"

    builds = Builds(["microtype.sty", "enumitem.sty"])
    monkeypatch.setattr(packages, "render_latex", builds)
    monkeypatch.setattr(packages, "tlmgr", record)
    result = render_installing("src", tmp_path / "out.pdf", pdflatex)
    assert result.pages == 1
    assert builds.calls == 3
    assert commands == [
        ("update", "--self"),
        ("search", "--global", "--file", "/microtype.sty"),
        ("install", "microtype"),
        ("search", "--global", "--file", "/enumitem.sty"),
        ("install", "enumitem"),
    ]


def test_a_package_that_stays_missing_stops_the_loop(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, pdflatex: Path
) -> None:
    monkeypatch.setattr(packages, "render_latex", Builds(["microtype.sty", "microtype.sty"]))
    monkeypatch.setattr(packages, "tlmgr", lambda _e, *_a: SEARCH_OUTPUT)
    with pytest.raises(LatexFailedError):
        render_installing("src", tmp_path / "out.pdf", pdflatex)


def test_errors_that_arent_missing_files_are_not_retried(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, pdflatex: Path
) -> None:
    builds = Builds([None])
    monkeypatch.setattr(packages, "render_latex", builds)
    with pytest.raises(LatexFailedError):
        render_installing("src", tmp_path / "out.pdf", pdflatex)
    assert builds.calls == 1
