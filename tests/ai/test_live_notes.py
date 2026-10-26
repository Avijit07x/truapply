from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from difflib import SequenceMatcher
from pathlib import Path

import pytest

from satyaapply.core.documents import ResumeData, ResumeEntry, ResumeSection
from satyaapply.core.models import Job
from satyaapply.resume.structured import StructuredResume, from_json
from satyaapply.resume.tailor import Tailored, TailorRequest, tailor
from tests.unit import samples

pytestmark = pytest.mark.ai

NOTES = ("Keep my bullet points in their original order.",)
EXPERIENCE = (
    ResumeEntry(
        "Acme Analytics",
        "Frontend Engineer",
        "2024 - Present",
        "Bengaluru",
        (
            "Ran weekly office hours for new hires.",
            "Wrote internal docs for the release process.",
            "Built 40 shared React components with Storybook docs and theming.",
            "Cut page load time by 30% with code splitting and lazy loading.",
        ),
    ),
    ResumeEntry(
        "Globex",
        "Software Engineer Intern",
        "2023 - 2024",
        "Pune",
        (
            "Fixed bugs reported by the support team.",
            "Wrote Jest tests for the checkout flow.",
            "Built a Node.js REST API backed by PostgreSQL.",
            "Built analytics dashboards with React and a charting library.",
        ),
    ),
)
JOBS = (
    (
        "Northwind",
        "Frontend Engineer, Testing",
        "Build customer-facing React screens. We care most about automated testing with Jest "
        "and a reliable checkout.",
    ),
    (
        "Contoso",
        "Full-stack Engineer",
        "Own features across a React frontend and a Node.js REST API on PostgreSQL.",
    ),
    (
        "Fabrikam",
        "Design Systems Engineer",
        "Grow our component library: React components, Storybook docs, tokens and theming, "
        "used by twelve product teams.",
    ),
    (
        "Tailspin",
        "Frontend Engineer, Dashboards",
        "Build analytics dashboards with React and charting libraries. Large tables, filters "
        "and real-time data.",
    ),
    (
        "Litware",
        "Web Performance Engineer",
        "Make our web app fast: Core Web Vitals, code splitting, lazy loading, bundle size and "
        "load time budgets.",
    ),
)


def master() -> StructuredResume:
    data = samples.resume_data()
    sections = (
        ResumeSection("Summary", ("Frontend engineer with 2+ years of React.",), ()),
        ResumeSection("Experience", (), EXPERIENCE),
        ResumeSection("Skills", ("React, TypeScript, Node.js, PostgreSQL, Jest, Storybook",), ()),
    )
    return StructuredResume(replace(data, sections=sections))


def jobs() -> list[Job]:
    return [
        replace(samples.job(external_id=str(index), company=company), title=title, description=text)
        for index, (company, title, text) in enumerate(JOBS)
    ]


def closest(bullet: str, originals: tuple[str, ...]) -> int:
    scores = [SequenceMatcher(None, bullet, original).ratio() for original in originals]
    return scores.index(max(scores))


def reordered(data: ResumeData) -> list[str]:
    originals = {entry.heading: entry.bullets for entry in EXPERIENCE}
    entries = [entry for section in data.sections for entry in section.entries]
    return [
        f"{entry.heading}: {list(entry.bullets)}"
        for entry in entries
        if entry.heading in originals
        and (order := [closest(bullet, originals[entry.heading]) for bullet in entry.bullets])
        != sorted(set(order))
    ]


def broken_note(job: Job, result: Tailored) -> str | None:
    if result.used_original:
        return f"{job.title}: not tailored ({'; '.join(result.problems)})"
    moved = reordered(from_json(result.source))
    return f"{job.title}: bullets reordered in {moved}" if moved else None


def tailored_for_five_jobs(notes: tuple[str, ...], tmp_path: Path) -> list[str | None]:
    resume = master()
    original = resume.render(resume.source, tmp_path / "master.pdf")

    def tailor_for(job: Job) -> Tailored:
        request = TailorRequest(job, notes, tmp_path / job.external_id, "Resume.pdf", original)
        return tailor(resume, request)

    targets = jobs()
    with ThreadPoolExecutor(max_workers=5) as pool:
        results = list(pool.map(tailor_for, targets))
    return [broken_note(job, result) for job, result in zip(targets, results, strict=True)]


def test_a_bullet_order_note_holds_for_five_tailored_resumes(tmp_path: Path) -> None:
    broken = tailored_for_five_jobs(NOTES, tmp_path)
    assert broken == [None] * len(JOBS), "\n".join(filter(None, broken))
