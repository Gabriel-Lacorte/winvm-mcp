"""Higher-level analysis workflows that compose the kd_* primitives.

Two shapes:

* ``analyze_dump_*``  — open a crash/hibernation/minidump, run a curated
  command-set, close (transient session).
* ``analyze_live_*``   — open a transient livekd session, snapshot some aspect
  of the running kernel, close.

``analyze_state`` is VM-side (no KD) and is a good first call before any
deeper work.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from . import run_transient, safe

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP

    from . import ServerContext


def register(mcp: FastMCP, ctx: ServerContext) -> None:
    cfg = ctx.cfg
    vmrun = ctx.vmrun
    kd = ctx.kd

    @mcp.tool()
    @safe
    def analyze_state() -> str:
        """One-shot summary: VM state, snapshot list, tools state. Call before digging in."""
        res = vmrun.run(["list"], timeout=15, auth=False)
        running = res.out.strip().splitlines()
        is_up = any(cfg.vmx in line for line in running)
        tools_res = vmrun.run(["checkToolsState", cfg.vmx], timeout=30, auth=False)
        snap_res = vmrun.run(["listSnapshots", cfg.vmx], timeout=60, auth=False)
        return "\n\n".join(
            [
                "== VM & Tools ==",
                f"VM running: {is_up}\nTools state: {tools_res.out.strip() or 'unknown'}",
                "\n== Snapshots ==",
                snap_res.out.strip() or "(no snapshots)",
            ]
        )

    # ------------------------------------------------------------------ #
    # Dump / minidump triage
    # ------------------------------------------------------------------ #

    @mcp.tool()
    @safe
    def analyze_dump_overview(dump_path: str) -> str:
        """Open a crash dump and run the standard triage set; consolidated bug-check analysis.

        Closes the session when done.
        """
        return run_transient(
            kd,
            f"dump:{dump_path}",
            ["!analyze -v", "lmvm nt", "kb", ".bugcheck", "q"],
            connect_timeout=180,
            run_timeout=180,
        )

    @mcp.tool()
    @safe
    def analyze_dump_full(dump_path: str) -> str:
        """Open a crash/hibernation/minidump and run a FULL multi-section triage.

        Returns: bugcheck analysis, faulting module, faulting thread stack,
        all thread stacks, pool state, loaded modules with timestamps.
        Closes the session when done.
        """
        return run_transient(
            kd,
            f"dump:{dump_path}",
            [
                ".bugcheck /no",
                "!analyze -v",
                "lmvm nt",
                ".ecxr",
                "kb 30",
                "~* kb 20",
                "!poolused 2",
                "lm t n",
                "q",
            ],
            connect_timeout=240,
            run_timeout=180,
        )

    @mcp.tool()
    @safe
    def analyze_dump_bugcheck(dump_path: str) -> str:
        """Quick bugcheck extraction from a dump. Returns code + parameters decoded."""
        return run_transient(
            kd,
            f"dump:{dump_path}",
            [".bugcheck /no", "!analyze -v", "q"],
            connect_timeout=120,
            run_timeout=120,
        )

    @mcp.tool()
    @safe
    def analyze_dump_threads(dump_path: str, depth: int = 25) -> str:
        """Enumerate all threads in a dump with their call stacks.

        Identifies the faulting thread (.ecxr) first, then dumps every thread.
        Closes the session when done.
        """
        return run_transient(
            kd,
            f"dump:{dump_path}",
            [".ecxr", f"kb {depth}", f"~* kb {depth}", "q"],
            connect_timeout=180,
            run_timeout=180,
        )

    @mcp.tool()
    @safe
    def analyze_dump_pool(dump_path: str, tag: str = "") -> str:
        """Analyze pool state in a crash dump — corruption detection + tag usage.

        If a tag is given, shows all allocations for that tag.

        Args:
          dump_path: Path to the .dmp file.
          tag: Optional 4-char pool tag to focus on (e.g. 'Proc', 'Toke').
        """
        cmds = ["!poolused 2", "!verifier"]
        if tag:
            cmds.insert(0, f"!poolused 0 {tag}")
        cmds.append("q")
        return run_transient(kd, f"dump:{dump_path}", cmds, connect_timeout=180, run_timeout=180)

    @mcp.tool()
    @safe
    def analyze_dump_modules(dump_path: str, find_module: str = "") -> str:
        """Dump the loaded module list from a crash dump with versions + timestamps.

        Useful to spot unsigned/unusual modules or version mismatches.

        Args:
          dump_path: Path to the .dmp file.
          find_module: If given, dump detailed info for just that module (lmvm).
        """
        cmds = [f"lmvm {find_module}", "lm t n", "q"] if find_module else ["lm t n", "lm t m", "q"]
        return run_transient(kd, f"dump:{dump_path}", cmds, connect_timeout=120, run_timeout=120)

    @mcp.tool()
    @safe
    def analyze_minidump(dump_path: str) -> str:
        """Specialised minidump analysis: exception record, faulting thread, modules, memory.

        Minidumps (typically in C:\\\\Windows\\\\Minidump\\\\*.dmp) are small crash dumps.
        This extracts maximum information from the limited data available.
        """
        return run_transient(
            kd,
            f"dump:{dump_path}",
            [
                ".bugcheck /no",
                "!analyze -v",
                ".ecxr",  # exception context record
                "r",
                "kb 25",
                "~",
                "lm t n",
                "!dh f -f",
                "q",
            ],
            connect_timeout=120,
            run_timeout=180,
        )

    # ------------------------------------------------------------------ #
    # Live kernel (transient livekd sessions)
    # ------------------------------------------------------------------ #

    @mcp.tool()
    @safe
    def analyze_live_processes() -> str:
        """Quick live view of processes from kernel context.

        Opens a transient livekd session, dumps the process list, and closes it.
        """
        return run_transient(
            kd, "livekd", ["!process 0 0", "q"], connect_timeout=120, run_timeout=180
        )

    @mcp.tool()
    @safe
    def analyze_live_processes_detailed() -> str:
        """Full process tree from the live kernel: EPROCESS addresses, PIDs, tokens, threads."""
        return run_transient(
            kd, "livekd", ["!process 0 7", "q"], connect_timeout=120, run_timeout=180
        )

    @mcp.tool()
    @safe
    def analyze_live_drivers() -> str:
        """List all loaded drivers from the live kernel with base addresses and sizes."""
        return run_transient(
            kd, "livekd", ["lm t n", "!devnode 0 1", "q"], connect_timeout=120, run_timeout=120
        )

    @mcp.tool()
    @safe
    def analyze_live_system() -> str:
        """Comprehensive live snapshot: version, build, CPU, CRx, modules, callbacks, namespace."""
        return run_transient(
            kd,
            "livekd",
            [
                "vertest",
                "!cpuid",
                "r kv",
                "lm t n",
                "x nt!*NotifyRoutine*",
                "!object \\",
                "q",
            ],
            connect_timeout=120,
            run_timeout=180,
        )
