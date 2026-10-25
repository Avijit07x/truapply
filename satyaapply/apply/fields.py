import re
from functools import cache
from importlib import resources

from playwright.sync_api import Locator, Page

from satyaapply.core.codec import decode
from satyaapply.core.errors import DecodeError
from satyaapply.core.forms import Field

FIELD_ATTR = "data-satya-field"
OPTION_ATTR = "data-satya-option"
SCOPE_ATTR = "data-satya-scope"
FIELD_ID = re.compile(r"^f\d+$")


@cache
def _script() -> str:
    return resources.files("satyaapply.apply").joinpath("fields.js").read_text("utf-8")


def _field(raw: object) -> Field | None:
    try:
        field = decode(Field, raw)
    except DecodeError:
        return None
    return field if FIELD_ID.match(field.id) else None


def read_fields(page: Page) -> list[Field]:
    raw = page.evaluate(_script())
    candidates = (_field(item) for item in raw) if isinstance(raw, list) else ()
    return [field for field in candidates if field]


def form_scope(page: Page) -> Locator:
    scope = page.locator(f"[{SCOPE_ATTR}]")
    return scope.first if scope.count() else page.locator("body")


def control(page: Page, field: Field) -> Locator:
    return page.locator(f'[{FIELD_ATTR}="{field.id}"]')


def option(page: Page, field: Field, index: int) -> Locator:
    return page.locator(f'[{FIELD_ATTR}="{field.id}"][{OPTION_ATTR}="{index}"]')
