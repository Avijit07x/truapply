import csv
import re
from importlib import resources

from satyaapply.core.models import Ats
from satyaapply.sources.discover import SHARED_LIST, shared_boards

COLUMNS = ["ats", "slug", "company", "tags"]
SLUG = re.compile(r"^[\w.%-]+$")
TAGS = frozenset({"india", "remote"})


def rows() -> list[dict[str, str]]:
    content = resources.files("satyaapply.sources").joinpath(SHARED_LIST).read_text("utf-8")
    reader = csv.DictReader(content.splitlines())
    assert reader.fieldnames == COLUMNS
    return list(reader)


def test_the_shared_list_is_sorted_and_has_no_duplicates() -> None:
    keys = [(row["ats"], row["slug"]) for row in rows()]
    assert keys == sorted(keys)
    assert len(keys) == len(set(keys))


def test_every_row_is_valid() -> None:
    for row in rows():
        assert row["ats"] in {ats.value for ats in Ats}, row
        assert SLUG.match(row["slug"]), row
        assert row["company"].strip(), row
        assert set(filter(None, row["tags"].split(";"))) <= TAGS, row


def test_the_shared_list_has_at_least_a_hundred_boards() -> None:
    assert len(shared_boards()) >= 100
