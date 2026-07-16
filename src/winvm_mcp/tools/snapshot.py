"""Snapshot tools — the basis of reproducible vulnerability analysis."""

from __future__ import annotations

from typing import TYPE_CHECKING

from . import ok, safe, tool_error

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP

    from . import ServerContext


def register(mcp: FastMCP, ctx: ServerContext) -> None:
    cfg = ctx.cfg
    vmrun = ctx.vmrun

    @mcp.tool()
    @safe
    def snapshot_list() -> str:
        """List all snapshots of the configured VM."""
        res = vmrun.run(["listSnapshots", cfg.vmx], timeout=60, auth=False)
        if res.rc != 0:
            return tool_error(f"listSnapshots rc={res.rc}: {res.err.strip()}")
        return res.out.strip() or "(no snapshots)"

    @mcp.tool()
    @safe
    def snapshot_create(name: str) -> str:
        """Create a new snapshot. Names should be short and unique (e.g. 'clean-w10', 'poc-triggered')."""
        res = vmrun.run(["snapshot", cfg.vmx, name], timeout=180, auth=False)
        return ok(f"snapshot '{name}' rc={res.rc}: {res.err.strip() or res.out.strip()}")

    @mcp.tool()
    @safe
    def snapshot_revert(name: str) -> str:
        """Revert the VM to a previously-created snapshot (discards current state)."""
        res = vmrun.run(["revertToSnapshot", cfg.vmx, name], timeout=180, auth=False)
        return ok(f"revert to '{name}' rc={res.rc}: {res.err.strip() or res.out.strip()}")

    @mcp.tool()
    @safe
    def snapshot_delete(name: str) -> str:
        """Delete a snapshot (frees disk; cannot be undone)."""
        res = vmrun.run(["deleteSnapshot", cfg.vmx, name], timeout=180, auth=False)
        return ok(f"delete '{name}' rc={res.rc}: {res.err.strip() or res.out.strip()}")
