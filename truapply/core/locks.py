import sys
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import IO

from truapply.core.errors import TruApplyError

if sys.platform == "win32":
    import msvcrt

    def _lock(handle: IO[str]) -> bool:
        handle.seek(0)
        try:
            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
        except OSError:
            return False
        return True

    def _unlock(handle: IO[str]) -> None:
        handle.seek(0)
        msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)

else:
    import fcntl

    def _lock(handle: IO[str]) -> bool:
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return False
        return True

    def _unlock(handle: IO[str]) -> None:
        fcntl.flock(handle, fcntl.LOCK_UN)


@contextmanager
def held(path: Path, busy: TruApplyError) -> Iterator[None]:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as handle:
        if not _lock(handle):
            raise busy
        try:
            yield
        finally:
            _unlock(handle)


def is_held(path: Path) -> bool:
    if not path.is_file():
        return False
    with path.open("a") as handle:
        if not _lock(handle):
            return True
        _unlock(handle)
    return False
