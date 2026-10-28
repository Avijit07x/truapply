import html
import re
from collections.abc import Mapping
from datetime import UTC, datetime

LIST_ITEM = re.compile(r"<li[^>]*>", re.IGNORECASE)
BLOCK_END = re.compile(r"</(?:p|div|li|h[1-6]|ul|ol|tr|section)>|<br\s*/?>", re.IGNORECASE)
TAG = re.compile(r"<[^>]+>")
SPACES = re.compile(r"[^\S\n]+")
BLANK_LINES = re.compile(r"\n{3,}")
MILLISECONDS = 1000


def html_to_text(markup: str) -> str:
    decoded = html.unescape(markup)
    marked = BLOCK_END.sub("\n", LIST_ITEM.sub("\n- ", decoded))
    text = html.unescape(TAG.sub("", marked))
    lines = (SPACES.sub(" ", line).strip() for line in text.splitlines())
    return BLANK_LINES.sub("\n\n", "\n".join(lines)).strip()


def mapping(value: object) -> Mapping[str, object]:
    return value if isinstance(value, Mapping) else {}


def items(value: object) -> list[object]:
    return value if isinstance(value, list) else []


def text(source: Mapping[str, object], key: str) -> str:
    value = source.get(key)
    return value.strip() if isinstance(value, str) else ""


def identifier(source: Mapping[str, object], key: str) -> str:
    value = source.get(key)
    return str(value) if isinstance(value, str | int) and not isinstance(value, bool) else ""


def iso_time(value: str) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


def epoch_ms(value: object) -> datetime | None:
    if not isinstance(value, int) or isinstance(value, bool):
        return None
    return datetime.fromtimestamp(value / MILLISECONDS, UTC)
