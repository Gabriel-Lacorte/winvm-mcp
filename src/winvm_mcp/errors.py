"""Typed exceptions for winvm-mcp.

Tools translate these into structured ``[ERROR] …`` tool results rather than
letting exceptions propagate and tear down the MCP transport.
"""

from __future__ import annotations


class WinvmError(Exception):
    """Base class for every winvm-mcp error."""


class ConfigError(WinvmError):
    """Configuration is missing, unreadable, or invalid."""


class VmrunError(WinvmError):
    """A ``vmrun`` invocation failed (binary missing, non-zero rc, timeout)."""


class SshError(WinvmError):
    """An SSH connect/exec operation failed."""


class KdError(WinvmError):
    """A kernel-debugger operation failed."""


class KdNotConnectedError(KdError):
    """A kd command was issued with no active debugger session."""
