from collections.abc import Callable
from dataclasses import dataclass
from functools import cached_property

from satyaapply.core.clock import Clock
from satyaapply.core.paths import Paths
from satyaapply.core.profile import Profile
from satyaapply.resume.contract import Rendered, Resume

PARALLEL_AI_CALLS = 4

Progress = Callable[[str], None]


def quiet(_message: str) -> None:
    return None


@dataclass(frozen=True)
class RunContext:
    paths: Paths
    profile: Profile
    resume: Resume
    master: Rendered
    clock: Clock
    progress: Progress = quiet
    notes: tuple[str, ...] = ()
    preferences: tuple[str, ...] = ()

    @cached_property
    def resume_text(self) -> str:
        return self.resume.readable(self.resume.source)
