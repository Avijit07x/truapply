import hashlib
import json

from truapply.core.codec import decode
from truapply.core.documents import ResumeData, ResumeFormat
from truapply.core.errors import LatexMissingError
from truapply.core.files import write_private
from truapply.core.paths import Paths
from truapply.core.profile import Profile
from truapply.resume.contract import Rendered, Resume
from truapply.resume.latex import LatexResume
from truapply.resume.render import find_pdflatex
from truapply.resume.structured import StructuredResume


def load_resume(profile: Profile) -> Resume:
    source = profile.resume.path.read_text(encoding="utf-8")
    if profile.resume.format is ResumeFormat.STRUCTURED:
        return StructuredResume(decode(ResumeData, json.loads(source)))
    pdflatex = find_pdflatex()
    if pdflatex is None:
        raise LatexMissingError("Your resume is LaTeX, but pdflatex isn't installed.")
    return LatexResume(source, pdflatex)


def _digest(resume: Resume) -> str:
    return hashlib.sha256(resume.source.encode("utf-8")).hexdigest()


def remember(paths: Paths, resume: Resume, rendered: Rendered) -> None:
    meta = {"sha256": _digest(resume), "pages": rendered.pages}
    write_private(paths.master_pdf_meta, json.dumps(meta))


def cached_master(paths: Paths, resume: Resume) -> Rendered | None:
    if not (paths.master_pdf.is_file() and paths.master_pdf_meta.is_file()):
        return None
    meta = json.loads(paths.master_pdf_meta.read_text(encoding="utf-8"))
    if meta.get("sha256") != _digest(resume):
        return None
    return Rendered(paths.master_pdf, int(meta["pages"]))


def master_pdf(paths: Paths, resume: Resume) -> Rendered:
    cached = cached_master(paths, resume)
    if cached:
        return cached
    rendered = resume.render(resume.source, paths.master_pdf)
    remember(paths, resume, rendered)
    return rendered
