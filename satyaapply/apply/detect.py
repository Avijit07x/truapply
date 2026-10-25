import re
from enum import StrEnum
from functools import cache
from importlib import resources

from playwright.sync_api import Page

CONFIRMED = re.compile(
    r"application (was |has been )?(successfully )?(submitted|sent|received)"
    r"|thank(s| you) for (applying|your application|submitting)"
    r"|successfully (applied|submitted)"
    r"|we('ve| have) received your application"
    r"|you('ve| have) (successfully )?applied",
    re.IGNORECASE,
)
CLOSED = re.compile(
    r"no longer (accepting applications|available|open|accepting)"
    r"|(this |the )?(job|position|posting|role) (is |has been )?(closed|filled|expired|removed)"
    r"|job (not found|does not exist)"
    r"|position has been filled",
    re.IGNORECASE,
)
ALREADY_APPLIED = re.compile(
    r"you('ve| have) already applied|already submitted an application"
    r"|application (is )?already (submitted|received)",
    re.IGNORECASE,
)
HUMAN_CHECK_TEXT = re.compile(
    r"verify (that )?you('re| are) (a )?human|are you a robot|press (and|&) hold"
    r"|complete the security check",
    re.IGNORECASE,
)
HUMAN_CHECK_FRAME = re.compile(
    r"recaptcha/(api2|enterprise)/anchor(?!.*size=invisible)"
    r"|hcaptcha\.com|challenges\.cloudflare\.com",
    re.IGNORECASE,
)


class PageState(StrEnum):
    FORM = "form"
    NO_FORM = "no_form"
    CLOSED = "closed"
    ALREADY_APPLIED = "already_applied"
    HUMAN_CHECK = "human_check"


def is_confirmed(text: str) -> bool:
    return bool(CONFIRMED.search(text))


def text_state(text: str) -> PageState | None:
    if ALREADY_APPLIED.search(text):
        return PageState.ALREADY_APPLIED
    if HUMAN_CHECK_TEXT.search(text):
        return PageState.HUMAN_CHECK
    if CLOSED.search(text):
        return PageState.CLOSED
    return None


def has_human_check(page: Page) -> bool:
    return any(HUMAN_CHECK_FRAME.search(frame.url) for frame in page.frames)


@cache
def _errors_script() -> str:
    return resources.files("satyaapply.apply").joinpath("errors.js").read_text("utf-8")


def form_errors(page: Page) -> list[str]:
    found = page.evaluate(_errors_script())
    return [str(item) for item in found] if isinstance(found, list) else []
