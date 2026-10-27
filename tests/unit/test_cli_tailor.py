from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path

import pytest

from satyaapply import cli
from satyaapply.core.paths import Paths
from satyaapply.core.profile import Profile, save
from satyaapply.resume.contract import Rendered, Resume
from satyaapply.resume.tailor import Tailored, TailorRequest
from satyaapply.store import rules
from satyaapply.store.db import connect
from satyaapply.store.rules import NewRule, RuleKind, RuleState
from tests.unit import samples
from tests.unit.test_master import CountingResume

NOW = datetime(2026, 10, 26, tzinfo=UTC)
NOTE = "Don't change my headline."


def test_a_tailoring_preview_follows_your_tailoring_notes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    paths = Paths(tmp_path / "home")
    paths.ensure()
    master_tex = tmp_path / "master.tex"
    master_tex.write_text("resume", encoding="utf-8")
    save(paths, samples.profile(master_tex))
    with closing(connect(paths.database)) as db:
        rules.add(db, NewRule(RuleKind.TAILORING_NOTE, NOTE, RuleState.ACTIVE, NOW))
        rules.add(db, NewRule(RuleKind.RULE, "No staffing agencies.", RuleState.ACTIVE, NOW))
    asked: list[tuple[str, ...]] = []

    def preview(_resume: Resume, request: TailorRequest) -> Tailored:
        asked.append(request.notes)
        return Tailored(tmp_path / "preview.pdf", "v1", False, (), ())

    def master(_paths: Paths, _resume: Resume) -> Rendered:
        return Rendered(tmp_path / "master.pdf", 1)

    def resume(_profile: Profile) -> Resume:
        return CountingResume()

    monkeypatch.setenv("SATYAAPPLY_HOME", str(paths.root))
    monkeypatch.setattr(cli, "load_resume", resume)
    monkeypatch.setattr(cli, "master_pdf", master)
    monkeypatch.setattr(cli, "tailor", preview)
    job = tmp_path / "job.txt"
    job.write_text("React dashboards for hospitals.", encoding="utf-8")
    argv = ["tailor", "--company", "Northwind", "--title", "Frontend Engineer", str(job)]
    assert cli.main(argv) == 0
    assert asked == [(NOTE,)]
