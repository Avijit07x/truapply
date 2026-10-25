import pytest

from satyaapply.core.models import Ats
from satyaapply.sources.ats import poll
from satyaapply.sources.discover import shared_boards

pytestmark = pytest.mark.network

BOARDS_PER_SYSTEM = {Ats.GREENHOUSE: 8, Ats.ASHBY: 7, Ats.LEVER: 5}


def test_twenty_real_boards_give_complete_jobs() -> None:
    boards = [
        board
        for ats, count in BOARDS_PER_SYSTEM.items()
        for board in [b for b in shared_boards() if b.ats is ats][:count]
    ]
    assert len(boards) == sum(BOARDS_PER_SYSTEM.values())
    result = poll(boards)
    assert not result.unreachable
    assert result.jobs
    incomplete = [
        (job.key, field)
        for job in result.jobs
        for field, value in (
            ("title", job.title),
            ("company", job.company),
            ("url", job.url),
            ("apply_url", job.apply_url),
            ("location", job.location),
            ("description", job.description),
        )
        if not value.strip()
    ]
    share = len(incomplete) / len(result.jobs)
    assert not incomplete, (
        f"{len(incomplete)} gaps in {len(result.jobs)} jobs ({share:.1%}): {incomplete[:10]}"
    )
