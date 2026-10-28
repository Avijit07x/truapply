import os
import subprocess
import sys
from pathlib import Path

from truapply.core.locks import is_held
from truapply.core.paths import Paths

ALREADY_CHECKING = "The web archive is already being checked."
COMMAND: tuple[str, ...] = (sys.executable, "-m", "truapply", "archive")


def is_going(paths: Paths) -> bool:
    return is_held(paths.archive_lock)


def _windows_detached() -> int:
    if sys.platform == "win32":
        return subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS
    return 0


def _spawn(log: Path) -> None:
    environment = {**os.environ, "PYTHONUNBUFFERED": "1", "PYTHONUTF8": "1"}
    with log.open("wb") as out:
        subprocess.Popen(  # noqa: S603
            COMMAND,
            stdin=subprocess.DEVNULL,
            stdout=out,
            stderr=subprocess.STDOUT,
            env=environment,
            creationflags=_windows_detached(),
            start_new_session=sys.platform != "win32",
        )


def start_in_background(paths: Paths) -> bool:
    if is_going(paths):
        return False
    paths.root.mkdir(parents=True, exist_ok=True)
    _spawn(paths.archive_log)
    return True
