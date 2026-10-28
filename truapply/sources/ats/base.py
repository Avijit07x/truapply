import re
from collections.abc import Callable
from dataclasses import dataclass

from truapply.core.models import Ats, Board, Job


@dataclass(frozen=True)
class AtsReader:
    ats: Ats
    board_url: re.Pattern[str]
    list_url: Callable[[str], str]
    posting_url: Callable[[str, str], str | None]
    parse: Callable[[Board, object], list[Job]]


def external_id(board: Board, posting_id: str) -> str:
    return f"{board.ats}/{board.slug}/{posting_id}"


def company_name(board: Board) -> str:
    return board.company or board.slug.replace("-", " ").title()
