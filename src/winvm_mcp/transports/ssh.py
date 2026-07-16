"""SSH client for the Windows guest (paramiko-backed).

Two entry shapes:

* :meth:`SshClient.exec` / :meth:`SshClient.powershell` — one-shot commands.
  The exit code comes from ``channel.recv_exit_status()`` and stdout/stderr are
  read from the **separate** streams paramiko provides. This replaces the old
  ``cmd /c "… 2>&1 & echo __RC__%errorlevel%"`` trick, whose ``%errorlevel%``
  expanded at parse time and whose ``2>&1`` merged stderr into stdout.
* :meth:`SshClient.open_pty_session` — a PTY-backed channel for the
  interactive cdb session (see :mod:`winvm_mcp.debug.kd_engine`).
"""

from __future__ import annotations

import base64
from dataclasses import dataclass

import paramiko

from ..config import VMConfig
from ..errors import SshError
from ..log import get_logger

__all__ = ["SshResult", "SshClient"]

_log = get_logger("ssh")


@dataclass(frozen=True)
class SshResult:
    """Outcome of a one-shot SSH command."""

    rc: int
    out: str
    err: str


def _apply_host_key_policy(client: paramiko.SSHClient, policy: str) -> None:
    if policy == "known_hosts":
        client.load_system_host_keys()
        client.set_missing_host_key_policy(paramiko.RejectPolicy())
    else:  # "auto_add"
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())


class SshClient:
    """Drives one-shot commands and interactive PTY sessions on the guest."""

    def __init__(self, cfg: VMConfig) -> None:
        self._cfg = cfg

    # -- connection ---------------------------------------------------------
    def _connect(self) -> paramiko.SSHClient:
        if not self._cfg.ssh_host:
            raise SshError("ssh_host is not configured in [vm].")
        client = paramiko.SSHClient()
        _apply_host_key_policy(client, self._cfg.ssh_host_key_policy)
        try:
            client.connect(
                hostname=self._cfg.ssh_host,
                port=self._cfg.ssh_port,
                username=self._cfg.ssh_username,
                password=self._cfg.ssh_password,
                timeout=15,
                allow_agent=False,
                look_for_keys=False,
            )
        except Exception as exc:  # paramiko raises many concrete types
            raise SshError(
                f"SSH connect to {self._cfg.ssh_host}:{self._cfg.ssh_port} failed: {exc}"
            ) from exc
        return client

    # -- one-shot exec ------------------------------------------------------
    def exec(self, command: str, timeout: int = 120) -> SshResult:
        """Run ``command`` via the default shell; return rc + separate streams.

        On Windows OpenSSH the default shell is ``cmd.exe``, so use cmd syntax.
        """
        client = self._connect()
        try:
            _stdin, stdout, stderr = client.exec_command(command, timeout=timeout)
            out = stdout.read().decode("utf-8", errors="replace")
            err = stderr.read().decode("utf-8", errors="replace")
            rc = stdout.channel.recv_exit_status()
            return SshResult(rc=rc, out=out, err=err)
        except Exception as exc:
            raise SshError(f"SSH exec failed: {exc}") from exc
        finally:
            client.close()

    def powershell(self, script: str, timeout: int = 180) -> SshResult:
        """Run a PowerShell snippet via ``-EncodedCommand`` (UTF-16-LE base64).

        Avoids quoting hell across SSH → cmd → PowerShell.
        """
        encoded = base64.b64encode(script.encode("utf-16-le")).decode("ascii")
        return self.exec(
            f"powershell -NoProfile -NonInteractive -EncodedCommand {encoded}",
            timeout=timeout,
        )

    # -- interactive PTY session (for the kd engine) ------------------------
    def open_pty_session(self, command: str) -> tuple[paramiko.SSHClient, paramiko.Channel]:
        """Open a PTY-backed channel running ``command`` (for the cdb engine)."""
        client = self._connect()
        try:
            chan = client.get_transport().open_session()
            chan.get_pty()
            chan.exec_command(command)
        except Exception as exc:
            client.close()
            raise SshError(f"SSH PTY session failed: {exc}") from exc
        return client, chan
