import base64
import binascii
import re
import sqlite3
from dataclasses import replace
from pathlib import Path

from truapply.core.errors import TruApplyError
from truapply.core.files import write_private
from truapply.core.paths import Paths
from truapply.core.profile import load, save
from truapply.resume import storing
from truapply.resume.contract import Resume
from truapply.resume.importer import SUPPORTED_SUFFIXES, read_document
from truapply.resume.master import remember
from truapply.resume.render import find_pdflatex
from truapply.tracker.body import Body, text
from truapply.tracker.responses import Response, bad_request, ok
from truapply.tracker.routes import Route, route

PATH = "/settings/resume"
MAX_RESUME_BYTES = 5_000_000
MAX_UPLOAD_BYTES = MAX_RESUME_BYTES * 4 // 3 + 1_000
MAX_NAME = 200
KINDS = ", ".join(sorted(SUPPORTED_SUFFIXES))
WRONG_KIND = f"Pick a resume file ({KINDS})."
TOO_BIG = f"The file is over {MAX_RESUME_BYTES // 1_000_000} MB."
NOT_READ = "The file didn't come through. Pick it again."


def _bytes(body: Body) -> bytes | None:
    data = body.get("data")
    if not isinstance(data, str):
        return None
    try:
        return base64.b64decode(data, validate=True)
    except (binascii.Error, ValueError):
        return None


def _resume(upload: Path) -> Resume:
    document = read_document(upload)
    pdflatex = find_pdflatex()
    if storing.is_latex(document) and pdflatex is not None:
        return storing.as_latex(document, pdflatex)
    return storing.converted(document)


def replaced(paths: Paths, suffix: str, data: bytes) -> dict[str, object]:
    profile = load(paths)
    upload = paths.resume_dir / f"upload{suffix}"
    write_private(upload, data)
    try:
        resume = _resume(upload)
    finally:
        upload.unlink(missing_ok=True)
    rendered = resume.render(resume.source, paths.master_pdf)
    remember(paths, resume, rendered)
    ref = storing.keep(paths, resume)
    save(paths, replace(profile, resume=ref))
    return {"format": ref.format.value, "pages": rendered.pages}


def _replace(_db: sqlite3.Connection, paths: Paths, _match: re.Match[str], body: Body) -> Response:
    suffix = Path(text(body, "name", MAX_NAME)).suffix.lower()
    if suffix not in SUPPORTED_SUFFIXES:
        return bad_request(WRONG_KIND)
    data = _bytes(body)
    if not data:
        return bad_request(NOT_READ)
    if len(data) > MAX_RESUME_BYTES:
        return bad_request(TOO_BIG)
    try:
        return ok(replaced(paths, suffix, data))
    except TruApplyError as error:
        return bad_request(f"Your resume wasn't changed. {error}")


GET: tuple[Route, ...] = ()
POST: tuple[Route, ...] = (route(PATH, _replace),)
