import dataclasses
import types
from collections.abc import Callable, Mapping
from datetime import date
from enum import Enum
from pathlib import Path
from typing import Any, TypeVar, Union, get_args, get_origin, get_type_hints

from satyaapply.core.errors import DecodeError

T = TypeVar("T")


def _as_str(value: object) -> str:
    if isinstance(value, str):
        return value
    raise TypeError("must be text")


def _as_int(value: object) -> int:
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    raise TypeError("must be a whole number")


def _as_float(value: object) -> float:
    if isinstance(value, int | float) and not isinstance(value, bool):
        return float(value)
    raise TypeError("must be a number")


def _as_bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    raise TypeError("must be true or false")


def _as_path(value: object) -> Path:
    return Path(_as_str(value)).expanduser()


def _as_date(value: object) -> date:
    try:
        return date.fromisoformat(_as_str(value))
    except ValueError:
        raise TypeError("must be a date like 2001-05-07") from None


SCALARS: dict[object, Callable[[object], object]] = {
    str: _as_str,
    int: _as_int,
    float: _as_float,
    bool: _as_bool,
    Path: _as_path,
    date: _as_date,
}

SCALAR_SCHEMAS: dict[object, dict[str, object]] = {
    str: {"type": "string"},
    int: {"type": "integer"},
    float: {"type": "number"},
    bool: {"type": "boolean"},
    Path: {"type": "string"},
    date: {"type": "string"},
}


def _join(path: str, name: str) -> str:
    return f"{path}.{name}" if path else name


def _optional_inner(tp: Any) -> Any | None:
    if get_origin(tp) not in (Union, types.UnionType):
        return None
    inner = [option for option in get_args(tp) if option is not type(None)]
    if len(inner) != 1 or len(get_args(tp)) != len(inner) + 1:
        raise TypeError(f"only `X | None` unions are supported, not {tp}")
    return inner[0]


def _decode_dataclass(cls: Any, value: object, path: str) -> Any:
    if not isinstance(value, Mapping):
        raise DecodeError(path, "must be an object")
    hints = get_type_hints(cls)
    fields = {field.name: field for field in dataclasses.fields(cls) if field.init}
    unknown = sorted(set(value) - set(fields))
    if unknown:
        raise DecodeError(_join(path, str(unknown[0])), "is not a known field")
    arguments: dict[str, object] = {}
    for name, field in fields.items():
        if name in value:
            arguments[name] = _decode(hints[name], value[name], _join(path, name))
        elif field.default is dataclasses.MISSING and field.default_factory is dataclasses.MISSING:
            raise DecodeError(_join(path, name), "is required")
    return cls(**arguments)


def _decode(tp: Any, value: object, path: str) -> Any:
    inner = _optional_inner(tp)
    if inner is not None:
        return None if value is None else _decode(inner, value, path)
    if get_origin(tp) is tuple:
        if not isinstance(value, list):
            raise DecodeError(path, "must be a list")
        item_type = get_args(tp)[0]
        return tuple(_decode(item_type, item, f"{path}[{i}]") for i, item in enumerate(value))
    if dataclasses.is_dataclass(tp):
        return _decode_dataclass(tp, value, path)
    if isinstance(tp, type) and issubclass(tp, Enum):
        try:
            return tp(value)
        except ValueError:
            choices = ", ".join(str(member.value) for member in tp)
            raise DecodeError(path, f"must be one of: {choices}") from None
    if tp in SCALARS:
        try:
            return SCALARS[tp](value)
        except TypeError as error:
            raise DecodeError(path, str(error)) from None
    raise TypeError(f"cannot decode {tp}")


def decode(cls: type[T], data: object) -> T:
    result: T = _decode(cls, data, "")
    return result


def encode(value: object) -> object:
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        return {
            field.name: encode(getattr(value, field.name)) for field in dataclasses.fields(value)
        }
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, tuple | list):
        return [encode(item) for item in value]
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, date):
        return value.isoformat()
    return value


def json_schema(tp: Any) -> dict[str, object]:
    inner = _optional_inner(tp)
    if inner is not None:
        return {"anyOf": [json_schema(inner), {"type": "null"}]}
    if get_origin(tp) is tuple:
        return {"type": "array", "items": json_schema(get_args(tp)[0])}
    if dataclasses.is_dataclass(tp):
        hints = get_type_hints(tp)
        fields = [field for field in dataclasses.fields(tp) if field.init]
        return {
            "type": "object",
            "properties": {field.name: json_schema(hints[field.name]) for field in fields},
            "required": [field.name for field in fields],
            "additionalProperties": False,
        }
    if isinstance(tp, type) and issubclass(tp, Enum):
        return {"type": "string", "enum": [str(member.value) for member in tp]}
    if tp in SCALAR_SCHEMAS:
        return dict(SCALAR_SCHEMAS[tp])
    raise TypeError(f"no JSON schema for {tp}")
