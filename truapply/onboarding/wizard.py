from pathlib import Path

from truapply.ai import tasks
from truapply.ai.replies import ProfileDraft
from truapply.core.documents import ResumeDocument, ResumeFormat
from truapply.core.errors import SetupCancelledError, TruApplyError
from truapply.core.paths import Paths
from truapply.core.profile import Profile, ResumeRef, save
from truapply.onboarding import ask, steps
from truapply.onboarding.ask import Option
from truapply.onboarding.latex import install_tinytex
from truapply.resume import storing
from truapply.resume.contract import Resume
from truapply.resume.importer import read_document
from truapply.resume.latex import split_document
from truapply.resume.master import master_pdf
from truapply.resume.render import find_pdflatex

NEXT_STEPS = (
    "truapply doctor                       check that everything works",
    "truapply tailor JOB.txt --company … --title …   preview a tailored resume",
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


def _structured(document: ResumeDocument) -> Resume:
    ask.say("Moving your resume into the built-in design with Claude …")
    return storing.converted(document)


def store_resume(paths: Paths, document: ResumeDocument) -> tuple[ResumeRef, Resume]:
    if not storing.is_latex(document):
        resume = _structured(document)
    else:
        split_document(document.text or "")
        pdflatex = _pdflatex()
        resume = _structured(document) if pdflatex is None else storing.as_latex(document, pdflatex)
    return storing.keep(paths, resume), resume


def _compose(draft: ProfileDraft, resume: ResumeRef) -> Profile:
    basics = steps.confirm_basics(draft)
    targets = steps.ask_targets(draft, basics)
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
    except TruApplyError as error:
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
    ask.heading("TruApply setup")
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
