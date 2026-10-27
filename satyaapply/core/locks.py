import fcntl
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from satyaapply.core.errors import SatyaApplyError


@contextmanager
def held(path: Path, busy: SatyaApplyError) -> Iterator[None]:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as handle:
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise busy from None
        yield


def is_held(path: Path) -> bool:
    if not path.is_file():
        return False
    with path.open("a") as handle:
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return True
        fcntl.flock(handle, fcntl.LOCK_UN)
    return False
