from contextlib import redirect_stdout
from dataclasses import replace
from io import StringIO
from pathlib import Path

from tests.unit import samples
from truapply.cli import _print_run
from truapply.core.models import Status
from truapply.resume.tailor import Tailored
from truapply.run import RunReport
from truapply.run.discovery import Discovery
from truapply.run.scoring import Scoring, _outcome
from truapply.run.tailoring import Prepared
from truapply.tracker.run_report import report_of


def _prepared(company: str, title: str, original: bool = False) -> Prepared:
    resume = Tailored(Path("resume.pdf"), "", original, (), ())
    return Prepared(replace(samples.job(company=company), title=title), resume)


def _printed(report: RunReport) -> list[str]:
    out = StringIO()
    with redirect_stdout(out):
        _print_run(report)
    return out.getvalue().splitlines()


FOUND = Discovery(boards=668, new_boards=2, found=48_345, kept=666, added=3, dead=1, unreachable=6)
PROGRESS = [
    "Manual run",
    "Scoring 3 jobs with AI …",
    f"  1/3 Acme · Frontend Engineer: {_outcome(Status.SCORED, 84, 'React matches')}",
    f"  2/3 Commvault · Engineer: Python: {_outcome(Status.SKIPPED, 40, 'deal-breaker: Python')}",
    "  3/3 Zeta · Dev: couldn't score it, will retry next run",
    f"  3/3 Globex · UI: {_outcome(Status.SKIPPED, 52, 'score 52: - asks 6 years')}",
    "  Beta · Dev: skipped, same job as one you already have",
]


def test_the_report_reads_the_numbers_and_each_scored_job() -> None:
    lines = PROGRESS + _printed(RunReport(FOUND, Scoring(1, 2, 1), []))
    report = report_of(lines)
    assert report is not None
    assert report["companies"] == {"checked": 668, "new": 2, "gone": 1, "unreachable": 6}
    assert report["jobs"] == {"open": 48_345, "fit": 666, "new": 3}
    assert report["scored"] == {"good": 1, "skipped": 2, "retry": 1}
    assert report["prepared"] == []
    assert report["results"] == [
        {
            "company": "Acme",
            "title": "Frontend Engineer",
            "result": "good",
            "score": 84,
            "note": "",
        },
        {
            "company": "Commvault",
            "title": "Engineer: Python",
            "result": "skipped",
            "score": None,
            "note": "deal-breaker: Python",
        },
        {"company": "Zeta", "title": "Dev", "result": "retry", "score": None, "note": ""},
        {
            "company": "Globex",
            "title": "UI",
            "result": "skipped",
            "score": 52,
            "note": "- asks 6 years",
        },
        {
            "company": "Beta",
            "title": "Dev",
            "result": "skipped",
            "score": None,
            "note": "same job as one you already have",
        },
    ]


def test_the_report_lists_jobs_made_ready() -> None:
    ready = [_prepared("Acme", "Frontend Engineer"), _prepared("Beta", "Dev", original=True)]
    report = report_of(_printed(RunReport(FOUND, Scoring(2, 0, 0), ready)))
    assert report is not None
    assert report["prepared"] == [
        {"company": "Acme", "title": "Frontend Engineer"},
        {"company": "Beta", "title": "Dev"},
    ]


def test_a_failed_run_reports_its_error_and_what_it_got_to() -> None:
    lines = [
        "Automatic run",
        "Checking company career pages …",
        "  48,120 open jobs · 1 new ones fit your titles and places",
        "Scoring 1 job with AI …",
        "✘ Today's Claude call budget is used up.",
        "  → Change it in Settings → Applying → Claude calls per day.",
    ]
    report = report_of(lines)
    assert report is not None
    assert report["jobs"] == {"open": 48_120, "fit": None, "new": 1}
    assert report["error"] == {
        "message": "Today's Claude call budget is used up.",
        "hint": "Change it in Settings → Applying → Claude calls per day.",
        "fix": "/settings?tab=applying",
    }
    assert report["companies"] is None


def test_a_hint_that_repeats_the_error_is_shown_once() -> None:
    lines = ["✘ Budget is used up.", "  → Budget is used up, so the run stopped."]
    report = report_of(lines)
    assert report is not None
    assert report["error"] == {
        "message": "Budget is used up, so the run stopped.",
        "hint": "",
        "fix": "",
    }


def test_a_run_that_did_nothing_yet_has_no_report() -> None:
    assert report_of(["Manual run", "Checking company career pages …"]) is None
