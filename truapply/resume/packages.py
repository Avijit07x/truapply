import logging
import re
import subprocess
from pathlib import Path

from truapply.core.errors import LatexFailedError
from truapply.resume.contract import Rendered
from truapply.resume.render import render_latex

TLMGR_TIMEOUT_S = 300
MAX_PACKAGE_INSTALLS = 15
ERROR_TAIL_LINES = 2
PACKAGE_LINE = re.compile(r"^([\w.+-]+):$", re.MULTILINE)

log = logging.getLogger(__name__)


def tlmgr(executable: Path, *arguments: str) -> str:
    action = " ".join(arguments)
    try:
        completed = subprocess.run(  # noqa: S603
            [str(executable), *arguments],
            capture_output=True,
            text=True,
            timeout=TLMGR_TIMEOUT_S,
            check=True,
        )
    except subprocess.CalledProcessError as error:
        output = f"{error.stdout or ''}\n{error.stderr or ''}".strip().splitlines()
        reason = " ".join(output[-ERROR_TAIL_LINES:]) or f"exit code {error.returncode}"
        raise LatexFailedError(f"`tlmgr {action}` failed: {reason}", None) from None
    except subprocess.TimeoutExpired:
        raise LatexFailedError(f"`tlmgr {action}` timed out", None) from None
    return completed.stdout


def package_for(executable: Path, file_name: str) -> str | None:
    match = PACKAGE_LINE.search(tlmgr(executable, "search", "--global", "--file", f"/{file_name}"))
    return match.group(1) if match else None


def render_installing(source: str, target: Path, pdflatex: Path) -> Rendered:
    manager = pdflatex.parent / "tlmgr"
    installed: list[str] = []
    for _ in range(MAX_PACKAGE_INSTALLS):
        try:
            return render_latex(source, target, pdflatex)
        except LatexFailedError as error:
            if error.missing_file is None or not manager.exists():
                raise
            if not installed:
                tlmgr(manager, "update", "--self")
            package = package_for(manager, error.missing_file)
            if package is None or package in installed:
                raise
            log.info("installing the LaTeX package %s", package)
            tlmgr(manager, "install", package)
            installed.append(package)
    raise LatexFailedError("too many missing LaTeX packages", None)
