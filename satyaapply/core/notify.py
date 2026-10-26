import shutil
import subprocess
import sys

TIMEOUT_S = 10


def _quoted(text: str) -> str:
    return '"' + text.replace("\\", "\\\\").replace('"', '\\"') + '"'


def _command(title: str, message: str) -> list[str] | None:
    if sys.platform == "darwin":
        tool = shutil.which("osascript")
        script = f"display notification {_quoted(message)} with title {_quoted(title)}"
        return [tool, "-e", script] if tool else None
    tool = shutil.which("notify-send")
    return [tool, title, message] if tool else None


def send(title: str, message: str) -> None:
    command = _command(title, message)
    if command is None:
        return
    try:
        subprocess.run(command, capture_output=True, check=False, timeout=TIMEOUT_S)  # noqa: S603
    except (OSError, subprocess.SubprocessError):
        return
