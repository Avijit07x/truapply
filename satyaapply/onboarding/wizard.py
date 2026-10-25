from pathlib import Path

from satyaapply.ai import tasks
from satyaapply.ai.replies import ProfileDraft
from satyaapply.core.documents import ResumeDocument, ResumeFormat
from satyaapply.core.errors import SatyaApplyError, SetupCancelledError
from satyaapply.core.files import write_private
from satyaapply.core.paths import Paths
from satyaapply.core.profile import Profile, ResumeRef, save
from satyaapply.onboarding import ask, steps
from satyaapply.onboarding.ask import Option
from satyaapply.onboarding.latex import install_tinytex
from satyaapply.resume.contract import Resume
from satyaapply.resume.importer import read_document
from satyaapply.resume.latex import LatexResume, split_document
from satyaapply.resume.master import master_pdf
from satyaapply.resume.render import find_pdflatex
from satyaapply.resume.structured import StructuredResume, to_json

NEXT_STEPS = (
    "satyaapply doctor                       check that everything works",
    "satyaapply tailor JOB.txt --company … --title …   preview a tailored resume",
)


def _pdflatex() -> Path | None:
    found = find_pdflatex()
    if found:
        return found
    choice = ask.choose(
        "Your resume is LaTeX. Building it needs pdflatex, which isn't installed.",
        [
            Option(
                "Install TinyTeX now",
                "install",
                "About 100 MB, no admin password, official installer.",
            ),
            Option("I'll install LaTeX myself, then run setup again", "exit"),
            Option(
                "Use the built-in resume design instead",
                "structured",
                "Your resume's content moves into a clean one-column design.",
            ),
        ],
    )
    if choice == "exit":
        raise SetupCancelledError("Install LaTeX (pdflatex), then run setup again.")
    if choice == "structured":
        return None
    ask.say("Installing TinyTeX. This takes a minute or two …")
    return install_tinytex()


def _store_structured(paths: Paths, document: ResumeDocument) -> tuple[ResumeRef, Resume]:
    ask.say("Moving your resume into the built-in design with Claude …")
    data = tasks.convert_resume(document)
    target = paths.resume_dir / "master.json"
    write_private(target, to_json(data))
    return ResumeRef(ResumeFormat.STRUCTURED, target), StructuredResume(data)


def store_resume(paths: Paths, document: ResumeDocument) -> tuple[ResumeRef, Resume]:
    if document.path.suffix.lower() != ".tex" or document.text is None:
        return _store_structured(paths, document)
    split_document(document.text)
    pdflatex = _pdflatex()
    if pdflatex is None:
        return _store_structured(paths, document)
    target = paths.resume_dir / "master.tex"
    write_private(target, document.text)
    return ResumeRef(ResumeFormat.LATEX, target), LatexResume(document.text, pdflatex)


def _compose(draft: ProfileDraft, resume: ResumeRef) -> Profile:
    basics = steps.confirm_basics(draft)
    targets = steps.ask_targets(draft, basics)
    sites = steps.ask_sites()
    autonomy = steps.ask_autonomy(basics.current_company)
    facts = steps.ask_facts(basics.country)
    diversity = steps.ask_diversity()
    extra = steps.ask_extra()
    return Profile(
        name=basics.name,
        email=basics.email,
        phone=basics.phone,
        city=basics.city,
        country=basics.country,
        links=basics.links,
        current_company=basics.current_company,
        years_experience=basics.years_experience,
        resume=resume,
        roles=targets.roles,
        title_keywords=targets.title_keywords,
        title_exclude=targets.title_exclude,
        work_places=targets.work_places,
        sites=sites,
        submit_mode=autonomy.submit_mode,
        unknown_questions=autonomy.unknown_questions,
        daily_cap=autonomy.daily_cap,
        cover_letter=autonomy.cover_letter,
        skip_companies=autonomy.skip_companies,
        notice_period=facts.notice_period,
        citizenship=facts.citizenship,
        work_without_visa=facts.work_without_visa,
        needs_sponsorship_elsewhere=facts.needs_sponsorship_elsewhere,
        salary=facts.salary,
        dob=facts.dob,
        diversity=diversity,
        extra_facts=extra,
    )


def _confirm_replace(paths: Paths) -> None:
    if paths.profile.exists() and not ask.yes_no("A profile already exists. Replace it?", False):
        raise SetupCancelledError("Kept your existing profile.")


def _finish(paths: Paths, profile: Profile, resume: Resume) -> None:
    ask.heading("Done")
    ask.say(f"Profile saved to {paths.profile}")
    try:
        ask.say("Building your master resume (missing LaTeX packages install automatically) …")
        rendered = master_pdf(paths, resume)
    except SatyaApplyError as error:
        ask.say(f"Your resume didn't build yet: {error}")
        ask.say(error.hint)
        return
    ask.say(f"Master resume: {rendered.pdf} ({rendered.pages} page{'s' * (rendered.pages != 1)})")
    if profile.resume.format is ResumeFormat.STRUCTURED:
        ask.say("Open it once and check every line. Edit master.json to fix anything.")
    print("\nNext:")
    for line in NEXT_STEPS:
        print(f"  {line}")


def run(paths: Paths, resume_path: Path | None) -> Profile:
    paths.ensure()
    _confirm_replace(paths)
    ask.heading("SatyaApply setup")
    ask.say("Checking Claude Code …")
    tasks.ping()
    path = resume_path or Path(
        ask.text("Where is your resume? (.tex, .pdf, .docx, .md or .txt)", required=True)
    )
    document = read_document(path.expanduser())
    ask.say("Reading your resume with Claude …")
    draft = tasks.draft_profile(document)
    resume_ref, resume = store_resume(paths, document)
    profile = _compose(draft, resume_ref)
    save(paths, profile)
    _finish(paths, profile, resume)
    return profile
