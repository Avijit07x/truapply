from pathlib import Path

from satyaapply.ai import tasks
from satyaapply.core.documents import ResumeDocument, ResumeFormat
from satyaapply.core.files import write_private
from satyaapply.core.paths import Paths
from satyaapply.core.profile import ResumeRef
from satyaapply.resume.contract import Resume
from satyaapply.resume.latex import LatexResume, split_document
from satyaapply.resume.structured import StructuredResume

LATEX = ".tex"


def is_latex(document: ResumeDocument) -> bool:
    return document.path.suffix.lower() == LATEX and document.text is not None


def as_latex(document: ResumeDocument, pdflatex: Path) -> LatexResume:
    text = document.text or ""
    split_document(text)
    return LatexResume(text, pdflatex)


def converted(document: ResumeDocument) -> StructuredResume:
    return StructuredResume(tasks.convert_resume(document))


def keep(paths: Paths, resume: Resume) -> ResumeRef:
    latex = isinstance(resume, LatexResume)
    target = paths.resume_dir / f"master{resume.suffix}"
    write_private(target, resume.source)
    return ResumeRef(ResumeFormat.LATEX if latex else ResumeFormat.STRUCTURED, target)
