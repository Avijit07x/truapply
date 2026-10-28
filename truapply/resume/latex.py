from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from truapply.ai.tasks import revise_latex, rewrite_latex
from truapply.core.errors import ResumeUnreadableError
from truapply.core.models import Job
from truapply.resume.contract import Draft, Rendered
from truapply.resume.packages import render_installing
from truapply.resume.render import latex_commands

DOCUMENT_START = "\\begin{document}"
DOCUMENT_END = "\\end{document}"
CHARACTER_ESCAPE = "^^"


def split_document(source: str) -> tuple[str, str]:
    start = source.find(DOCUMENT_START)
    if start < 0:
        raise ResumeUnreadableError("The LaTeX resume has no \\begin{document}.")
    return source[:start], source[start:]


def body_problems(original_body: str, tailored_body: str) -> list[str]:
    stripped = tailored_body.strip()
    if not stripped.startswith(DOCUMENT_START) or not stripped.endswith(DOCUMENT_END):
        return ["the tailored body must run from \\begin{document} to \\end{document}"]
    problems = []
    added = sorted(latex_commands(tailored_body) - latex_commands(original_body))
    if added:
        problems.append("new LaTeX commands: " + ", ".join(f"\\{name}" for name in added))
    if CHARACTER_ESCAPE in tailored_body and CHARACTER_ESCAPE not in original_body:
        problems.append("TeX character escapes (^^) are not allowed")
    return problems


@dataclass(frozen=True)
class LatexResume:
    source: str
    pdflatex: Path
    suffix: str = ".tex"

    @property
    def preamble(self) -> str:
        return split_document(self.source)[0]

    @property
    def body(self) -> str:
        return split_document(self.source)[1]

    def readable(self, source: str) -> str:
        return split_document(source)[1]

    def draft(self, job: Job, notes: Sequence[str]) -> Draft:
        rewrite = rewrite_latex(self.preamble, self.body, job, notes)
        return Draft(self.preamble + rewrite.body.strip() + "\n", rewrite.changes)

    def revise(self, draft: Draft, problems: Sequence[str]) -> Draft:
        tailored_body = draft.source[len(self.preamble) :]
        rewrite = revise_latex(self.preamble, self.body, tailored_body, problems)
        return Draft(self.preamble + rewrite.body.strip() + "\n", rewrite.changes)

    def problems(self, draft: Draft) -> list[str]:
        if not draft.source.startswith(self.preamble):
            return ["the LaTeX preamble changed"]
        return body_problems(self.body, draft.source[len(self.preamble) :])

    def render(self, source: str, target: Path) -> Rendered:
        return render_installing(source, target, self.pdflatex)
