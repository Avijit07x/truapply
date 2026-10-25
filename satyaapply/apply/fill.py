import logging
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import Locator, Page
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from satyaapply.apply.fields import control, option
from satyaapply.apply.options import as_number, best_option, is_truthy
from satyaapply.core.forms import (
    COVER_LETTER_FILE,
    MULTI_VALUE_SEPARATOR,
    RESUME_FILE,
    Field,
    FieldKind,
)

ACTION_TIMEOUT_MS = 8_000
COMBOBOX_SETTLE_MS = 700
SUGGESTIONS_TIMEOUT_MS = 5_000
NOT_UPLOADED = "(dry run: file not uploaded)"
VISIBLE_OPTIONS = "[role='option']:visible"

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class Files:
    resume: Path | None
    cover_letter: Path | None


Filler = Callable[[Page, Field, str, Files], str | None]


def _check(target: Locator, checked: bool = True) -> None:
    try:
        target.set_checked(checked, force=True, timeout=ACTION_TIMEOUT_MS)
    except PlaywrightError:
        target.dispatch_event("click")


def _text(page: Page, field: Field, value: str, _files: Files) -> str | None:
    limited = value[: field.max_length] if field.max_length else value
    control(page, field).first.fill(limited, timeout=ACTION_TIMEOUT_MS)
    return limited


def _number(page: Page, field: Field, value: str, files: Files) -> str | None:
    number = as_number(value)
    return _text(page, field, number, files) if number is not None else None


def _select(page: Page, field: Field, value: str, _files: Files) -> str | None:
    index = best_option(field.options, value)
    if index is None:
        return None
    control(page, field).first.select_option(label=field.options[index], timeout=ACTION_TIMEOUT_MS)
    return field.options[index]


def _radio(page: Page, field: Field, value: str, _files: Files) -> str | None:
    index = best_option(field.options, value)
    if index is None:
        return None
    _check(option(page, field, index))
    return field.options[index]


def _checkboxes(page: Page, field: Field, value: str, _files: Files) -> str | None:
    picked = [best_option(field.options, part) for part in value.split(MULTI_VALUE_SEPARATOR)]
    indexes = sorted({index for index in picked if index is not None})
    for index in indexes:
        _check(option(page, field, index))
    return MULTI_VALUE_SEPARATOR.join(field.options[index] for index in indexes) or None


def _checkbox(page: Page, field: Field, value: str, _files: Files) -> str | None:
    checked = is_truthy(value)
    _check(control(page, field).first, checked)
    return "yes" if checked else "no"


def _file(page: Page, field: Field, value: str, files: Files) -> str | None:
    chosen = {RESUME_FILE: files.resume, COVER_LETTER_FILE: files.cover_letter}
    if value not in chosen:
        return None
    path = chosen[value]
    if path is None:
        return f"{value.lower()} {NOT_UPLOADED}"
    control(page, field).first.set_input_files(str(path), timeout=ACTION_TIMEOUT_MS)
    return path.name


def _suggestions(page: Page) -> Locator:
    choices = page.locator(VISIBLE_OPTIONS)
    try:
        choices.first.wait_for(state="visible", timeout=SUGGESTIONS_TIMEOUT_MS)
    except PlaywrightTimeoutError:
        return choices
    page.wait_for_timeout(COMBOBOX_SETTLE_MS)
    return choices


def _combobox(page: Page, field: Field, value: str, _files: Files) -> str | None:
    box = control(page, field).first
    box.click(timeout=ACTION_TIMEOUT_MS)
    box.fill(value, timeout=ACTION_TIMEOUT_MS)
    choices = _suggestions(page)
    names = [" ".join(name.split()) for name in choices.all_inner_texts()]
    index = best_option(names, value)
    if index is not None:
        choices.nth(index).click(timeout=ACTION_TIMEOUT_MS)
        return names[index]
    box.press("Tab")
    page.wait_for_timeout(COMBOBOX_SETTLE_MS)
    return box.input_value() or None


FILLERS: dict[FieldKind, Filler] = {
    FieldKind.TEXT: _text,
    FieldKind.EMAIL: _text,
    FieldKind.TEL: _text,
    FieldKind.URL: _text,
    FieldKind.DATE: _text,
    FieldKind.TEXTAREA: _text,
    FieldKind.NUMBER: _number,
    FieldKind.SELECT: _select,
    FieldKind.RADIO: _radio,
    FieldKind.CHECKBOXES: _checkboxes,
    FieldKind.CHECKBOX: _checkbox,
    FieldKind.FILE: _file,
    FieldKind.COMBOBOX: _combobox,
}


def fill_field(page: Page, field: Field, value: str, files: Files) -> str | None:
    try:
        return FILLERS[field.kind](page, field, value, files)
    except PlaywrightError as error:
        log.info("couldn't fill %s (%s): %s", field.id, field.kind, error)
        return None
