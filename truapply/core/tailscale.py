import json
import shutil
import subprocess
import sys
from pathlib import Path

INSTALLED = {
    "darwin": Path("/Applications/Tailscale.app/Contents/MacOS/Tailscale"),
    "win32": Path("C:/Program Files/Tailscale/tailscale.exe"),
}
WAIT_S = 3


def _binary() -> str | None:
    found = shutil.which("tailscale")
    if found:
        return found
    known = INSTALLED.get(sys.platform)
    return str(known) if known and known.is_file() else None


def _status(binary: str) -> object:
    try:
        done = subprocess.run(  # noqa: S603
            [binary, "status", "--json"], capture_output=True, timeout=WAIT_S, check=False
        )
        return json.loads(done.stdout)
    except (OSError, subprocess.TimeoutExpired, json.JSONDecodeError):
        return None


def device_name() -> str | None:
    binary = _binary()
    status = _status(binary) if binary else None
    me = status.get("Self") if isinstance(status, dict) else None
    name = me.get("DNSName") if isinstance(me, dict) else None
    return name.rstrip(".") if isinstance(name, str) and name.strip(".") else None
