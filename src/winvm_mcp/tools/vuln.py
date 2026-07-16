"""Vulnerability-research compositions built on the kd_* primitives.

* ``vuln_dump_overview`` / ``vuln_check_exploit_success`` open their own
  transient session.
* ``vuln_ioctl_dispatch`` / ``vuln_token_compare`` /
  ``vuln_pool_corruption`` / ``vuln_callback_hunt`` require an active
  ``kd_connect`` session so state (e.g. a live exploit) persists.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from . import run_transient, safe, tool_error

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP

    from . import ServerContext


def register(mcp: FastMCP, ctx: ServerContext) -> None:
    kd = ctx.kd

    @mcp.tool()
    @safe
    def vuln_dump_overview(dump_path: str) -> str:
        """Vulnerability-focused dump triage: bugcheck + corruption + pool + faulting code.

        Combines !analyze with pool corruption checks, Special Pool detection
        (if Driver Verifier was active), and disassembly of the crash site.
        """
        return run_transient(
            kd,
            f"dump:{dump_path}",
            [
                ".bugcheck /no",
                "!analyze -v",
                ".ecxr",
                "kb 30",
                "ub @rip L20",
                "u @rip L20",
                "!pool @rdx",
                "!pool @rcx",
                "!verifier",
                "q",
            ],
            connect_timeout=240,
            run_timeout=240,
        )

    @mcp.tool()
    @safe
    def vuln_ioctl_dispatch(driver_name: str) -> str:
        """Find and dump a driver's IRP_MJ_DEVICE_CONTROL dispatch routine.

        Locates the DRIVER_OBJECT, extracts MajorFunction[IRP_MJ_DEVICE_CONTROL],
        disassembles the handler — the #1 target for kernel LPE research.

        Requires an active kd session (kd_connect first).
        """
        if not kd.connected:
            return tool_error("No active kd session. Call kd_connect first.")
        # IRP_MJ_DEVICE_CONTROL = 0xe, MajorFunction array index = 0xe
        return kd.run_batch(
            [
                f"!drvobj {driver_name} 7",
                "? @@c++(((nt!_DRIVER_OBJECT*)0)->MajorFunction[0xe])",
                "? sizeof(nt!_DRIVER_OBJECT)",
                "q",
            ]
        )

    @mcp.tool()
    @safe
    def vuln_token_compare(pid_a: str, pid_b: str) -> str:
        """Compare the security tokens of two processes — essential for proving LPE.

        For each process: switch into its context (``!process <pid> 0``) then
        dump its token (``!token``). If the target (e.g. winlogon / System) has
        been corrupted or cloned, the comparison makes the proof obvious.

        Requires an active kd session.
        """
        if not kd.connected:
            return tool_error("No active kd session. Call kd_connect first.")
        return kd.run_batch(
            [
                f"!process {pid_a} 0",
                "!token",
                f"!process {pid_b} 0",
                "!token",
            ]
        )

    @mcp.tool()
    @safe
    def vuln_pool_corruption(address: str, scan_size: int = 0x200) -> str:
        """Deep pool corruption analysis around an address.

        Dumps pool header, surrounding allocations, checks for overflow/underflow
        patterns, and verifies the allocation size vs header size.

        Requires an active kd session.
        """
        if not kd.connected:
            return tool_error("No active kd session. Call kd_connect first.")
        half = hex(scan_size // 2)
        length = f"L{scan_size:x}"
        return kd.run_batch(
            [
                f"!pool {address}",
                f"db {address}-{half} {length}",
                f"!pool {address}-{half}",
                f"!pool {address}+{half}",
            ]
        )

    @mcp.tool()
    @safe
    def vuln_check_exploit_success(target_pid: str = "0n592") -> str:
        """Verify whether a privilege-escalation exploit succeeded.

        Dumps the token of a high-privilege target process (default: winlogon.exe)
        and compares integrity level + privileges. Call this AFTER running a PoC.

        Args:
          target_pid: PID of the high-privilege process to inspect.
                      Default 0n592 is a common winlogon.exe PID (verify first).
        """
        return run_transient(
            kd,
            "livekd",
            [f"!process {target_pid} 0", "!token", "q"],
            connect_timeout=120,
            run_timeout=120,
        )

    @mcp.tool()
    @safe
    def vuln_callback_hunt() -> str:
        """Enumerate ALL security-relevant kernel callbacks and notify routines.

        Finds:
          - PsSetCreateProcessNotifyRoutine(Ex) callbacks
          - PsSetLoadImageNotifyRoutine callbacks
          - PsSetCreateThreadNotifyRoutine callbacks
          - CmRegisterCallback (registry filter) callbacks
          - ObRegisterCallbacks (object filter) callbacks

        Use this to identify EDR/AV hooks that may block exploitation, or to
        find unbacked callback addresses (potential injection).

        Requires an active kd session.
        """
        if not kd.connected:
            return tool_error("No active kd session. Call kd_connect first.")
        return kd.run_batch(
            [
                "x nt!Psp*NotifyEnableMask",
                "x nt!*CreateProcessNotifyRoutine*",
                "x nt!*LoadImageNotifyRoutine*",
                "x nt!*CreateThreadNotifyRoutine*",
                "x nt!*CallbackListHead*",
                "x nt!*CallbackRegistration*",
                "!object \\Callback",
                "dps nt!PspCreateProcessNotifyRoutine L40",
                "dps nt!PspLoadImageNotifyRoutine L40",
                "dps nt!PspCreateThreadNotifyRoutine L40",
            ]
        )
