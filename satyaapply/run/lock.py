from contextlib import AbstractContextManager

from satyaapply.core.errors import RunAlreadyGoingError
from satyaapply.core.locks import held
from satyaapply.core.paths import Paths

ALREADY_RUNNING = "Another run is already running."


def run_lock(paths: Paths) -> AbstractContextManager[None]:
    return held(paths.lock, RunAlreadyGoingError(ALREADY_RUNNING))
