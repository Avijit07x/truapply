import re
from collections.abc import Sequence

from truapply.core.models import normalize

TRUTHY = frozenset({"yes", "y", "true", "checked", "1", "agree", "i agree", "accept"})
NUMBER = re.compile(r"-?\d+(?:\.\d+)?")


def best_option(options: Sequence[str], answer: str) -> int | None:
    wanted = normalize(answer)
    if not wanted:
        return None
    names = [normalize(option) for option in options]
    for index, name in enumerate(names):
        if name == wanted:
            return index
    for index, name in enumerate(names):
        if name and (name.startswith(f"{wanted} ") or wanted.startswith(f"{name} ")):
            return index
    for index, name in enumerate(names):
        if name and f" {wanted} " in f" {name} ":
            return index
    words = set(wanted.split())
    for index, name in enumerate(names):
        if words <= set(name.split()):
            return index
    return None


def is_truthy(answer: str) -> bool:
    return normalize(answer) in TRUTHY


def as_number(answer: str) -> str | None:
    match = NUMBER.search(answer)
    return match.group(0) if match else None
