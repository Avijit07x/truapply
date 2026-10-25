import ast
import io
import re
import sys
import tokenize
from collections.abc import Iterator, Sequence
from pathlib import Path

ALLOWED_DIRECTIVE = re.compile(r"#\s*(?:noqa\b|type:\s*ignore\b)")
DEFAULT_ROOTS = ("satyaapply", "tools", "tests")
DOCSTRING_HOLDERS = (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)


def comment_lines(source: str) -> list[int]:
    tokens = tokenize.generate_tokens(io.StringIO(source).readline)
    return [
        token.start[0]
        for token in tokens
        if token.type == tokenize.COMMENT and not ALLOWED_DIRECTIVE.match(token.string)
    ]


def docstring_lines(source: str) -> list[int]:
    return [
        node.body[0].lineno
        for node in ast.walk(ast.parse(source))
        if isinstance(node, DOCSTRING_HOLDERS) and ast.get_docstring(node, clean=False) is not None
    ]


def violations(path: Path) -> list[str]:
    source = path.read_text(encoding="utf-8")
    found = [f"{path}:{line}: comment" for line in comment_lines(source)]
    found.extend(f"{path}:{line}: docstring" for line in docstring_lines(source))
    return found


def python_files(arguments: Sequence[str]) -> Iterator[Path]:
    if arguments:
        yield from (Path(argument) for argument in arguments if argument.endswith(".py"))
        return
    for root in DEFAULT_ROOTS:
        yield from sorted(Path(root).rglob("*.py"))


def main(arguments: Sequence[str]) -> int:
    found = [violation for path in python_files(arguments) for violation in violations(path)]
    for violation in found:
        print(violation)
    return 1 if found else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
