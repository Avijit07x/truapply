from collections.abc import Sequence

SEPARATOR = " · "
ESCAPED = {"\\": " ", " ": " ", ",": " ", "&": "&", "%": "%", "$": "$", "#": "#", "_": "_"}
PLAIN = {"~": " ", "}": "", "$": ""}
REPLACED = {"item": "• ", "sep": SEPARATOR}
LAST_ARGUMENT = frozenset({"href", "textcolor"})
HIDDEN = frozenset(
    {
        "begin",
        "end",
        "vspace",
        "hspace",
        "color",
        "fontsize",
        "setlength",
        "usepackage",
        "documentclass",
        "newcommand",
        "renewcommand",
        "definecolor",
    }
)


def readable_changes(lines: Sequence[str]) -> list[str]:
    return [shown for shown in map(_readable, lines) if shown]


def _readable(line: str) -> str:
    sign, body = (line[:1], line[1:]) if line[:1] in ("+", "-") else ("", line)
    if not body.strip() or body.lstrip().startswith("%"):
        return ""
    if "\\" not in body:
        return line
    try:
        text = " ".join(_render(body).split()).strip(" ·")
    except RecursionError:
        return line
    text = text.replace("---", "—").replace("--", "\u2013")
    return f"{sign}{text}" if text else ""


def _render(text: str) -> str:
    pieces: list[str] = []
    index = 0
    while index < len(text):
        piece, index = _token(text, index)
        pieces.append(piece)
    return "".join(pieces)


def _token(text: str, index: int) -> tuple[str, int]:
    char = text[index]
    if char == "\\":
        return _command(text, index + 1)
    if char == "{":
        inner, end = _group(text, index)
        return _render(inner), end
    if char == "%":
        return "", len(text)
    return PLAIN.get(char, char), index + 1


def _group(text: str, start: int) -> tuple[str, int]:
    depth = 0
    index = start
    while index < len(text):
        char = text[index]
        if char == "\\":
            index += 2
            continue
        depth += {"{": 1, "}": -1}.get(char, 0)
        if depth == 0:
            return text[start + 1 : index], index + 1
        index += 1
    return text[start + 1 :], len(text)


def _command(text: str, start: int) -> tuple[str, int]:
    if start >= len(text):
        return "", start
    if not text[start].isalpha():
        end = _skip_optional(text, start + 1) if text[start] == "\\" else start + 1
        return ESCAPED.get(text[start], ""), end
    end = start
    while end < len(text) and text[end].isalpha():
        end += 1
    name = text[start:end]
    if text.startswith("*", end):
        end += 1
    arguments, end = _arguments(text, _skip_optional(text, end))
    return _expand(name, arguments), end


def _skip_optional(text: str, index: int) -> int:
    if not text.startswith("[", index):
        return index
    close = text.find("]", index)
    return index if close < 0 else close + 1


def _arguments(text: str, index: int) -> tuple[list[str], int]:
    arguments: list[str] = []
    while text.startswith("{", next_index := _skip_optional(text, index)):
        argument, index = _group(text, next_index)
        arguments.append(argument)
    return arguments, index


def _expand(name: str, arguments: list[str]) -> str:
    if name in HIDDEN:
        return " "
    if name in LAST_ARGUMENT and arguments:
        return _render(arguments[-1])
    shown = [part for part in map(_render, arguments) if part.strip()]
    if not arguments:
        return REPLACED.get(name, " ")
    return REPLACED.get(name, "") + SEPARATOR.join(shown)
