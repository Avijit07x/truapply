from pathlib import Path

import pytest

from satyaapply.browser.pdf import count_pages
from satyaapply.core.errors import ResumeUnreadableError
from satyaapply.core.numbers import new_numbers
from satyaapply.resume.contract import Draft
from satyaapply.resume.latex import LatexResume, body_problems, split_document
from satyaapply.resume.render import missing_file, page_count

PREAMBLE = "\\documentclass{article}\n\\newcommand{\\B}[1]{\\textbf{#1}}\n"
BODY = "\\begin{document}\n\\B{React} for 2+ years, 1,600+ stars.\n\\end{document}\n"
SOURCE = PREAMBLE + BODY


def test_numbers_that_already_exist_are_fine() -> None:
    assert new_numbers("1,600+ stars, 2+ years", "2+ years and 1600+ stars") == []


def test_a_changed_metric_is_caught() -> None:
    assert new_numbers("cut load time by 30%", "cut load time by 45%") == ["45"]


def test_split_keeps_preamble_and_body_apart() -> None:
    assert split_document(SOURCE) == (PREAMBLE, BODY)


def test_latex_without_a_document_is_unreadable() -> None:
    with pytest.raises(ResumeUnreadableError):
        split_document("\\documentclass{article}")


def test_reordered_body_with_known_commands_passes() -> None:
    tailored = "\\begin{document}\n1,600+ stars and \\B{React}.\n\\end{document}\n"
    assert body_problems(BODY, tailored) == []


def test_a_new_command_is_refused() -> None:
    tailored = "\\begin{document}\n\\input{/etc/passwd}\\B{React}\n\\end{document}"
    assert body_problems(BODY, tailored) == ["new LaTeX commands: \\input"]


def test_character_escapes_are_refused() -> None:
    tailored = "\\begin{document}\n^^5cinput{secret}\n\\end{document}"
    assert body_problems(BODY, tailored) == ["TeX character escapes (^^) are not allowed"]


def test_a_body_that_isnt_a_document_is_refused() -> None:
    assert body_problems(BODY, "\\B{React}") != []


def test_a_changed_preamble_is_refused() -> None:
    resume = LatexResume(SOURCE, Path("/bin/pdflatex"))
    draft = Draft("\\documentclass{book}\n" + BODY, ())
    assert resume.problems(draft) == ["the LaTeX preamble changed"]


def test_missing_package_and_font_are_found_in_the_log() -> None:
    assert missing_file("! LaTeX Error: File `microtype.sty' not found.") == "microtype.sty"
    font_log = "! Font T1/bch/m/n/10=bchr8t at 10.0pt not loadable: Metric (TFM) file not found."
    assert missing_file(font_log) == "bchr8t.tfm"


def test_page_count_is_read_from_the_log() -> None:
    assert page_count("Output written on resume.pdf (1 page, 54321 bytes).") == 1
    assert page_count("Output written on\nresume.pdf (2 pages, 9 bytes).") == 2


def test_pdf_pages_are_counted_but_not_the_page_tree() -> None:
    pdf = b"<< /Type /Pages /Count 2 >> << /Type /Page >> << /Type/Page >>"
    assert count_pages(pdf) == 2
