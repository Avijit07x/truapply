import subprocess
import sys
from pathlib import Path

import pytest

from truapply import cli
from truapply.core.errors import RunAlreadyGoingError
from truapply.core.paths import HOME_ENV, Paths
from truapply.run import RunOptions, run
from truapply.run.lock import run_lock

HOLD_THE_LOCK = (
    "import fcntl, sys, time\n"
    "handle = open(sys.argv[1], 'a')\n"
    "fcntl.flock(handle, fcntl.LOCK_EX)\n"
    "print('locked', flush=True)\n"
    "time.sleep(30)\n"
)


def test_a_second_run_exits_while_the_first_is_going(tmp_path: Path) -> None:
    paths = Paths(tmp_path)
    with run_lock(paths), pytest.raises(RunAlreadyGoingError, match="already running"):
        run(paths, RunOptions(search=False))
    with run_lock(paths):
        pass


def test_the_run_command_says_already_running(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv(HOME_ENV, str(tmp_path))
    with run_lock(Paths(tmp_path)):
        assert cli.main(["run", "--no-search"]) == 1
    assert "already running" in capsys.readouterr().err


def test_a_scheduled_run_writes_its_log_where_the_tracker_reads_it(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(HOME_ENV, str(tmp_path))
    assert cli.main(["run", "--scheduled"]) == 1
    logs = list(Paths(tmp_path).runs.glob("*.log"))
    assert len(logs) == 1
    assert logs[0].read_text(encoding="utf-8").startswith("Automatic run\n✘ No profile yet.")


def test_a_scheduled_run_leaves_no_log_while_another_run_is_going(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv(HOME_ENV, str(tmp_path))
    paths = Paths(tmp_path)
    with run_lock(paths):
        assert cli.main(["run", "--scheduled"]) == 0
    assert list(paths.runs.glob("*.log")) == []
    assert "already running" in capsys.readouterr().out


def test_a_killed_run_frees_the_lock(tmp_path: Path) -> None:
    paths = Paths(tmp_path)
    command = [sys.executable, "-c", HOLD_THE_LOCK, str(paths.lock)]
    with subprocess.Popen(command, stdout=subprocess.PIPE, text=True) as holder:  # noqa: S603
        assert holder.stdout is not None
        assert holder.stdout.readline().strip() == "locked"
        with pytest.raises(RunAlreadyGoingError), run_lock(paths):
            pass
        holder.kill()
        holder.wait(5)
    with run_lock(paths):
        pass
