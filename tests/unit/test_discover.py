from truapply.core.models import Ats, Board
from truapply.sources.discover import as_csv_rows


def test_shared_rows_read_cleanly_and_list_each_company_once() -> None:
    found = [
        Board(Ats.ASHBY, "Deel", "Deel"),
        Board(Ats.ASHBY, "deel", "deel"),
        Board(Ats.ASHBY, "Fermi%20AI", "Fermi%20AI"),
        Board(Ats.LEVER, "contoso"),
    ]
    assert as_csv_rows(found) == [
        "ashby,Deel,Deel,",
        "ashby,Fermi%20AI,Fermi AI,",
        "lever,contoso,contoso,",
    ]
