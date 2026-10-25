from collections.abc import Callable
from dataclasses import dataclass
from functools import partial

from satyaapply.ai.tasks import ping
from satyaapply.browser.chrome import browser_name
from satyaapply.core.errors import SatyaApplyError
from satyaapply.core.paths import Paths
from satyaapply.core.profile import Profile, load
from satyaapply.resume.master import load_resume, master_pdf


@dataclass(frozen=True)
class Check:
    name: str
    ok: bool
    detail: str
    fix: str = ""


def _attempt(name: str, probe: Callable[[], str]) -> Check:
    try:
        return Check(name, True, probe())
    except SatyaApplyError as error:
        return Check(name, False, str(error), error.hint)


def _claude() -> str:
    ping()
    return "installed and logged in"


def _resume(paths: Paths, profile: Profile) -> str:
    rendered = master_pdf(paths, load_resume(profile))
    plural = "" if rendered.pages == 1 else "s"
    return f"{profile.resume.format} resume builds ({rendered.pages} page{plural})"


def run_checks(paths: Paths) -> list[Check]:
    checks = [_attempt("Claude Code", _claude)]
    try:
        profile = load(paths)
    except SatyaApplyError as error:
        checks.append(Check("Profile", False, str(error), error.hint))
    else:
        checks.append(Check("Profile", True, str(paths.profile)))
        checks.append(_attempt("Resume", partial(_resume, paths, profile)))
    checks.append(_attempt("Browser", browser_name))
    return checks


def report(checks: list[Check]) -> int:
    for check in checks:
        print(f"{'✔' if check.ok else '✘'} {check.name}: {check.detail}")
        if check.fix:
            print(f"   → {check.fix}")
    return 0 if all(check.ok for check in checks) else 1
