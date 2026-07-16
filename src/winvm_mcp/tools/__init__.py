"""MCP tool registry: shared context, helpers, and ``register_all``."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from functools import wraps
from typing import TYPE_CHECKING, Any

from ..config import VMConfig
from ..debug.kd_engine import KDEngine
from ..errors import KdError, WinvmError
from ..transports.ssh import SshClient
from ..transports.vmrun import VmrunClient

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP


@dataclass
class ServerContext:
    """Shared services constructed once per server and closed over by tools."""

    cfg: VMConfig
    vmrun: VmrunClient
    ssh: SshClient
    kd: KDEngine


def tool_error(msg: str) -> str:
    """Wrap an error message so the LLM sees it without crashing the MCP."""
    return f"[ERROR] {msg}"


def ok(text: str) -> str:
    """Normalize empty output so the LLM always sees something."""
    return text if text else "(no output)"


def safe(func: Callable[..., Any]) -> Callable[..., Any]:
    """Map :class:`~winvm_mcp.errors.WinvmError` to a structured tool-error string."""

    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            return func(*args, **kwargs)
        except WinvmError as exc:
            return tool_error(str(exc))

    return wrapper


def run_transient(
    kd: KDEngine,
    target: str,
    commands: list[str],
    connect_timeout: int = 180,
    run_timeout: int = 180,
) -> str:
    """Open a transient KD session, run a batch, always close.

    Used by ``analyze_*`` and ``vuln_*`` tools that open their own session
    rather than relying on a persistent ``kd_connect``.
    """
    try:
        kd.connect(target=target, timeout=connect_timeout)
    except KdError as exc:
        return tool_error(f"Could not open {target}: {exc}")
    try:
        return kd.run_batch(commands, timeout=run_timeout)
    finally:
        kd.disconnect()


# Import tool modules after the helpers they depend on are defined, so each
# module's ``from . import ok, safe, ...`` resolves at import time.
from . import (  # noqa: E402
    analyze,
    guest,
    kd,
    shell,
    snapshot,
    vm,
    vuln,
)


def register_all(mcp: FastMCP, ctx: ServerContext) -> None:
    """Register every tool module onto the FastMCP server."""
    vm.register(mcp, ctx)
    snapshot.register(mcp, ctx)
    guest.register(mcp, ctx)
    shell.register(mcp, ctx)
    kd.register(mcp, ctx)
    analyze.register(mcp, ctx)
    vuln.register(mcp, ctx)
