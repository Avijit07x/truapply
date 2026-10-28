from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path

import pytest

from truapply.core.models import Job
from truapply.core.paths import Paths
from truapply.resume.contract import Draft, Rendered
from truapply.resume.master import cached_master, master_pdf


@dataclass
class CountingResume:
    source: str = "v1"
    suffix: str = ".txt"
    renders: list[str] = field(default_factory=list)

    def readable(self, source: str) -> str:
        return source

    def draft(self, job: Job, notes: Sequence[str]) -> Draft:
        return Draft(f"{self.source} for {job.title} {notes}", ())

    def revise(self, draft: Draft, problems: Sequence[str]) -> Draft:
        return Draft(draft.source, tuple(problems))

    def problems(self, draft: Draft) -> list[str]:
        return [] if draft.source else ["empty"]

    def render(self, source: str, target: Path) -> Rendered:
        self.renders.append(source)
        target.write_text(source)
        return Rendered(target, 1)


@pytest.fixture
def paths(tmp_path: Path) -> Paths:
    home = Paths(tmp_path / "home")
    home.ensure()
    return home


def test_master_pdf_is_built_once_and_then_reused(paths: Paths) -> None:
    resume = CountingResume()
    first = master_pdf(paths, resume)
    second = master_pdf(paths, resume)
    assert first == second == Rendered(paths.master_pdf, 1)
    assert resume.renders == ["v1"]


def test_an_edited_resume_is_rebuilt(paths: Paths) -> None:
    master_pdf(paths, CountingResume())
    edited = CountingResume(source="v2")
    assert cached_master(paths, edited) is None
    master_pdf(paths, edited)
    assert edited.renders == ["v2"]
    assert paths.master_pdf.read_text() == "v2"


def test_a_deleted_pdf_is_rebuilt(paths: Paths) -> None:
    resume = CountingResume()
    master_pdf(paths, resume)
    paths.master_pdf.unlink()
    master_pdf(paths, resume)
    assert resume.renders == ["v1", "v1"]
