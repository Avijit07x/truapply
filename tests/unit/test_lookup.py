from collections.abc import Sequence
from dataclasses import replace
from pathlib import Path

import pytest

from tests.unit import samples
from truapply.core.models import Ats, Board, Job
from truapply.sources import lookup
from truapply.sources.ats import PollResult
from truapply.sources.lookup import entries_in, look_up, slugs


def test_names_and_websites_become_board_names_to_try() -> None:
    assert slugs("Sarvam AI") == ["sarvamai", "sarvam-ai", "sarvam"]
    assert slugs("https://www.zinier.com/careers") == ["zinier"]
    assert slugs("Interview Kickstart") == ["interviewkickstart", "interview-kickstart"]


def test_a_pasted_list_is_split_into_companies() -> None:
    assert entries_in("Zinier, Glance\n\nzinier.com; Glance") == ["Zinier", "Glance", "zinier.com"]


def test_only_boards_with_jobs_in_your_country_are_found(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def job(board: str, location: str) -> Job:
        return replace(samples.job(external_id=f"{board}/1"), location=location)

    def polled(tried: Sequence[Board]) -> PollResult:
        alive = {"greenhouse/northwind": "Bengaluru, India", "lever/tcs": "Banbury, UK"}
        jobs = [job(board.key, alive[board.key]) for board in tried if board.key in alive]
        return PollResult(jobs, [], [], [])

    monkeypatch.setattr(lookup, "poll", polled)
    found = look_up(["Northwind", "tcs.com"], samples.profile(tmp_path / "master.tex"))
    assert found.found == [Board(Ats.GREENHOUSE, "northwind", "Northwind")]
    assert found.missing == ["tcs.com"]
