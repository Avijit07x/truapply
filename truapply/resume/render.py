import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from truapply.core.errors import LatexFailedError
from truapply.resume.contract import Rendered

PDFLATEX_TIMEOUT_S = 60
JOB_NAME = "resume"
SANDBOX_ENV = {"openin_any": "p", "openout_any": "p"}
TINYTEX_BIN_DIRS = (Path("~/Library/TinyTeX/bin"), Path("~/.TinyTeX/bin"))
COMMAND = re.compile(r"\\([A-Za-z@]+)")
MISSING_FILE = re.compile(r"! LaTeX Error: File `([^']+)' not found")
MISSING_FONT = re.compile(r"Font \S+=(\S+) at \S+ not loadable: Metric \(TFM\) file not found")
OUTPUT_PAGES = re.compile(r"Output\s+written\s+on\s+\S+\s+\((\d+)\s+pages?", re.S)
LOG_ERROR = re.compile(r"^! .+$", re.M)


def latex_commands(source: str) -> set[str]:
    return set(COMMAND.findall(source))


def find_pdflatex() -> Path | None:
    on_path = shutil.which("pdflatex")
    if on_path:
        return Path(on_path)
    for bin_dir in TINYTEX_BIN_DIRS:
        for candidate in sorted(bin_dir.expanduser().glob("*/pdflatex")):
            return candidate
    return None


def missing_file(log: str) -> str | None:
    if match := MISSING_FILE.search(log):
        return match.group(1)
    if match := MISSING_FONT.search(log):
        return f"{match.group(1)}.tfm"
    return None


def page_count(log: str) -> int:
    match = OUTPUT_PAGES.search(log)
    return int(match.group(1)) if match else 0


def _compile(pdflatex: Path, workdir: Path) -> tuple[int, str]:
    try:
        completed = subprocess.run(  # noqa: S603
            [
                str(pdflatex),
                "-interaction=nonstopmode",
                "-halt-on-error",
                "-no-shell-escape",
                f"{JOB_NAME}.tex",
            ],
            cwd=workdir,
            capture_output=True,
            text=True,
            errors="replace",
            timeout=PDFLATEX_TIMEOUT_S,
            env={**os.environ, **SANDBOX_ENV},
            check=False,
        )
    except subprocess.TimeoutExpired:
        raise LatexFailedError(f"timed out after {PDFLATEX_TIMEOUT_S} s", None) from None
    log_file = workdir / f"{JOB_NAME}.log"
    log = log_file.read_text(encoding="utf-8", errors="replace") if log_file.exists() else ""
    return completed.returncode, log or completed.stdout


def render_latex(source: str, target: Path, pdflatex: Path) -> Rendered:
    with tempfile.TemporaryDirectory(prefix="truapply-tex-") as work:
        workdir = Path(work)
        (workdir / f"{JOB_NAME}.tex").write_text(source, encoding="utf-8")
        returncode, log = _compile(pdflatex, workdir)
        pdf = workdir / f"{JOB_NAME}.pdf"
        if returncode != 0 or not pdf.exists():
            excerpt = " ".join(LOG_ERROR.findall(log)[:2]) or f"exit code {returncode}"
            raise LatexFailedError(excerpt, missing_file(log))
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(pdf, target)
    return Rendered(target, page_count(log))
