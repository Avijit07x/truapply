import zipfile
from pathlib import Path

import pytest

from satyaapply.core.errors import ResumeUnreadableError
from satyaapply.resume.importer import read_document

DOCUMENT_XML = (
    "<w:document><w:body>"
    "<w:p><w:r><w:t>Asha Rao</w:t></w:r></w:p>"
    "<w:p><w:r><w:t>React</w:t></w:r><w:tab/><w:r><w:t>&amp; TypeScript</w:t></w:r></w:p>"
    "</w:body></w:document>"
)


def test_word_resume_text_is_extracted(tmp_path: Path) -> None:
    path = tmp_path / "resume.docx"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("word/document.xml", DOCUMENT_XML)
    assert read_document(path).text == "Asha Rao\nReact & TypeScript"


def test_pdf_is_left_for_claude_to_read(tmp_path: Path) -> None:
    path = tmp_path / "resume.pdf"
    path.write_bytes(b"%PDF-1.7")
    assert read_document(path).needs_reading


def test_plain_text_is_read_as_is(tmp_path: Path) -> None:
    path = tmp_path / "resume.md"
    path.write_text("# Asha Rao")
    assert read_document(path).text == "# Asha Rao"


@pytest.mark.parametrize("name", ["resume.pages", "missing.pdf"])
def test_unsupported_or_missing_files_are_refused(tmp_path: Path, name: str) -> None:
    if name.endswith(".pages"):
        (tmp_path / name).write_text("x")
    with pytest.raises(ResumeUnreadableError):
        read_document(tmp_path / name)


def test_a_broken_word_file_is_refused(tmp_path: Path) -> None:
    path = tmp_path / "resume.docx"
    path.write_text("not a zip")
    with pytest.raises(ResumeUnreadableError, match="Word"):
        read_document(path)
