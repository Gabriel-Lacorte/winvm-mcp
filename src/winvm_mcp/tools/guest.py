"""Guest interaction via vmrun (VMware Tools): exec, files, screen, processes."""

from __future__ import annotations

import time
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
    def guest_exec(
        program_path: str, args: str = "", no_wait: bool = False, timeout: int = 180
    ) -> str:
        """Run a program in the guest and (by default) wait for it to exit.

        program_path must be an absolute Windows path to an .exe.
        """
        cmd = ["runProgramInGuest", cfg.vmx]
        if no_wait:
            cmd.append("-noWait")
        cmd.append(program_path)
        if args:
            cmd.append(args)
        res = vmrun.run(cmd, timeout=timeout)
        return ok(f"rc={res.rc}: {res.err.strip() or res.out.strip()}")

    @mcp.tool()
    @safe
    def guest_run_script(interpreter: str, script_body: str, timeout: int = 180) -> str:
        """Run a script in the guest via an interpreter.

        Typical usage:
          interpreter = r'C:\\Windows\\System32\\WindowsPowerShell\\v1.0\\powershell.exe'
          script_body = '-Command "Get-Process | Select-Object -First 5"'
        Or for cmd: interpreter = 'cmd.exe', script_body = '/c dir C:\\\\'
        """
        res = vmrun.run(["runScriptInGuest", cfg.vmx, interpreter, script_body], timeout=timeout)
        return ok(f"rc={res.rc}: {res.err.strip() or res.out.strip()}")

    @mcp.tool()
    @safe
    def guest_list_processes() -> str:
        """List running processes in the guest (PID + name + owner)."""
        res = vmrun.run(["listProcessesInGuest", cfg.vmx], timeout=60)
        if res.rc != 0:
            return tool_error(f"listProcesses rc={res.rc}: {res.err.strip()}")
        return res.out.strip()

    @mcp.tool()
    @safe
    def guest_capture_screen(host_path: str = "") -> str:
        """Capture the guest screen to a PNG on the host and return its path."""
        if not host_path:
            host_path = f"/tmp/winvm-screen-{int(time.time())}.png"
        res = vmrun.run(["captureScreen", cfg.vmx, host_path], timeout=60)
        if res.rc != 0:
            return tool_error(f"captureScreen rc={res.rc}: {res.err.strip()}")
        return f"Saved screenshot to {host_path}"

    @mcp.tool()
    @safe
    def guest_copy_to(host_path: str, guest_path: str) -> str:
        """Copy a file from the host into the guest."""
        res = vmrun.run(["CopyFileFromHostToGuest", cfg.vmx, host_path, guest_path], timeout=300)
        return ok(f"copy host->guest rc={res.rc}: {res.err.strip() or res.out.strip()}")

    @mcp.tool()
    @safe
    def guest_copy_from(guest_path: str, host_path: str) -> str:
        """Copy a file out of the guest to the host."""
        res = vmrun.run(["CopyFileFromGuestToHost", cfg.vmx, guest_path, host_path], timeout=300)
        return ok(f"copy guest->host rc={res.rc}: {res.err.strip() or res.out.strip()}")

    @mcp.tool()
    @safe
    def guest_list_dir(guest_path: str) -> str:
        """List the contents of a directory in the guest."""
        res = vmrun.run(["listDirectoryInGuest", cfg.vmx, guest_path], timeout=60)
        if res.rc != 0:
            return tool_error(f"listDirectory rc={res.rc}: {res.err.strip()}")
        return res.out.strip()

    @mcp.tool()
    @safe
    def guest_file_exists(guest_path: str) -> str:
        """Return whether a file exists in the guest."""
        res = vmrun.run(["fileExistsInGuest", cfg.vmx, guest_path], timeout=30)
        return f"{guest_path}: {'EXISTS' if res.rc == 0 else 'MISSING'}"

    @mcp.tool()
    @safe
    def guest_create_dir(guest_path: str) -> str:
        """Create a directory in the guest (creates parents)."""
        res = vmrun.run(["createDirectoryInGuest", cfg.vmx, guest_path], timeout=60)
        return ok(f"mkdir rc={res.rc}: {res.err.strip() or res.out.strip()}")

    @mcp.tool()
    @safe
    def guest_delete_path(guest_path: str, recurse: bool = True) -> str:
        """Delete a file or directory in the guest."""
        op = "deleteDirectoryInGuest" if recurse else "deleteFileInGuest"
        res = vmrun.run([op, cfg.vmx, guest_path], timeout=60)
        return ok(f"delete rc={res.rc}: {res.err.strip() or res.out.strip()}")
