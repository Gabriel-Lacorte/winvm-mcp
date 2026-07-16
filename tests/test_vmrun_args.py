"""Tests for vmrun argv construction (no subprocess, no VM)."""

from __future__ import annotations

from winvm_mcp.config import VMConfig
from winvm_mcp.transports.vmrun import CommandResult, VmrunClient


def _client(**kw: object) -> VmrunClient:
    base: dict[str, object] = {"vmx": "/x/w.vmx", "username": "u", "password": "p"}
    base.update(kw)
    return VmrunClient(VMConfig(**base))  # type: ignore[arg-type]


def test_basic_argv_has_guest_auth() -> None:
    argv = _client().build_argv(["list"])
    assert argv == ["/usr/bin/vmrun", "-gu", "u", "-gp", "p", "list"]


def test_guest_ops_include_vmx_and_auth() -> None:
    argv = _client().build_argv(["listProcessesInGuest", "/x/w.vmx"])
    gu = argv.index("-gu")
    gp = argv.index("-gp")
    assert argv[gu + 1] == "u"
    assert argv[gp + 1] == "p"
    assert argv[-2:] == ["listProcessesInGuest", "/x/w.vmx"]


def test_vmrun_type_inserted() -> None:
    argv = _client(vmrun_type="-T ws").build_argv(["start", "/x/w.vmx", "nogui"])
    assert argv[0] == "/usr/bin/vmrun"
    assert argv[1] == "-T ws"
    assert argv[2] == "-gu"


def test_no_type_when_blank() -> None:
    argv = _client(vmrun_type="").build_argv(["stop", "/x/w.vmx"])
    # No product-type token: -gu follows the binary directly.
    assert argv[1] == "-gu"


def test_no_auth_strips_credentials() -> None:
    # Host-level commands (list/start/snapshot) must not send guest creds.
    argv = _client().build_argv(["list"], auth=False)
    assert "-gu" not in argv
    assert "-gp" not in argv
    assert argv == ["/usr/bin/vmrun", "list"]


def test_runner_is_injected_and_used() -> None:
    calls: list[tuple[list[str], int]] = []

    def fake(cmd: list[str], timeout: int) -> CommandResult:
        calls.append((cmd, timeout))
        return CommandResult(0, "ok", "")

    c = VmrunClient(VMConfig(vmx="/x", username="u", password="p"), runner=fake)
    res = c.run(["list"], timeout=42)
    assert res == CommandResult(0, "ok", "")
    assert calls[0][1] == 42
    assert calls[0][0][0] == "/usr/bin/vmrun"
