"""Kernel-debugging tools — thin, well-documented wrappers over cdb commands.

Two flavours:

* session management — ``kd_connect`` / ``kd_command`` / ``kd_disconnect`` /
  ``kd_status`` / ``kd_run_batch``
* primitives — memory, disassembly, type/symbol, registers/stack/breakpoints,
  kernel objects, system tables, expression evaluation

All require an active session (call ``kd_connect`` first) unless noted.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..debug import kd_parse
from . import safe, tool_error

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP

    from . import ServerContext


def register(mcp: FastMCP, ctx: ServerContext) -> None:
    kd = ctx.kd

    # ------------------------------------------------------------------ #
    # Session management
    # ------------------------------------------------------------------ #

    @mcp.tool()
    @safe
    def kd_connect(target: str = "livekd", timeout: int = 120) -> str:
        """Open a kernel-debug session against the guest.

        target:
          * 'livekd'  -> livekd.exe wrapping cdb (recommended; no reboot, full kernel)
          * 'live'    -> cdb.exe -k (requires the guest booted in debug/test mode)
          * 'dump:<path-to-.dmp>' -> analyse a saved crash/hibernation dump

        Returns the debugger banner. State persists until kd_disconnect.
        """
        banner = kd.connect(target=target, timeout=timeout)
        if not kd_parse.has_trailing_prompt(banner):
            return (
                "Connected, but no prompt seen yet (the engine may still be "
                "loading). Banner so far:\n" + banner
            )
        return f"[connected: {target}]\n{banner}"

    @mcp.tool()
    @safe
    def kd_command(command: str, timeout: int = 60) -> str:
        """Run one cdb/kd debugger command in the active session and return its output.

        Examples: '!process 0 0', 'lmvm nt', 'bp nt!NtCreateFile', 'g', 'kb', '!pte'.
        """
        if not kd.connected:
            return tool_error("No active kd session. Call kd_connect first.")
        return kd.command(command, timeout=timeout)

    @mcp.tool()
    @safe
    def kd_disconnect() -> str:
        """Close the active kernel-debug session."""
        if not kd.connected:
            return "(no active session)"
        kd.disconnect()
        return "disconnected"

    @mcp.tool()
    @safe
    def kd_status() -> str:
        """Report whether a kernel-debug session is active and what target it holds."""
        if not kd.connected:
            return "No active kd session."
        return f"Active session, target='{kd.target}'. Use kd_command to drive it."

    @mcp.tool()
    @safe
    def kd_run_batch(commands: list[str], timeout: int = 120) -> str:
        """Run a sequence of debugger commands in order; return combined output.

        Useful for scripted analysis, e.g. ['~', 'kb', 'kv', '.trap', 'q'].
        """
        if not kd.connected:
            return tool_error("No active kd session. Call kd_connect first.")
        return kd.run_batch(commands, timeout=timeout)

    # ------------------------------------------------------------------ #
    # Memory inspection
    # ------------------------------------------------------------------ #

    @mcp.tool()
    @safe
    def kd_memory_read(address: str, size: str = "L40", fmt: str = "db") -> str:
        """Read memory at an address and format it.

        Args:
          address: Virtual address or symbol (e.g. '0xfffff805' or 'nt!PsActiveProcessHead').
          size:    How many entries/bytes. Use 'L40' (40 entries) or 'L100' etc.
          fmt:     db(bytes) dw(words) dd(dwords) dq(qwords) dc(chars) dp(pointer-sized)
                   dD(dwords-double) du(unicode) da(ascii-str) dds(sym-dwords) dps(sym-qwords).
        """
        return kd.command(f"{fmt} {address} {size}")

    @mcp.tool()
    @safe
    def kd_memory_search(
        range_start: str, range_end_or_size: str, pattern: str, fmt: str = "b"
    ) -> str:
        """Search memory for a byte/dword/qword pattern.

        Args:
          range_start: Start address (or symbol).
          range_end_or_size: End address (e.g. '0xfffff81000000') or 'L?200' for size.
          pattern: Pattern to find (e.g. '00 50 56 ff' for bytes, '0x12345678' for dwords).
          fmt: b=bytes w=words d=dwords q=qwords.
        """
        return kd.command(f"s -{fmt} {range_start} {range_end_or_size} {pattern}")

    @mcp.tool()
    @safe
    def kd_disasm(address: str, count: int = 20) -> str:
        """Disassemble instructions at an address or symbol.

        Args:
          address: Address or symbol (e.g. 'nt!NtCreateFile', '0xfffff8051234').
          count:   Number of instructions to disassemble.
        """
        return kd.command(f"u {address} L{count}")

    @mcp.tool()
    @safe
    def kd_disasm_function(symbol: str) -> str:
        """Disassemble an entire function by name (uses 'uf').

        Args:
          symbol: Function name (e.g. 'nt!NtQueryInformationProcess', 'MyDriver!DispatchIoctl').
        """
        return kd.command(f"uf {symbol}")

    @mcp.tool()
    @safe
    def kd_dump_type(type_name: str, address: str = "", fields: str = "") -> str:
        """Dump a structure type (dt) — show layout, or dump live at an address.

        Args:
          type_name: e.g. '_EPROCESS', '_KTHREAD', '_POOL_HEADER', '_DRIVER_OBJECT'.
          address:   Optional address to dump the struct live.
          fields:    Optional field filter (e.g. 'ImageFileName Token').
        """
        parts = ["dt", type_name]
        if address:
            parts.append(address)
        if fields:
            parts.append(fields)
        return kd.command(" ".join(parts))

    @mcp.tool()
    @safe
    def kd_symbols(pattern: str) -> str:
        """Resolve / search symbols (x command).

        Args:
          pattern: Glob pattern (e.g. 'nt!*CreateProcess*', 'MyDriver!*').
        """
        return kd.command(f"x {pattern}")

    @mcp.tool()
    @safe
    def kd_what_is(address: str) -> str:
        """Identify what's at/near an address: nearest symbol, module, ln lookup."""
        return kd.command(f"ln {address}")

    # ------------------------------------------------------------------ #
    # Debugging state
    # ------------------------------------------------------------------ #

    @mcp.tool()
    @safe
    def kd_registers() -> str:
        """Dump all registers (r)."""
        return kd.command("r")

    @mcp.tool()
    @safe
    def kd_stack(depth: int = 12, fmt: str = "kb") -> str:
        """Get the current thread's call stack.

        Args:
          depth: Number of frames.
          fmt:   kb(base+args) kv(FPO+args) kn(frame-numbers) kh(handled)
                 kc(no-args) kf(FPO) kP(source-with-params).
        """
        return kd.command(f"{fmt} {depth}")

    @mcp.tool()
    @safe
    def kd_stack_thread(tid_or_ptr: str, depth: int = 20) -> str:
        """Dump the stack of a specific thread.

        Args:
          tid_or_ptr: Thread TID (e.g. '0n1234') or KTHREAD pointer (e.g. '0xffffa01').
                      Pass the raw identifier; the context switch is applied for you.
          depth:      Frame count.
        """
        return kd.run_batch([f".thread /r {tid_or_ptr}", f"kb {depth}"])

    @mcp.tool()
    @safe
    def kd_breakpoint_set(symbol_or_addr: str, condition: str = "", one_shot: bool = False) -> str:
        """Set a breakpoint.

        Args:
          symbol_or_addr: e.g. 'nt!NtCreateFile+0x45', 'MyDriver!IoctlHandler'.
          condition: Optional MASM predicate (e.g. '.if @@(poi(@rcx) == 0x1234)').
          one_shot: If True, the breakpoint removes itself after the first hit ('bp /1').
        """
        bp = "bp /1" if one_shot else "bp"
        cmd = f"{bp} {symbol_or_addr}"
        if condition:
            cmd += f' "{condition}"'
        return kd.command(cmd)

    @mcp.tool()
    @safe
    def kd_breakpoint_list() -> str:
        """List all breakpoints (bl)."""
        return kd.command("bl")

    @mcp.tool()
    @safe
    def kd_breakpoint_clear(ids: str = "") -> str:
        """Clear breakpoints. ids='*' for all, or '1', '2 3', etc."""
        return kd.command(f"bc {ids or '*'}")

    @mcp.tool()
    @safe
    def kd_go() -> str:
        """Continue execution (g). Returns when the debugger breaks again."""
        return kd.command("g", timeout=120)

    @mcp.tool()
    @safe
    def kd_step(count: int = 1, mode: str = "t") -> str:
        """Single-step the debugger.

        Args:
          count: Instructions to step.
          mode:  t=trace-into, p=step-over.
        """
        return kd.command(f"{mode} {count}")

    # ------------------------------------------------------------------ #
    # Kernel object inspection
    # ------------------------------------------------------------------ #

    @mcp.tool()
    @safe
    def kd_processes_detailed() -> str:
        """Dump the full process list with EPROCESS addresses, PIDs, tokens (!process 0 0)."""
        return kd.command("!process 0 0")

    @mcp.tool()
    @safe
    def kd_process_detail(process: str) -> str:
        """Dump detailed info for one process (!process <ptr|pid|name> 7).

        Args:
          process: EPROCESS pointer, PID (e.g. '0n1234'), or name pattern (e.g. 'cmd.exe').
        """
        return kd.command(f"!process {process} 7")

    @mcp.tool()
    @safe
    def kd_threads(process: str = "0", flags: int = 2) -> str:
        """List threads of a process (!process <proc> <flags>).

        Args:
          process: EPROCESS ptr / PID / name. '0' = all processes.
          flags:   0=basic, 1=+stacks, 2=+handles, 7=everything.
        """
        return kd.command(f"!process {process} {flags}")

    @mcp.tool()
    @safe
    def kd_token(process_or_ptr: str) -> str:
        """Dump the security token of a process: privileges, groups, user SID.

        Args:
          process_or_ptr: EPROCESS ptr or PID (e.g. '0n4' for System).

        Switches the debugger into the target process context (via
        ``!process <X> 0``), then runs ``!token`` so the dumped token belongs
        to that process (not whatever thread happened to be current).
        """
        return kd.run_batch([f"!process {process_or_ptr} 0", "!token"])

    @mcp.tool()
    @safe
    def kd_handles(process: str, filter_str: str = "") -> str:
        """Dump the handle table of a process.

        Args:
          process: EPROCESS ptr, PID, or name.
          filter_str: Optional filter, e.g. 'Key' or 'mutant' (passed to !handle).
        """
        handle_cmd = f"!handle 0 f {filter_str}" if filter_str else "!handle 0 ff"
        return kd.run_batch([f"!process {process} 0", handle_cmd])

    @mcp.tool()
    @safe
    def kd_drivers() -> str:
        """List all loaded kernel drivers with base address, size, and path (lm t n)."""
        return kd.command("lm t n")

    @mcp.tool()
    @safe
    def kd_driver_detail(driver_name: str) -> str:
        """Detailed info about a loaded driver: base, size, timestamp, symbols (lmvm).

        Args:
          driver_name: Module name (e.g. 'nt', 'MyDriver', 'tcpip').
        """
        return kd.command(f"lmvm {driver_name}")

    @mcp.tool()
    @safe
    def kd_pte(virtual_addr: str) -> str:
        """Walk the page table for a virtual address (!pte).

        Shows PML4E -> PDPTE -> PDE -> PTE chain and the resulting physical page.
        Essential for exploit dev (check NX, Write, Present bits).
        """
        return kd.command(f"!pte {virtual_addr}")

    @mcp.tool()
    @safe
    def kd_pool_scan(tag: str, pool_type: str = "nonpaged") -> str:
        """Scan pool allocations for a specific 4-byte tag (!poolused).

        Args:
          tag:      4-char pool tag (e.g. 'Proc', 'Thre', 'File').
          pool_type: 'nonpaged' or 'paged'.
        """
        pt = "0" if pool_type == "nonpaged" else "1"
        return kd.command(f"!poolused {pt} {tag}")

    @mcp.tool()
    @safe
    def kd_pool_info(address: str) -> str:
        """Inspect the pool header at an address (!pool <addr>).

        Shows tag, size, type, allocation — essential for pool corruption analysis.
        """
        return kd.command(f"!pool {address}")

    @mcp.tool()
    @safe
    def kd_pool_ranges() -> str:
        """Show pool allocation ranges (!poolused 2). Useful to understand heap layout."""
        return kd.command("!poolused 2")

    # ------------------------------------------------------------------ #
    # System tables, callbacks, object manager
    # ------------------------------------------------------------------ #

    @mcp.tool()
    @safe
    def kd_callbacks() -> str:
        """Enumerate registered kernel callback / notification routines.

        Shows PsSetCreateProcessNotifyRoutine, PsSetLoadImageNotifyRoutine,
        PsSetCreateThreadNotifyRoutine, CmRegisterCallback, ObRegisterCallbacks,
        and similar — useful to find security product hooks / detection points.
        """
        return kd.run_batch(["x nt!*NotifyRoutine*", "x nt!*Callback*", "!devnode 0 1"])

    @mcp.tool()
    @safe
    def kd_object_directory(path: str = "\\") -> str:
        """Dump the Windows object manager namespace (!object <path>).

        Args:
          path: Object directory (e.g. '\\\\', '\\\\Device', '\\\\Driver', '\\\\BaseNamedObjects').
        """
        return kd.command(f"!object {path}")

    @mcp.tool()
    @safe
    def kd_device_objects(driver_name: str = "") -> str:
        """List DEVICE_OBJECTs and their DriverObject back-references.

        Args:
          driver_name: If given, dump the DRIVER_OBJECT + dispatch table (!drvobj <name> 7).
                       If empty, list all devices (!devnode 0 1).
        """
        if driver_name:
            return kd.command(f"!drvobj {driver_name} 7")
        return kd.command("!devnode 0 1")

    @mcp.tool()
    @safe
    def kd_system_info() -> str:
        """One-shot system overview: build, version, uptime, processors, PRCB."""
        return kd.run_batch(["vertest", "!cpuid", "r kv", "!running -t"])

    # ------------------------------------------------------------------ #
    # Expression evaluation
    # ------------------------------------------------------------------ #

    @mcp.tool()
    @safe
    def kd_eval(expression: str) -> str:
        """Evaluate a MASM expression and return the result (?).

        Use for pointer arithmetic, struct offset calculation, type sizes, etc.
        Examples: '? sizeof(_EPROCESS)', '? nt!PsActiveProcessHead', '? 0xfffff805 + 0x100'.
        """
        return kd.command(f"? {expression}")

    @mcp.tool()
    @safe
    def kd_list_entry(head: str, offset: str, max_entries: int = 50) -> str:
        """Walk a doubly-linked LIST_ENTRY chain (!list).

        Essential for enumerating _EPROCESS.ActiveProcessLinks, timer lists, etc.

        Args:
          head:   Address of the LIST_ENTRY head (e.g. 'nt!PsActiveProcessHead').
          offset: Offset of the LIST_ENTRY within the parent struct,
                  or a full expression like 'poi(nt!_EPROCESS+0x2f0)'.
          max_entries: Maximum entries to dump.
        """
        return kd.command(f"!list -t {head} -x dps @$extret -l {offset} {max_entries}")
