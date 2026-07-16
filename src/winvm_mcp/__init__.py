"""winvm-mcp — MCP server for VMware-hosted Windows VM security research.

Exposes four layers of tools to an LLM:

* ``vm_*``      — VM lifecycle (vmrun): start/stop/suspend/pause/snapshot.
* ``guest_*``   — guest interaction via vmrun (exec, file transfer, screen,
                  processes) and SSH (interactive PowerShell / cmd).
* ``kd_*``      — kernel / crash-dump debugging via ``cdb.exe`` driven over SSH.
* ``analyze_*`` / ``vuln_*`` — higher-level compositions of the primitives.

Security note: this server drives a *local* lab VM the researcher owns. It
exposes powerful primitives (remote command execution, kernel memory access) on
purpose; keep the MCP transport local (stdio) and the VM on an isolated
network (NAT / host-only).
"""

from __future__ import annotations

__version__ = "1.0.0"

__all__ = ["__version__"]
