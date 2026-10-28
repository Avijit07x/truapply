from collections.abc import Iterator, Sequence
from contextlib import closing
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

import pytest

from tests.unit import samples
from tests.unit.tracker_api import post, running
from truapply.core.models import Ats, Board
from truapply.core.paths import Paths
from truapply.core.profile import save
from truapply.sources import intake
from truapply.sources.ats import PollResult
from truapply.sources.intake import NOT_A_BOARD
from truapply.store import boards, records
from truapply.store.boards import BoardOrigin
from truapply.store.db import connect
from truapply.tracker.server import TrackerServer

NOW = datetime(2026, 10, 26, 12, 0, tzinfo=UTC)
LINK = "https://job-boards.greenhouse.io/northwindcareers/jobs/4707747006?gh_jid=4707747006"


@pytest.fixture
def tracker(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[TrackerServer]:
    fitting = samples.job(external_id="greenhouse/northwindcareers/111")
    linked = replace(
        samples.job(external_id="greenhouse/northwindcareers/4707747006"), title="Office Manager"
    )
    unwanted = replace(
        samples.job(external_id="greenhouse/northwindcareers/222"), title="Office Manager"
    )

    def polled(checked: Sequence[Board]) -> PollResult:
        return PollResult([fitting, linked, unwanted], list(checked), [], [])

    monkeypatch.setattr(intake, "poll", polled)
    paths = Paths(tmp_path / "home")
    paths.ensure()
    master = tmp_path / "master.tex"
    master.write_text("resume", encoding="utf-8")
    save(paths, samples.profile(master))
    with running(paths) as server:
        yield server


def test_a_pasted_job_link_adds_its_company_and_keeps_that_job(tracker: TrackerServer) -> None:
    code, added = post(tracker, "/api/boards/link", {"link": LINK})
    assert (code, added["open"], added["kept"], added["added"]) == (200, 3, 2, 2)
    with closing(connect(tracker.paths.database)) as db:
        linked = boards.by_origin(db, BoardOrigin.LINK)
        found = [records.find(db, job_id) for job_id in (1, 2)]
    kept = {record.job.external_id for record in found if record}
    assert linked == [Board(Ats.GREENHOUSE, "northwindcareers", linked[0].company)]
    assert kept == {"greenhouse/northwindcareers/111", "greenhouse/northwindcareers/4707747006"}


@pytest.mark.parametrize("link", ["https://www.linkedin.com/jobs/view/123", "not a link", ""])
def test_links_from_other_sites_are_refused(tracker: TrackerServer, link: str) -> None:
    assert post(tracker, "/api/boards/link", {"link": link}) == (400, {"error": NOT_A_BOARD})
