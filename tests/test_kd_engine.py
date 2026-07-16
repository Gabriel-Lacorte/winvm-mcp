"""Unit tests for the KD engine using a fake SSH channel (no VM)."""

from __future__ import annotations

import pytest

from winvm_mcp.config import VMConfig
from winvm_mcp.debug.kd_engine import KDEngine
from winvm_mcp.errors import KdError, KdNotConnectedError


class _FakeChan:
    def __init__(self) -> None:
        self.closed = False
        self.sent: list[bytes] = []
        self._q = bytearray()

    def recv_ready(self) -> bool:
        return len(self._q) > 0

    def recv(self, n: int) -> bytes:
        chunk = bytes(self._q[:n])
        del self._q[: len(chunk)]
        return chunk

    def sendall(self, b: bytes) -> None:
        self.sent.append(b)
        cmd = b.decode("utf-8", "replace").strip()
        responses = {
            "kb": b"0: kd> kb\r\nRetAddr\r\n00 nt!foo\r\n0: kd> ",
            "r": b"lkd> r\r\nrax=0001 rbx=0002\r\nlkd> ",
            "!process 0 0": b"0: kd> !process 0 0\r\nPROCESS ffff\r\n0: kd> ",
        }
        if cmd in responses:
            self._q.extend(responses[cmd])

    def exit_status_ready(self) -> bool:
        return False

    def close(self) -> None:
        self.closed = True


class _FakeSsh:
    def open_pty_session(self, command: str) -> tuple[object, _FakeChan]:
        return object(), _FakeChan()


def _cfg() -> VMConfig:
    return VMConfig(vmx="/x", username="u", password="p", ssh_host="h")


def test_command_requires_connection() -> None:
    kd = KDEngine(_FakeSsh(), _cfg())  # type: ignore[arg-type]
    with pytest.raises(KdNotConnectedError):
        kd.command("kb")


def test_command_cleans_echo_and_prompt() -> None:
    kd = KDEngine(_FakeSsh(), _cfg())  # type: ignore[arg-type]
    kd._chan = _FakeChan()  # type: ignore[assignment]
    assert isinstance(kd._chan, _FakeChan)
    out = kd.command("kb")
    assert out == "RetAddr\n00 nt!foo"
    assert kd._chan.sent[-1] == b"kb\r"


def test_run_batch_sections_output() -> None:
    kd = KDEngine(_FakeSsh(), _cfg())  # type: ignore[arg-type]
    kd._chan = _FakeChan()  # type: ignore[assignment]
    out = kd.run_batch(["kb", "r"])
    assert "### kd> kb" in out
    assert "### kd> r" in out
    assert "RetAddr" in out
    assert "rax=0001" in out


def test_disconnect_closes_channel() -> None:
    kd = KDEngine(_FakeSsh(), _cfg())  # type: ignore[arg-type]
    chan = _FakeChan()
    kd._chan = chan  # type: ignore[assignment]
    kd.disconnect()
    assert chan.closed
    assert not kd.connected
    assert kd.target == ""


def test_build_command_modes() -> None:
    kd = KDEngine(_FakeSsh(), _cfg())  # type: ignore[arg-type]
    assert "-k" in kd._build_command("live")
    assert "kd-livekd.bat" in kd._build_command("livekd")
    assert '-z "C:\\dump.dmp"' in kd._build_command("dump:C:\\dump.dmp")
    with pytest.raises(KdError):
        kd._build_command("bogus")
