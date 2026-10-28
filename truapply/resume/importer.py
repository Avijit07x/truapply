import html
import re
import zipfile
from pathlib import Path

from truapply.core.documents import ResumeDocument
from truapply.core.errors import ResumeUnreadableError

SUPPORTED_SUFFIXES = frozenset({".tex", ".pdf", ".docx", ".md", ".txt"})
DOCX_BODY = "word/document.xml"
PARAGRAPH_END = re.compile(r"</w:p>")
INLINE_BREAK = re.compile(r"<w:(?:br|tab)\b[^>]*/>")
TAG = re.compile(r"<[^>]+>")


def docx_text(path: Path) -> str:
    try:
        with zipfile.ZipFile(path) as archive:
            xml = archive.read(DOCX_BODY).decode("utf-8")
    except (zipfile.BadZipFile, KeyError, UnicodeDecodeError) as error:
        raise ResumeUnreadableError(f"{path.name} isn't a readable Word file.") from error
    paragraphs = (
        html.unescape(TAG.sub("", INLINE_BREAK.sub(" ", part))) for part in PARAGRAPH_END.split(xml)
    )
    return "\n".join(line.strip() for line in paragraphs if line.strip())


def read_document(path: Path) -> ResumeDocument:
    if not path.is_file():
        raise ResumeUnreadableError(f"{path} doesn't exist.")
    suffix = path.suffix.lower()
    if suffix not in SUPPORTED_SUFFIXES:
        raise ResumeUnreadableError(f"{path.name} isn't a supported resume file.")
    if suffix == ".pdf":
        return ResumeDocument(path, None)
    if suffix == ".docx":
        return ResumeDocument(path, docx_text(path))
    try:
        return ResumeDocument(path, path.read_text(encoding="utf-8"))
    except UnicodeDecodeError as error:
        raise ResumeUnreadableError(f"{path.name} isn't UTF-8 text.") from error
