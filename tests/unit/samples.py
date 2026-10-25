from pathlib import Path

from satyaapply.core.documents import ResumeData, ResumeEntry, ResumeFormat, ResumeSection
from satyaapply.core.models import Job, Source
from satyaapply.core.profile import (
    CoverLetter,
    Profile,
    ResumeRef,
    Salary,
    SubmitMode,
    UnknownQuestions,
    WorkPlaces,
)


def profile(resume_path: Path) -> Profile:
    return Profile(
        name="Asha Rao",
        email="asha.rao@example.com",
        phone="+91 90000 00000",
        city="Bengaluru",
        country="India",
        links=("https://github.com/asharao",),
        current_company="Acme Analytics",
        years_experience=2.5,
        resume=ResumeRef(ResumeFormat.LATEX, resume_path),
        roles=("Frontend Engineer",),
        title_keywords=("frontend", "react"),
        title_exclude=("senior",),
        work_places=WorkPlaces(True, True, False, (), False),
        sites=(Source.CAREER_PAGES,),
        submit_mode=SubmitMode.TRUST,
        unknown_questions=UnknownQuestions.SKIP,
        daily_cap=20,
        cover_letter=CoverLetter.REQUIRED,
        skip_companies=("Acme Analytics",),
        notice_period="30 days",
        citizenship="India",
        work_without_visa=("India",),
        needs_sponsorship_elsewhere=True,
        salary=Salary("INR", 1_200_000, 1_800_000, 800_000),
        dob=None,
        diversity=None,
        extra_facts="",
    )


def job(
    source: Source = Source.CAREER_PAGES, external_id: str = "42", company: str = "Northwind"
) -> Job:
    return Job(
        source,
        external_id,
        f"https://jobs.example.com/{external_id}",
        company,
        "Frontend Engineer",
        description="React and TypeScript dashboards.",
    )


def resume_data() -> ResumeData:
    return ResumeData(
        name="Asha Rao",
        headline="Frontend Engineer",
        contact=("asha.rao@example.com", "Bengaluru"),
        sections=(
            ResumeSection("Summary", ("Frontend engineer with 2+ years of React.",), ()),
            ResumeSection(
                "Experience",
                (),
                (
                    ResumeEntry(
                        "Acme Analytics",
                        "Frontend Engineer",
                        "2024 - Present",
                        "Bengaluru",
                        ("Built 40 shared components.", "Cut load time by 30%."),
                    ),
                ),
            ),
        ),
    )
