"""VM lifecycle tools (vmrun): start/stop/suspend/pause + state."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

from ..log import get_logger
from . import ok, safe

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP

    from . import ServerContext

_log = get_logger("tool.vm")


def register(mcp: FastMCP, ctx: ServerContext) -> None:
    cfg = ctx.cfg
    vmrun = ctx.vmrun

    @mcp.tool()
    @safe
    def vm_state() -> str:
        """Report whether the configured VM is running, and list all running VMs on this host."""
        res = vmrun.run(["list"], timeout=15, auth=False)
        running = res.out.strip().splitlines()
        is_up = any(cfg.vmx in line for line in running)
        tools_res = vmrun.run(["checkToolsState", cfg.vmx], timeout=30, auth=False)
        count = max(len(running) - 1, 0)
        return (
            f"VM running: {is_up}\n"
            f"Tools state: {tools_res.out.strip() or 'unknown'}\n"
            f"All running VMs ({count}):\n" + "\n".join(running[1:])
        )

    @mcp.tool()
    @safe
    def vm_start(headless: bool = True, timeout: int = 300) -> str:
        """Start the configured VM (nogui by default) and wait for VMware Tools."""
        args = ["start", cfg.vmx, "nogui" if headless else "gui"]
        res = vmrun.run(args, timeout=timeout, auth=False)
        if res.rc != 0:
            return f"[ERROR] start failed (rc={res.rc}): {res.err.strip() or res.out.strip()}"
        last = ""
        for _ in range(40):
            t = vmrun.run(["checkToolsState", cfg.vmx], timeout=15, auth=False)
            last = t.out.strip()
            if "installed" in last and "running" in last:
                return f"Started (headless={headless}). Tools: {last}"
            time.sleep(5)
        return f"Started but VMware Tools not yet running: {last}"

    @mcp.tool()
    @safe
    def vm_stop(mode: str = "soft", timeout: int = 120) -> str:
        """Stop the VM. mode = soft (guest shutdown) | hard (power off)."""
        if mode not in ("soft", "hard"):
            return "[ERROR] mode must be 'soft' or 'hard'"
        res = vmrun.run(
            ["stop", cfg.vmx, "hard" if mode == "hard" else "soft"], timeout=timeout, auth=False
        )
        return ok(f"stop({mode}) rc={res.rc}: {res.err.strip() or res.out.strip()}")

    @mcp.tool()
    @safe
    def vm_reset() -> str:
        """Hard-reset the VM (equivalent to the reset button)."""
        res = vmrun.run(["reset", cfg.vmx], timeout=120, auth=False)
        return ok(f"reset rc={res.rc}: {res.err.strip() or res.out.strip()}")

    @mcp.tool()
    @safe
    def vm_suspend() -> str:
        """Suspend the VM to disk (stateful pause)."""
        res = vmrun.run(["suspend", cfg.vmx], timeout=120, auth=False)
        return ok(f"suspend rc={res.rc}: {res.err.strip() or res.out.strip()}")

    @mcp.tool()
    @safe
    def vm_pause() -> str:
        """Pause VM execution (in-memory freeze). Use vm_unpause to resume."""
        res = vmrun.run(["pause", cfg.vmx], timeout=60, auth=False)
        return ok(f"pause rc={res.rc}: {res.err.strip() or res.out.strip()}")

    @mcp.tool()
    @safe
    def vm_unpause() -> str:
        """Resume a paused VM."""
        res = vmrun.run(["unpause", cfg.vmx], timeout=60, auth=False)
        return ok(f"unpause rc={res.rc}: {res.err.strip() or res.out.strip()}")

    @mcp.tool()
    @safe
    def vm_wait_tools(timeout: int = 300, poll_interval: int = 5) -> str:
        """Wait until VMware Tools reports installed + running.

        Useful as a standalone primitive after ``vm_start`` (v1.0: previously
        only embedded inside ``vm_start``).
        """
        cycles = max(timeout // max(poll_interval, 1), 1)
        last = ""
        for _ in range(cycles):
            t = vmrun.run(["checkToolsState", cfg.vmx], timeout=15, auth=False)
            last = t.out.strip()
            if "installed" in last and "running" in last:
                return f"Tools ready: {last}"
            time.sleep(poll_interval)
        return f"Tools not ready after {timeout}s: {last or 'no data'}"
