from pathlib import Path

import pytest

from satyaapply.ai import tasks
from satyaapply.ai.client import Request
from satyaapply.ai.job_prompts import SEARCH_HOSTS
from satyaapply.ai.replies import FoundPostings
from satyaapply.core.errors import AIError, UsageLimitError
from tests.unit import samples

FOUND = {
    SEARCH_HOSTS[0]: ("https://job-boards.greenhouse.io/northwind/jobs/1",),
    SEARCH_HOSTS[1]: (
        "https://jobs.lever.co/acme/2",
        "https://job-boards.greenhouse.io/northwind/jobs/1",
    ),
    SEARCH_HOSTS[2]: ("https://jobs.ashbyhq.com/zeta/3",),
}


def host_of(request: Request) -> str:
    return next(hosts for hosts in SEARCH_HOSTS if f"hosted on {hosts}," in request.prompt)


def test_each_job_site_gets_its_own_search_and_links_are_merged_once(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    asked: list[str] = []

    def ask(_shape: type[FoundPostings], request: Request) -> FoundPostings:
        asked.append(host_of(request))
        return FoundPostings(FOUND[host_of(request)])

    monkeypatch.setattr(tasks, "ask", ask)
    urls = tasks.find_posting_urls(samples.profile(Path("master.tex")))
    assert sorted(asked) == sorted(SEARCH_HOSTS)
    assert urls == (
        "https://job-boards.greenhouse.io/northwind/jobs/1",
        "https://jobs.lever.co/acme/2",
        "https://jobs.ashbyhq.com/zeta/3",
    )


def test_one_failed_search_keeps_the_others_but_all_failing_is_an_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def flaky(_shape: type[FoundPostings], request: Request) -> FoundPostings:
        if host_of(request) == SEARCH_HOSTS[1]:
            raise AIError("search failed")
        return FoundPostings(FOUND[host_of(request)])

    monkeypatch.setattr(tasks, "ask", flaky)
    assert len(tasks.find_posting_urls(samples.profile(Path("master.tex")))) == 2

    def broken(_shape: type[FoundPostings], _request: Request) -> FoundPostings:
        raise AIError("search failed")

    monkeypatch.setattr(tasks, "ask", broken)
    with pytest.raises(AIError):
        tasks.find_posting_urls(samples.profile(Path("master.tex")))

    def spent(_shape: type[FoundPostings], _request: Request) -> FoundPostings:
        raise UsageLimitError("out of calls")

    monkeypatch.setattr(tasks, "ask", spent)
    with pytest.raises(UsageLimitError):
        tasks.find_posting_urls(samples.profile(Path("master.tex")))
