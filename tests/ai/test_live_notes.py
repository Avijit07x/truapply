from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from pathlib import Path

import pytest

from satyaapply.core.documents import ResumeData, ResumeSection
from satyaapply.core.models import Job
from satyaapply.resume.structured import StructuredResume, from_json
from satyaapply.resume.tailor import Tailored, TailorRequest, tailor
from tests.unit import samples

pytestmark = pytest.mark.ai

NOTES = ("Don't change my summary.",)
JOBS = (
    (
        "Northwind",
        "Frontend Engineer",
        "Build customer-facing React and TypeScript screens. Care about clean UI code, "
        "testing with Jest and shipping weekly.",
    ),
    (
        "Contoso",
        "Full-stack Engineer",
        "Own features across a React frontend and a Node.js API. TypeScript everywhere, "
        "PostgreSQL, REST and GraphQL.",
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
        "Build analytics dashboards with React, TypeScript and charting libraries. Large "
        "tables, filters and real-time data.",
    ),
    (
        "Litware",
        "Web Performance Engineer",
        "Make our web app fast: Core Web Vitals, Lighthouse audits, code splitting, bundle "
        "size and load time budgets.",
    ),
)


def master() -> StructuredResume:
    data = samples.resume_data()
    skills = ResumeSection("Skills", ("React, TypeScript, Storybook, Jest, Lighthouse",), ())
    return StructuredResume(replace(data, sections=(*data.sections, skills)))


def jobs() -> list[Job]:
    return [
        replace(samples.job(external_id=str(index), company=company), title=title, description=text)
        for index, (company, title, text) in enumerate(JOBS)
    ]


def summary(data: ResumeData) -> ResumeSection | None:
    return next((section for section in data.sections if section.title == "Summary"), None)


def broken_note(job: Job, result: Tailored, original: ResumeSection | None) -> str | None:
    if result.used_original:
        return f"{job.title}: not tailored ({'; '.join(result.problems)})"
    tailored = summary(from_json(result.source))
    return None if tailored == original else f"{job.title}: summary became {tailored!r}"


def test_a_summary_note_holds_for_five_tailored_resumes(tmp_path: Path) -> None:
    resume = master()
    original = resume.render(resume.source, tmp_path / "master.pdf")

    def tailor_for(job: Job) -> Tailored:
        request = TailorRequest(job, NOTES, tmp_path / job.external_id, "Resume.pdf", original)
        return tailor(resume, request)

    targets = jobs()
    with ThreadPoolExecutor(max_workers=5) as pool:
        results = list(pool.map(tailor_for, targets))
    kept = summary(resume.data)
    pairs = zip(targets, results, strict=True)
    broken = [broken_note(job, result, kept) for job, result in pairs]
    assert broken == [None] * len(JOBS), "\n".join(filter(None, broken))
