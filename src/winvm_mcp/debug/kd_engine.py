"""Persistent ``cdb.exe`` session over a PTY-backed SSH channel.

The debugger runs **inside the guest** (no WinDbg-on-Linux dependency). A single
SSH channel is kept open across commands so breakpoints and session state
persist until :meth:`KDEngine.disconnect`.

Supported connect targets:

* ``live``    — ``cdb.exe -k``            (local kernel; needs debug/test mode)
* ``livekd``  — ``kd-livekd.bat``         (kernel of a running system, no reboot)
* ``dump:<p>`` — ``cdb.exe -z <path>``     (post-mortem crash/hibernation dump)
"""

from __future__ import annotations

import contextlib
import time

import paramiko

from ..config import VMConfig
from ..errors import KdError, KdNotConnectedError
from ..log import get_logger
from ..transports.ssh import SshClient
from . import kd_parse

__all__ = ["KDEngine"]

_log = get_logger("kd")


class KDEngine:
    """Drives a single persistent cdb/kd session in the guest."""

    START_TIMEOUT = 90  # opening a large dump can take a while

    def __init__(self, ssh: SshClient, cfg: VMConfig) -> None:
        self._ssh = ssh
        self._cfg = cfg
        self._client: paramiko.SSHClient | None = None
        self._chan: paramiko.Channel | None = None
        self.target: str = ""
        self.last_banner: str = ""

    @property
    def connected(self) -> bool:
        return self._chan is not None and not self._chan.closed

    # -- low-level IO -------------------------------------------------------
    def _drain(self, deadline: float, idle_quiet: float = 1.5) -> str:
        """Read until the prompt re-appears or the stream goes idle."""
        buf = bytearray()
        last_recv = time.time()
        while True:
            if self._chan is None:
                break
            if self._chan.recv_ready():
                chunk = self._chan.recv(8192)
                if not chunk:
                    break
                buf.extend(chunk)
                last_recv = time.time()
                if kd_parse.has_trailing_prompt(buf.decode("utf-8", errors="replace")):
                    break
            else:
                if time.time() > deadline:
                    break
                if buf and time.time() - last_recv > idle_quiet:
                    break
                time.sleep(0.05)
        return buf.decode("utf-8", errors="replace")

    # -- target command -----------------------------------------------------
    def _build_command(self, target: str) -> str:
        if target == "live":
            return f'"{self._cfg.debugger_path}" -k'
        if target == "livekd":
            # Launcher bat lives in the guest workdir (provisioned by bootstrap).
            return rf'"{self._cfg.guest_workdir}\kd-livekd.bat"'
        if target.startswith("dump:"):
            dump = target[len("dump:") :].strip()
            return f'"{self._cfg.debugger_path}" -z "{dump}"'
        raise KdError("target must be 'live', 'livekd', or 'dump:<path-to-.dmp>'")

    # -- lifecycle ----------------------------------------------------------
    def connect(self, target: str = "livekd", timeout: int = START_TIMEOUT) -> str:
        if self.connected:
            self.disconnect()
        if not self._cfg.ssh_host:
            raise KdError("ssh_host is not configured; kd tools require SSH.")

        cmd = self._build_command(target)
        try:
            client, chan = self._ssh.open_pty_session(cmd)
        except Exception as exc:  # SshError or transport issue
            raise KdError(f"kd connect failed: {exc}") from exc

        self._client = client
        self._chan = chan
        self.target = target

        # LiveKd can take 30-90s to generate the live dump and reach the prompt.
        deadline = time.time() + timeout
        banner = ""
        while time.time() < deadline:
            chunk = self._drain(time.time() + 30, idle_quiet=3.0)
            banner += chunk
            self.last_banner = banner
            if kd_parse.PROMPT_TAIL_RE.search(banner.rstrip()):
                break
            if self._chan is None or self._chan.exit_status_ready():
                break
        return banner

    def disconnect(self) -> None:
        if self._chan is not None and not self._chan.closed:
            with contextlib.suppress(Exception):
                self._chan.sendall(b"q\r")
                time.sleep(0.5)
            with contextlib.suppress(Exception):
                self._chan.close()
        if self._client is not None:
            with contextlib.suppress(Exception):
                self._client.close()
        self._chan = None
        self._client = None
        self.target = ""

    # -- command execution --------------------------------------------------
    def command(self, cmd: str, timeout: int = 60) -> str:
        """Send one debugger command and return its cleaned output."""
        if not self.connected:
            raise KdNotConnectedError("kd engine is not connected; call kd_connect first.")
        assert self._chan is not None
        # Flush leftover bytes from the previous command / banner.
        while self._chan.recv_ready():
            self._chan.recv(4096)
        time.sleep(0.1)
        while self._chan.recv_ready():
            self._chan.recv(4096)
        # PTY on Windows expects \r, not \n.
        self._chan.sendall((cmd.rstrip() + "\r").encode("utf-8", errors="replace"))
        raw = self._drain(time.time() + timeout)
        return kd_parse.clean_command_output(raw, cmd)

    def run_batch(self, commands: list[str], timeout: int = 120) -> str:
        """Run several commands sequentially; combined, sectioned output."""
        parts: list[str] = []
        for cmd in commands:
            parts.append(f"### kd> {cmd}")
            try:
                parts.append(self.command(cmd, timeout=timeout))
            except KdError as exc:
                parts.append(f"[ERROR] {exc}")
                break
        return "\n".join(parts)
