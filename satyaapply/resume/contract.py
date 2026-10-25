from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from satyaapply.core.models import Job


@dataclass(frozen=True)
class Draft:
    source: str
    changes: tuple[str, ...]


@dataclass(frozen=True)
class Rendered:
    pdf: Path
    pages: int


class Resume(Protocol):
    @property
    def source(self) -> str: ...

    @property
    def suffix(self) -> str: ...

    def readable(self, source: str) -> str: ...

    def draft(self, job: Job, notes: Sequence[str]) -> Draft: ...

    def revise(self, draft: Draft, problems: Sequence[str]) -> Draft: ...

    def problems(self, draft: Draft) -> list[str]: ...

    def render(self, source: str, target: Path) -> Rendered: ...
