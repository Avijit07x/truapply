from pathlib import Path

from tools.check_no_comments import violations

QUOTE = '"' * 3


def write(tmp_path: Path, source: str) -> Path:
    path = tmp_path / "module.py"
    path.write_text(source)
    return path


def test_a_planted_comment_is_caught(tmp_path: Path) -> None:
    path = write(tmp_path, "x = 1\n# explain x\n")
    assert violations(path) == [f"{path}:2: comment"]


def test_trailing_comments_are_caught_too(tmp_path: Path) -> None:
    path = write(tmp_path, "x = 1  # why\n")
    assert violations(path) == [f"{path}:1: comment"]


def test_tool_directives_are_allowed(tmp_path: Path) -> None:
    path = write(tmp_path, "import os  # noqa: F401\ny: int = 'a'  # type: ignore[assignment]\n")
    assert violations(path) == []


def test_docstrings_are_caught(tmp_path: Path) -> None:
    path = write(tmp_path, f"def f() -> None:\n    {QUOTE}Explain.{QUOTE}\n")
    assert violations(path) == [f"{path}:2: docstring"]


def test_hash_inside_a_string_is_not_a_comment(tmp_path: Path) -> None:
    path = write(tmp_path, "color = '#ff0000'\n")
    assert violations(path) == []
