import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from truapply.core.errors import LatexMissingError
from truapply.resume.render import find_pdflatex

WINDOWS = sys.platform == "win32"
TINYTEX_SCRIPT_URL = (
    "https://yihui.org/tinytex/install-bin-windows.bat"
    if WINDOWS
    else "https://yihui.org/tinytex/install-bin-unix.sh"
)
DOWNLOAD_TIMEOUT_S = 120
INSTALL_TIMEOUT_S = 900


def _tool(name: str) -> str:
    found = shutil.which(name)
    if found is None:
        raise LatexMissingError(f"`{name}` is needed to install TinyTeX.")
    return found


def _installer(script: Path) -> list[str]:
    if WINDOWS:
        return [_tool("cmd"), "/c", str(script)]
    return [_tool("sh"), str(script), "", "--no-path"]


def install_tinytex() -> Path:
    with tempfile.TemporaryDirectory(prefix="truapply-tinytex-") as work:
        script = Path(work) / ("install-tinytex.bat" if WINDOWS else "install-tinytex.sh")
        try:
            subprocess.run(  # noqa: S603
                [_tool("curl"), "-fsSL", TINYTEX_SCRIPT_URL, "-o", str(script)],
                check=True,
                capture_output=True,
                timeout=DOWNLOAD_TIMEOUT_S,
            )
            subprocess.run(  # noqa: S603
                _installer(script),
                check=False,
                capture_output=True,
                timeout=INSTALL_TIMEOUT_S,
            )
        except subprocess.CalledProcessError:
            raise LatexMissingError(
                f"Couldn't download TinyTeX from {TINYTEX_SCRIPT_URL}."
            ) from None
        except subprocess.TimeoutExpired:
            raise LatexMissingError("Installing TinyTeX took too long.") from None
    pdflatex = find_pdflatex()
    if pdflatex is None:
        raise LatexMissingError("TinyTeX didn't install correctly.")
    return pdflatex
