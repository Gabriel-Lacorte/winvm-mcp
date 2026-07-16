"""SSH-based guest tools: one-shot cmd and interactive PowerShell.

Prefer these over ``guest_run_script`` when you need full stdout/stderr or
pipelines. Output streams are kept separate and the exit code comes from the
SSH channel (not an echoed ``%errorlevel%``).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from . import safe

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP

    from . import ServerContext


def register(mcp: FastMCP, ctx: ServerContext) -> None:
    ssh = ctx.ssh

    @mcp.tool()
    @safe
    def ssh_exec_cmd(command: str, timeout: int = 120) -> str:
        """Run a single shell command on the guest over SSH and return stdout+stderr+rc.

        The command runs through cmd (the OpenSSH default shell on Windows), so
        use Windows cmd syntax.
        """
        res = ssh.exec(command, timeout=timeout)
        out = res.out.strip()
        if res.err:
            out += f"\n[stderr] {res.err.strip()}"
        return f"[rc={res.rc}]\n{out}"

    @mcp.tool()
    @safe
    def ssh_powershell(script: str, timeout: int = 180) -> str:
        """Run a PowerShell snippet on the guest over SSH and return its output.

        Example:
          ssh_powershell('Get-CimInstance Win32_Service | Select Name,State,StartName')
        """
        res = ssh.powershell(script, timeout=timeout)
        out = res.out.strip()
        if res.err:
            out += f"\n[stderr] {res.err.strip()}"
        return f"[rc={res.rc}]\n{out}"
