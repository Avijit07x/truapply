import threading
from contextlib import closing
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

import pytest

from tests.unit import samples
from tests.unit.test_master import CountingResume
from truapply.core.paths import Paths
from truapply.resume.contract import Rendered, Resume
from truapply.resume.tailor import Tailored, TailorRequest
from truapply.run import tailoring
from truapply.run.context import RunContext
from truapply.run.tailoring import tailor_all
from truapply.store.db import connect

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

    monkeypatch.setattr(tailoring, "tailor", tailor)
    picks = [replace(samples.job(), id=1), replace(samples.job(company="C"), id=2)]
    with closing(connect(run.paths.database)) as db:
        queued = tailor_all(db, run, picks)
    assert [item.job.id for item in queued] == [1, 2]
    assert said == [
        "Tailoring your resume for 2 jobs …",
        "  Northwind · Frontend Engineer: tailored",
        "  C · Frontend Engineer: kept your original resume",
    ]


def test_with_tailoring_off_every_job_gets_your_original_resume_and_no_ai_call(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    said: list[str] = []
    profile = samples.profile(tmp_path / "master.tex")
    master = tmp_path / "m.pdf"
    master.write_bytes(b"%PDF-1.4")
    run = RunContext(
        Paths(tmp_path),
        replace(profile, settings=replace(profile.settings, tailor_resume=False)),
        CountingResume(),
        Rendered(master, 1),
        lambda: NOW,
        progress=said.append,
    )

    def tailor(_resume: Resume, _request: TailorRequest) -> Tailored:
        raise AssertionError("tailoring is off")

    monkeypatch.setattr(tailoring, "tailor", tailor)
    with closing(connect(run.paths.database)) as db:
        queued = tailor_all(db, run, [replace(samples.job(), id=1)])
    assert queued[0].resume.used_original
    assert queued[0].resume.pdf.read_bytes() == b"%PDF-1.4"
    assert said == [
        "Getting your original resume ready for 1 job …",
        "  Northwind · Frontend Engineer: kept your original resume",
    ]
