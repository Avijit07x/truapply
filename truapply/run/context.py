from collections.abc import Callable
from dataclasses import dataclass
from functools import cached_property

from truapply.core.clock import Clock
from truapply.core.paths import Paths
from truapply.core.profile import Profile
from truapply.resume.contract import Rendered, Resume

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
