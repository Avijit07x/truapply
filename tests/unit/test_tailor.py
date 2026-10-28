from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from pathlib import Path

import pytest

from tests.unit import samples
from truapply.core.errors import AIError, UsageLimitError
from truapply.core.models import Job
from truapply.resume.contract import Draft, Rendered
from truapply.resume.tailor import TailorRequest, file_name_for, tailor

ORIGINAL = "Built 40 components with React.\nCut load time by 30%."
REORDERED = "Cut load time by 30%.\nBuilt 40 components with React."


@dataclass
class FakeResume:
    drafted: str = REORDERED
    pages: int = 1
    error: Exception | None = None
    source: str = ORIGINAL
    suffix: str = ".txt"
    revised: str | None = None
    rendered: list[str] = field(default_factory=list)
    revisions: list[tuple[str, ...]] = field(default_factory=list)

    def readable(self, source: str) -> str:
        return source

    def draft(self, job: Job, notes: Sequence[str]) -> Draft:
        if self.error:
            raise self.error
        return Draft(self.drafted, (f"tailored for {job.company}", *notes))

    def revise(self, draft: Draft, problems: Sequence[str]) -> Draft:
        self.revisions.append(tuple(problems))
        return Draft(draft.source if self.revised is None else self.revised, ("revised",))

    def problems(self, draft: Draft) -> list[str]:
        return [] if draft.source else ["empty"]

    def render(self, source: str, target: Path) -> Rendered:
        self.rendered.append(source)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(source)
        return Rendered(target, self.pages)


def no_claims(_original: str, _tailored: str) -> tuple[str, ...]:
    return ()


@pytest.fixture
def request_for(tmp_path: Path) -> Callable[[], TailorRequest]:
    original = tmp_path / "master.pdf"
    original.write_text("ORIGINAL PDF")

    def build() -> TailorRequest:
        return TailorRequest(
            samples.job(),
            ("keep my headline",),
            tmp_path / "out",
            "Asha_Rao_Resume.pdf",
            Rendered(original, 1),
        )

    return build


def test_clean_draft_is_used_and_saved(request_for: Callable[[], TailorRequest]) -> None:
    request = request_for()
    result = tailor(FakeResume(), request, no_claims)
    assert not result.used_original
    assert result.pdf.read_text() == REORDERED
    assert (request.out_dir / "tailored.txt").read_text() == REORDERED
    assert result.changes == ("tailored for Northwind", "keep my headline")


def test_a_new_number_falls_back_to_the_original(request_for: Callable[[], TailorRequest]) -> None:
    resume = FakeResume(drafted=ORIGINAL.replace("30%", "45%"))
    result = tailor(resume, request_for(), no_claims)
    assert result.used_original
    assert result.problems == ("new numbers: 45",)
    assert result.pdf.read_text() == "ORIGINAL PDF"
    assert resume.rendered == []


def test_a_clean_draft_is_never_revised(request_for: Callable[[], TailorRequest]) -> None:
    resume = FakeResume()
    tailor(resume, request_for(), no_claims)
    assert resume.revisions == []


def test_a_rejected_draft_is_revised_once_and_used_when_fixed(
    request_for: Callable[[], TailorRequest],
) -> None:
    resume = FakeResume(drafted=ORIGINAL.replace("30%", "45%"), revised=REORDERED)
    result = tailor(resume, request_for(), no_claims)
    assert not result.used_original
    assert resume.revisions == [("new numbers: 45",)]
    assert result.pdf.read_text() == REORDERED
    assert result.changes == ("revised",)


def test_a_revision_that_still_fails_falls_back(
    request_for: Callable[[], TailorRequest],
) -> None:
    resume = FakeResume(drafted=ORIGINAL.replace("30%", "45%"), revised=ORIGINAL + " 99")
    result = tailor(resume, request_for(), no_claims)
    assert result.used_original
    assert result.problems == ("new numbers: 99",)
    assert len(resume.revisions) == 1


def test_a_fallback_removes_a_stale_tailored_source(
    request_for: Callable[[], TailorRequest],
) -> None:
    request = request_for()
    tailor(FakeResume(), request, no_claims)
    tailor(FakeResume(drafted=ORIGINAL.replace("30%", "45%")), request, no_claims)
    assert not (request.out_dir / "tailored.txt").exists()


def test_a_new_claim_falls_back_to_the_original(request_for: Callable[[], TailorRequest]) -> None:
    def kubernetes(_original: str, _tailored: str) -> tuple[str, ...]:
        return ("Kubernetes experience",)

    result = tailor(FakeResume(drafted=REORDERED + "\nRan Kubernetes."), request_for(), kubernetes)
    assert result.used_original
    assert result.problems == ("new claim: Kubernetes experience",)


def test_a_longer_resume_falls_back_to_the_original(
    request_for: Callable[[], TailorRequest],
) -> None:
    result = tailor(FakeResume(pages=2), request_for(), no_claims)
    assert result.used_original
    assert "2 pages" in result.problems[0]


def test_an_ai_failure_falls_back_to_the_original(
    request_for: Callable[[], TailorRequest],
) -> None:
    result = tailor(FakeResume(error=AIError("garbled")), request_for(), no_claims)
    assert result.used_original
    assert result.problems == ("tailoring failed: garbled",)


def test_a_failed_claim_check_is_never_treated_as_clean(
    request_for: Callable[[], TailorRequest],
) -> None:
    def broken(_original: str, _tailored: str) -> tuple[str, ...]:
        raise AIError("timeout")

    result = tailor(FakeResume(), request_for(), broken)
    assert result.used_original
    assert result.problems == ("couldn't check for new claims: timeout",)


def test_a_usage_limit_stops_tailoring(request_for: Callable[[], TailorRequest]) -> None:
    with pytest.raises(UsageLimitError):
        tailor(FakeResume(error=UsageLimitError("limit")), request_for(), no_claims)


@pytest.mark.parametrize(
    ("person", "expected"),
    [
        ("Asha Rao", "Asha_Rao_Resume.pdf"),
        ("  José O'Neil ", "José_O_Neil_Resume.pdf"),
        ("../../etc/passwd", "etc_passwd_Resume.pdf"),
        ("", "Resume_Resume.pdf"),
    ],
)
def test_resume_file_is_named_like_a_person_would(person: str, expected: str) -> None:
    assert file_name_for(person) == expected
