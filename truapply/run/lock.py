from contextlib import AbstractContextManager

from truapply.core.errors import RunAlreadyGoingError
from truapply.core.locks import held
from truapply.core.paths import Paths

ALREADY_RUNNING = "Another run is already running."


def run_lock(paths: Paths) -> AbstractContextManager[None]:
    return held(paths.lock, RunAlreadyGoingError(ALREADY_RUNNING))
