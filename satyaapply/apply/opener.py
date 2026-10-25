import re
from http import HTTPStatus

from playwright.sync_api import Page

from satyaapply.apply.detect import PageState, has_human_check, text_state
from satyaapply.apply.fields import read_fields
from satyaapply.browser.page import (
    NAVIGATION_TIMEOUT_MS,
    find_button,
    visible_text,
    wait_until_quiet,
)
from satyaapply.core.models import Job

APPLY_OPENER = re.compile(
    r"^\s*(apply( now| for this (job|position|role))?|i'?m interested"
    r"|start (your )?application)\s*$",
    re.IGNORECASE,
)


def _state_without_form(page: Page) -> PageState:
    if has_human_check(page):
        return PageState.HUMAN_CHECK
    return text_state(visible_text(page)) or PageState.NO_FORM


def open_form(page: Page, job: Job) -> PageState:
    response = page.goto(
        job.apply_url or job.url, wait_until="domcontentloaded", timeout=NAVIGATION_TIMEOUT_MS
    )
    if response is not None and response.status == HTTPStatus.NOT_FOUND:
        return PageState.CLOSED
    wait_until_quiet(page)
    if read_fields(page):
        return (
            PageState.ALREADY_APPLIED
            if text_state(visible_text(page)) is PageState.ALREADY_APPLIED
            else PageState.FORM
        )
    opener = find_button(page.locator("body"), APPLY_OPENER)
    if opener is None:
        return _state_without_form(page)
    opener.click()
    wait_until_quiet(page)
    return PageState.FORM if read_fields(page) else _state_without_form(page)
