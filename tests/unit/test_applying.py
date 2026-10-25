import threading
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

import pytest

from satyaapply.core.paths import Paths
from satyaapply.resume.contract import Rendered, Resume
from satyaapply.resume.tailor import Tailored, TailorRequest
from satyaapply.run import applying
from satyaapply.run.applying import tailor_all
from satyaapply.run.context import RunContext
from tests.unit import samples
from tests.unit.test_master import CountingResume

NOW = datetime(2026, 10, 25, tzinfo=UTC)


def test_resumes_are_tailored_at_the_same_time_and_kept_in_order(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    said: list[str] = []
    run = RunContext(
        Paths(tmp_path),
        samples.profile(tmp_path / "master.tex"),
        CountingResume(),
        Rendered(tmp_path / "m.pdf", 1),
        lambda: NOW,
        progress=said.append,
    )
    both_running = threading.Barrier(2, timeout=5)

    def tailor(_resume: Resume, request: TailorRequest) -> Tailored:
        both_running.wait()
        kept = request.job.company == "C"
        return Tailored(tmp_path / f"{request.job.company}.pdf", "", kept, (), ())

    monkeypatch.setattr(applying, "tailor", tailor)
    picks = [replace(samples.job(), id=1), replace(samples.job(company="C"), id=2)]
    queued = tailor_all(run, picks)
    assert [item.job_id for item in queued] == [1, 2]
    assert said == [
        "Tailoring your resume for 2 jobs …",
        "  Northwind · Frontend Engineer: tailored",
        "  C · Frontend Engineer: kept your original resume",
    ]
