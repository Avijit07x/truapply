import plistlib
import shutil
import sqlite3
import sys
from collections.abc import Iterator, Sequence
from contextlib import closing, contextmanager
from functools import partial
from pathlib import Path
from typing import NoReturn

import pytest
from playwright.sync_api import Error as PlaywrightError

from truapply import doctor
from truapply.browser import chrome
from truapply.core.paths import Paths
from truapply.core.schedule import Plan, install, plist_path
from truapply.store.db import connect


class FailingChromium:
    def launch(self, **_options: object) -> NoReturn:
        raise PlaywrightError("no browser here")


class NoBrowsers:
    chromium = FailingChromium()


@contextmanager
def no_browsers() -> Iterator[NoBrowsers]:
    yield NoBrowsers()


def accept(_arguments: Sequence[str]) -> int:
    return 0


def broken(check: doctor.Check, fix: str) -> None:
    assert not check.ok
    assert fix in check.fix


def test_a_missing_data_folder_is_named(tmp_path: Path) -> None:
    check = doctor.attempt("Data folder", partial(doctor.folder, Paths(tmp_path / "missing")))
    broken(check, "truapply setup")


def test_a_read_only_data_folder_is_named(tmp_path: Path) -> None:
    tmp_path.chmod(0o500)
    try:
        check = doctor.attempt("Data folder", partial(doctor.folder, Paths(tmp_path)))
    finally:
        tmp_path.chmod(0o700)
    broken(check, "permissions")


def test_a_damaged_database_is_named(tmp_path: Path) -> None:
    paths = Paths(tmp_path)
    paths.database.write_bytes(b"this is not a database at all" * 100)
    broken(doctor.attempt("Database", partial(doctor.database, paths)), "truapply.db")


def test_a_database_from_a_newer_version_is_named(tmp_path: Path) -> None:
    paths = Paths(tmp_path)
    connect(paths.database).close()
    with closing(sqlite3.connect(paths.database)) as db:
        db.execute("pragma user_version = 999")
    broken(doctor.attempt("Database", partial(doctor.database, paths)), "upgrade")


def test_a_missing_profile_is_named(tmp_path: Path) -> None:
    [check] = doctor.profile_checks(Paths(tmp_path))
    broken(check, "truapply setup")


def test_missing_claude_is_named(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(shutil, "which", lambda _name: None)
    broken(doctor.attempt("Claude Code", doctor.claude), "Install Claude Code")


def test_a_missing_browser_is_named(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(chrome, "sync_playwright", no_browsers)
    broken(doctor.attempt("Browser", chrome.browser_name), "playwright install chromium")


def test_an_unbuilt_tracker_page_is_named(tmp_path: Path) -> None:
    check = doctor.attempt("Tracker page", partial(doctor.app, tmp_path / "index.html"))
    broken(check, "npm run build")


def test_a_schedule_whose_python_is_gone_is_named(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(sys, "platform", "darwin")
    install(Paths(tmp_path), Plan(3), tmp_path, accept)
    target = plist_path(tmp_path)
    agent = plistlib.loads(target.read_bytes())
    agent["ProgramArguments"][0] = str(tmp_path / "old-venv" / "python")
    target.write_bytes(plistlib.dumps(agent))
    broken(doctor.attempt("Schedule", partial(doctor.schedule, tmp_path)), "truapply schedule")


def test_no_schedule_is_not_a_problem(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "platform", "darwin")
    check = doctor.attempt("Schedule", partial(doctor.schedule, tmp_path))
    assert check.ok
    assert "truapply schedule" in check.detail


def test_the_report_fails_when_anything_is_broken(capsys: pytest.CaptureFixture[str]) -> None:
    fine = doctor.Check("Profile", True, "ok")
    assert doctor.report([fine]) == 0
    assert doctor.report([fine, doctor.Check("Browser", False, "gone", "Install Chrome")]) == 1
    assert "→ Install Chrome" in capsys.readouterr().out
