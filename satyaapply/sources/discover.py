import csv
from importlib import resources

from satyaapply.core.models import Ats, Board

SHARED_LIST = "companies.csv"


def shared_boards() -> list[Board]:
    content = resources.files("satyaapply.sources").joinpath(SHARED_LIST).read_text("utf-8")
    return [
        Board(Ats(row["ats"]), row["slug"], row["company"])
        for row in csv.DictReader(content.splitlines())
    ]


def as_csv_rows(boards: list[Board]) -> list[str]:
    return [
        f"{board.ats},{board.slug},{board.company or board.slug},"
        for board in sorted(boards, key=lambda board: (board.ats, board.slug))
    ]
