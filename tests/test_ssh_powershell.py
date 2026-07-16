"""Tests for the SSH transport's command shaping (no socket, no VM)."""

from __future__ import annotations

import base64

import pytest

from winvm_mcp.config import VMConfig
from winvm_mcp.errors import SshError
from winvm_mcp.transports.ssh import SshClient, SshResult


def _client(**kw: object) -> SshClient:
    base: dict[str, object] = {"vmx": "/x", "username": "u", "password": "p", "ssh_host": "h"}
    base.update(kw)
    return SshClient(VMConfig(**base))  # type: ignore[arg-type]


def test_exec_requires_ssh_host() -> None:
    c = SshClient(VMConfig(vmx="/x", username="u", password="p"))  # no ssh_host
    with pytest.raises(SshError, match="ssh_host"):
        c.exec("whoami")


def test_powershell_encodedcommand_is_utf16le_base64() -> None:
    c = _client()
    captured: dict[str, object] = {}

    def fake_exec(command: str, timeout: int = 120) -> SshResult:
        captured["cmd"] = command
        captured["timeout"] = timeout
        return SshResult(0, "", "")

    c.exec = fake_exec  # type: ignore[method-assign]

    script = "Get-Process | Select-Object -First 5"
    c.powershell(script, timeout=99)

    cmd = str(captured["cmd"])
    assert cmd.startswith("powershell -NoProfile -NonInteractive -EncodedCommand ")
    token = cmd.rsplit(" ", 1)[-1]
    assert base64.b64decode(token).decode("utf-16-le") == script
    assert captured["timeout"] == 99


def test_powershell_preserves_unicode() -> None:
    c = _client()
    captured: dict[str, object] = {}
    c.exec = lambda command, timeout=120: (
        captured.__setitem__("cmd", command) or SshResult(0, "", "")
    )  # type: ignore[method-assign]
    script = 'Write-Output "café — αβγ ✓"'
    c.powershell(script)
    token = str(captured["cmd"]).rsplit(" ", 1)[-1]
    assert base64.b64decode(token).decode("utf-16-le") == script
