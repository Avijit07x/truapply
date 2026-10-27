from datetime import UTC, datetime

import pytest

from satyaapply.browser.fetch import Response
from satyaapply.core.models import Ats, Board, Source
from satyaapply.sources import ats
from satyaapply.sources.ats import board_of, boards_in, poll, still_open
from satyaapply.sources.ats.ashby import READER as ASHBY
from satyaapply.sources.ats.greenhouse import READER as GREENHOUSE
from satyaapply.sources.ats.lever import READER as LEVER

GREENHOUSE_DATA = {
    "jobs": [
        {
            "id": 101,
            "title": "Frontend Engineer",
            "company_name": "Northwind",
            "location": {"name": "Bengaluru, India"},
            "content": (
                "&lt;p&gt;Build &lt;b&gt;React&lt;/b&gt; dashboards.&lt;/p&gt;"
                "&lt;ul&gt;&lt;li&gt;TypeScript&lt;/li&gt;&lt;/ul&gt;"
            ),
            "first_published": "2026-10-20T10:00:00-04:00",
        },
        {"id": 102, "title": ""},
        "not a job",
    ]
}
LEVER_DATA = [
    {
        "id": "abc-1",
        "text": "UI Engineer",
        "categories": {"location": "Pune"},
        "workplaceType": "remote",
        "hostedUrl": "https://jobs.lever.co/contoso/abc-1",
        "applyUrl": "https://jobs.lever.co/contoso/abc-1/apply",
        "createdAt": 1792000000000,
        "descriptionPlain": "Work on our design system.",
        "lists": [{"text": "You have", "content": "<li>React</li><li>CSS</li>"}],
        "additionalPlain": "Equal opportunity employer.",
    }
]
ASHBY_DATA = {
    "jobs": [
        {
            "id": "uuid-1",
            "title": "Product Engineer",
            "location": "Bengaluru",
            "secondaryLocations": [{"location": "Hyderabad"}],
            "isRemote": True,
            "jobUrl": "https://jobs.ashbyhq.com/fabrikam/uuid-1",
            "applyUrl": "https://jobs.ashbyhq.com/fabrikam/uuid-1/application",
            "publishedAt": "2026-10-21T08:00:00.000+00:00",
            "descriptionPlain": "Ship features end to end.",
        },
        {"id": "uuid-2", "title": "Hidden", "jobUrl": "https://x", "isListed": False},
    ]
}


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("https://job-boards.greenhouse.io/vercel/jobs/123", Board(Ats.GREENHOUSE, "vercel")),
        ("https://boards.greenhouse.io/embed/job_board?for=figma", Board(Ats.GREENHOUSE, "figma")),
        ("https://jobs.lever.co/weekdayworks/84b3", Board(Ats.LEVER, "weekdayworks")),
        ("https://jobs.ashbyhq.com/bidgely-inc/3640", Board(Ats.ASHBY, "bidgely-inc")),
        ("https://example.com/careers", None),
        ("https://jobs.lever.co/api/x", None),
    ],
)
def test_boards_are_recognised_from_posting_links(url: str, expected: Board | None) -> None:
    assert board_of(url) == expected


def test_the_same_board_is_listed_once() -> None:
    urls = ["https://jobs.lever.co/acme/1", "https://jobs.lever.co/acme/2"]
    assert boards_in(urls) == [Board(Ats.LEVER, "acme")]


def test_a_greenhouse_posting_counts_from_its_latest_update() -> None:
    posting = {
        "id": 7,
        "title": "Frontend Developer",
        "first_published": "2026-09-14T10:44:18-04:00",
        "updated_at": "2026-10-23T07:00:26-04:00",
    }
    [job] = GREENHOUSE.parse(Board(Ats.GREENHOUSE, "northwind"), {"jobs": [posting]})
    assert job.posted_at == datetime(2026, 10, 23, 11, 0, 26, tzinfo=UTC)


def test_greenhouse_postings_are_parsed_and_bad_ones_skipped() -> None:
    jobs = GREENHOUSE.parse(Board(Ats.GREENHOUSE, "northwind"), GREENHOUSE_DATA)
    assert len(jobs) == 1
    job = jobs[0]
    assert job.key == "career_pages:greenhouse/northwind/101"
    assert job.url == "https://job-boards.greenhouse.io/northwind/jobs/101"
    assert job.apply_url == "https://job-boards.greenhouse.io/embed/job_app?for=northwind&token=101"
    assert job.location == "Bengaluru, India"
    assert job.description == "Build React dashboards.\n\n- TypeScript"
    assert job.posted_at == datetime(2026, 10, 20, 14, 0, tzinfo=UTC)
    assert job.board == Board(Ats.GREENHOUSE, "northwind", "Northwind")


def test_lever_postings_include_every_section_and_remote() -> None:
    job = LEVER.parse(Board(Ats.LEVER, "contoso"), LEVER_DATA)[0]
    assert (job.title, job.company, job.location) == ("UI Engineer", "Contoso", "Pune (Remote)")
    assert job.apply_url.endswith("/apply")
    assert "- React" in job.description
    assert "Equal opportunity employer." in job.description


def test_ashby_postings_combine_locations_and_skip_unlisted() -> None:
    jobs = ASHBY.parse(Board(Ats.ASHBY, "fabrikam"), ASHBY_DATA)
    assert [job.title for job in jobs] == ["Product Engineer"]
    assert jobs[0].location == "Remote - Bengaluru / Remote - Hyderabad"
    assert jobs[0].source is Source.CAREER_PAGES


@pytest.mark.parametrize(
    ("places", "location"),
    [
        (
            {"location": "New York", "secondaryLocations": [{"location": "San Francisco"}]}
            | {"isRemote": True, "workplaceType": "Hybrid"},
            "New York / San Francisco",
        ),
        ({"location": "Europe", "isRemote": True, "workplaceType": "Remote"}, "Remote - Europe"),
        (
            {"location": "Remote", "secondaryLocations": [{"location": "Poland"}]}
            | {"workplaceType": "Remote"},
            "Remote - Poland",
        ),
        ({"location": "Remote", "workplaceType": "Remote"}, "Remote"),
        ({"location": "Remote - EMEA", "workplaceType": "Remote"}, "Remote - EMEA"),
        ({"location": "Tokyo, Japan"}, "Tokyo, Japan"),
    ],
)
def test_ashby_remote_stays_tied_to_its_places(places: dict[str, object], location: str) -> None:
    posting = {"id": "uuid-9", "title": "Engineer", "jobUrl": "https://jobs.ashbyhq.com/f/9"}
    [job] = ASHBY.parse(Board(Ats.ASHBY, "fabrikam"), {"jobs": [posting | places]})
    assert job.location == location


def test_polling_sorts_boards_into_alive_dead_and_unreachable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    replies = {
        GREENHOUSE.list_url("northwind"): Response("a", 200, GREENHOUSE_DATA),
        LEVER.list_url("gone"): Response("b", 404, None),
        ASHBY.list_url("flaky"): Response("c", 0, None),
    }
    monkeypatch.setattr(ats, "fetch_json", lambda urls: [replies[url] for url in urls])
    boards = [
        Board(Ats.GREENHOUSE, "northwind"),
        Board(Ats.LEVER, "gone"),
        Board(Ats.ASHBY, "flaky"),
    ]
    result = poll(boards)
    assert [job.title for job in result.jobs] == ["Frontend Engineer"]
    assert result.alive == [boards[0]]
    assert result.dead == [boards[1]]
    assert result.unreachable == [boards[2]]


def test_a_removed_posting_is_reported_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    open_job = GREENHOUSE.parse(Board(Ats.GREENHOUSE, "northwind"), GREENHOUSE_DATA)[0]
    ashby_job = ASHBY.parse(Board(Ats.ASHBY, "fabrikam"), ASHBY_DATA)[0]
    replies = {
        GREENHOUSE.posting_url("northwind", "101"): Response("a", 404, None),
        ASHBY.list_url("fabrikam"): Response("b", 200, ASHBY_DATA),
    }
    monkeypatch.setattr(ats, "fetch_json", lambda urls: [replies[url] for url in urls])
    assert still_open([open_job, ashby_job]) == [False, True]
