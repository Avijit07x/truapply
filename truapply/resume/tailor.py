import re
import shutil
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from truapply.ai.tasks import review_claims
from truapply.core.errors import AIError, LatexFailedError, UsageLimitError
from truapply.core.files import write_private
from truapply.core.models import Job
from truapply.core.numbers import new_numbers
from truapply.resume.contract import Draft, Rendered, Resume

ClaimReviewer = Callable[[str, str], tuple[str, ...]]
UNSAFE_FILE_CHARS = re.compile(r"[\W_]+")


@dataclass(frozen=True)
class TailorRequest:
    job: Job
    notes: tuple[str, ...]
    out_dir: Path
    file_name: str
    original: Rendered


@dataclass(frozen=True)
class Tailored:
    pdf: Path
    source: str
    used_original: bool
    problems: tuple[str, ...]
    changes: tuple[str, ...]


def file_name_for(person: str) -> str:
    stem = UNSAFE_FILE_CHARS.sub("_", person).strip("_") or "Resume"
    return f"{stem}_Resume.pdf"


def draft_problems(resume: Resume, draft: Draft, review: ClaimReviewer) -> list[str]:
    problems = resume.problems(draft)
    if problems:
        return problems
    original, tailored = resume.readable(resume.source), resume.readable(draft.source)
    added = new_numbers(original, tailored)
    if added:
        return ["new numbers: " + ", ".join(added)]
    try:
        claims = review(original, tailored)
    except UsageLimitError:
        raise
    except AIError as error:
        return [f"couldn't check for new claims: {error}"]
    return [f"new claim: {claim}" for claim in claims]


def keep_original(resume: Resume, target: Path, original: Rendered) -> Path:
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(original.pdf, target)
    (target.parent / f"tailored{resume.suffix}").unlink(missing_ok=True)
    return target


def _fallback(
    resume: Resume, request: TailorRequest, problems: list[str], changes: tuple[str, ...]
) -> Tailored:
    target = keep_original(resume, request.out_dir / request.file_name, request.original)
    return Tailored(target, resume.source, True, tuple(problems), changes)


def _render(resume: Resume, request: TailorRequest, draft: Draft) -> Tailored:
    target = request.out_dir / request.file_name
    try:
        rendered = resume.render(draft.source, target)
    except LatexFailedError as error:
        return _fallback(resume, request, [f"tailored resume didn't build: {error}"], draft.changes)
    if rendered.pages > request.original.pages:
        problem = (
            f"tailored resume has {rendered.pages} pages; the original has {request.original.pages}"
        )
        return _fallback(resume, request, [problem], draft.changes)
    write_private(request.out_dir / f"tailored{resume.suffix}", draft.source)
    return Tailored(rendered.pdf, draft.source, False, (), draft.changes)


def _checked_draft(
    resume: Resume, request: TailorRequest, review: ClaimReviewer
) -> tuple[Draft, list[str]]:
    draft = resume.draft(request.job, request.notes)
    problems = draft_problems(resume, draft, review)
    if not problems:
        return draft, []
    revised = resume.revise(draft, problems)
    return revised, draft_problems(resume, revised, review)


def tailor(
    resume: Resume, request: TailorRequest, review: ClaimReviewer = review_claims
) -> Tailored:
    try:
        draft, problems = _checked_draft(resume, request, review)
    except UsageLimitError:
        raise
    except AIError as error:
        return _fallback(resume, request, [f"tailoring failed: {error}"], ())
    if problems:
        return _fallback(resume, request, problems, draft.changes)
    return _render(resume, request, draft)
