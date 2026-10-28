import difflib

HEADER_PREFIXES = ("---", "+++", "@@")


def changed_lines(original: str, tailored: str) -> list[str]:
    diff = difflib.unified_diff(original.splitlines(), tailored.splitlines(), n=0, lineterm="")
    return [line for line in diff if not line.startswith(HEADER_PREFIXES)]
