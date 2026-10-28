import json
import shutil
import subprocess
from collections.abc import Sequence

import pytest

from truapply.core import tailscale


def answering(output: bytes) -> object:
    def run(command: Sequence[str], **_options: object) -> subprocess.CompletedProcess[bytes]:
        return subprocess.CompletedProcess(command, 0, output, b"")

    return run


def test_your_device_name_is_read_from_tailscale(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(shutil, "which", lambda _name: "tailscale")
    status = {"Self": {"DNSName": "laptop.tail1234.ts.net."}}
    monkeypatch.setattr(subprocess, "run", answering(json.dumps(status).encode()))
    assert tailscale.device_name() == "laptop.tail1234.ts.net"


@pytest.mark.parametrize("output", [b"not json", b"{}", b'{"Self": {"DNSName": ""}}'])
def test_no_usable_answer_means_no_name(monkeypatch: pytest.MonkeyPatch, output: bytes) -> None:
    monkeypatch.setattr(shutil, "which", lambda _name: "tailscale")
    monkeypatch.setattr(subprocess, "run", answering(output))
    assert tailscale.device_name() is None


def test_without_tailscale_there_is_no_name(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(shutil, "which", lambda _name: None)
    monkeypatch.setattr(tailscale, "INSTALLED", {})
    assert tailscale.device_name() is None
