import threading
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field

from truapply.core.errors import DailyBudgetError

SPENT = "Today's Claude call budget is used up."


@dataclass
class Budget:
    left: int
    used: int = 0
    guard: threading.Lock = field(default_factory=threading.Lock, repr=False, compare=False)

    def spend(self) -> None:
        with self.guard:
            if self.left <= 0:
                raise DailyBudgetError(SPENT)
            self.left -= 1
            self.used += 1


ACTIVE: list[Budget] = []


@contextmanager
def metered(budget: Budget) -> Iterator[Budget]:
    ACTIVE.append(budget)
    try:
        yield budget
    finally:
        ACTIVE.remove(budget)


def charge() -> None:
    for budget in ACTIVE:
        budget.spend()
