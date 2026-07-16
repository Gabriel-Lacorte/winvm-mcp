"""vmrun subprocess client — VM lifecycle and VMware-Tools guest operations.

``vmrun`` always needs the guest credentials (``-gu``/``-gp``) for in-guest
operations, so :meth:`VmrunClient.build_argv` prepends them. The argv builder
is pure and unit-tested; the actual subprocess call is a thin, injectable
runner.
"""

from __future__ import annotations

import subprocess
from collections.abc import Callable
from dataclasses import dataclass

from ..config import VMConfig
from ..errors import VmrunError

__all__ = ["CommandResult", "VmrunClient", "default_runner"]


@dataclass(frozen=True)
class CommandResult:
    """Outcome of a vmrun invocation."""

    rc: int
    out: str
    err: str


def default_runner(cmd: list[str], timeout: int) -> CommandResult:
    """Run ``cmd`` capturing output; raise :class:`VmrunError` if binary missing."""
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, check=False)
    except subprocess.TimeoutExpired:
        return CommandResult(124, "", f"vmrun timed out after {timeout}s")
    except FileNotFoundError as exc:
        raise VmrunError(f"vmrun not found at {cmd[0]}") from exc
    return CommandResult(proc.returncode, proc.stdout, proc.stderr)


class VmrunClient:
    """Thin wrapper around the host-side ``vmrun`` binary."""

    def __init__(
        self, cfg: VMConfig, runner: Callable[[list[str], int], CommandResult] = default_runner
    ) -> None:
        self._cfg = cfg
        self._runner = runner

    def build_argv(self, args: list[str], auth: bool = True) -> list[str]:
        """Build the full vmrun argv.

        ``auth=True`` prepends the guest credentials (``-gu``/``-gp``) required
        by ``*InGuest`` commands; host-level commands (``list``, ``start``,
        ``snapshot``, …) pass ``auth=False``.
        """
        cmd: list[str] = [self._cfg.vmrun]
        if self._cfg.vmrun_type:
            cmd.append(self._cfg.vmrun_type)
        if auth:
            cmd += ["-gu", self._cfg.username, "-gp", self._cfg.password]
        cmd += list(args)
        return cmd

    def run(self, args: list[str], timeout: int = 120, auth: bool = True) -> CommandResult:
        """Run a vmrun sub-command and return its captured result."""
        return self._runner(self.build_argv(args, auth=auth), timeout)
