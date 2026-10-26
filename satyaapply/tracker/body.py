from collections.abc import Mapping

Body = Mapping[str, object]


def text(body: Body, key: str, limit: int) -> str:
    value = body.get(key)
    return value.strip()[:limit] if isinstance(value, str) else ""


def flag(body: Body, key: str) -> bool | None:
    value = body.get(key)
    return value if isinstance(value, bool) else None


def number(body: Body, key: str) -> int | None:
    value = body.get(key)
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def strings(body: Body, key: str) -> list[str] | None:
    value = body.get(key)
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        return None
    return [str(item) for item in value]


def pairs(body: Body, key: str, limit: int) -> dict[str, str]:
    value = body.get(key)
    items = value if isinstance(value, list) else []
    return {
        item["question"]: item["answer"].strip()[:limit]
        for item in items
        if isinstance(item, dict)
        and isinstance(item.get("question"), str)
        and isinstance(item.get("answer"), str)
    }
