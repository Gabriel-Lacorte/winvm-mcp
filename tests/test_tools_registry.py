"""Registry smoke tests: every expected tool is registered exactly once.

The ``EXPECTED`` set is an intentional snapshot — adding, renaming, or removing
a tool requires updating it here, which forces a conscious decision and keeps
the tool surface auditable.
"""

from __future__ import annotations

import asyncio

from winvm_mcp.server import build_server

# 79 tools (the original 78 + vm_wait_tools added in v1.0).
EXPECTED: set[str] = {
    # vm / lifecycle
    "vm_state",
    "vm_start",
    "vm_stop",
    "vm_reset",
    "vm_suspend",
    "vm_pause",
    "vm_unpause",
    "vm_wait_tools",
    # snapshots
    "snapshot_list",
    "snapshot_create",
    "snapshot_revert",
    "snapshot_delete",
    # guest (vmrun)
    "guest_exec",
    "guest_run_script",
    "guest_list_processes",
    "guest_capture_screen",
    "guest_copy_to",
    "guest_copy_from",
    "guest_list_dir",
    "guest_file_exists",
    "guest_create_dir",
    "guest_delete_path",
    # ssh
    "ssh_exec_cmd",
    "ssh_powershell",
    # kd — session
    "kd_connect",
    "kd_command",
    "kd_disconnect",
    "kd_status",
    "kd_run_batch",
    # kd — memory
    "kd_memory_read",
    "kd_memory_search",
    "kd_disasm",
    "kd_disasm_function",
    "kd_dump_type",
    "kd_symbols",
    "kd_what_is",
    # kd — state
    "kd_registers",
    "kd_stack",
    "kd_stack_thread",
    "kd_breakpoint_set",
    "kd_breakpoint_list",
    "kd_breakpoint_clear",
    "kd_go",
    "kd_step",
    # kd — objects
    "kd_processes_detailed",
    "kd_process_detail",
    "kd_threads",
    "kd_token",
    "kd_handles",
    "kd_drivers",
    "kd_driver_detail",
    "kd_pte",
    "kd_pool_scan",
    "kd_pool_info",
    "kd_pool_ranges",
    # kd — system tables
    "kd_callbacks",
    "kd_object_directory",
    "kd_device_objects",
    "kd_system_info",
    # kd — expr
    "kd_eval",
    "kd_list_entry",
    # analyze
    "analyze_state",
    "analyze_dump_overview",
    "analyze_dump_full",
    "analyze_dump_bugcheck",
    "analyze_dump_threads",
    "analyze_dump_pool",
    "analyze_dump_modules",
    "analyze_minidump",
    "analyze_live_processes",
    "analyze_live_processes_detailed",
    "analyze_live_drivers",
    "analyze_live_system",
    # vuln
    "vuln_dump_overview",
    "vuln_ioctl_dispatch",
    "vuln_token_compare",
    "vuln_pool_corruption",
    "vuln_check_exploit_success",
    "vuln_callback_hunt",
}


def test_all_expected_tools_registered(vm_config) -> None:  # type: ignore[no-untyped-def]
    tools = asyncio.run(build_server(vm_config).list_tools())
    names = {t.name for t in tools}
    missing = EXPECTED - names
    extra = names - EXPECTED
    assert not missing, f"missing tools: {sorted(missing)}"
    assert not extra, f"unexpected extra tools: {sorted(extra)}"


def test_no_duplicate_tools(vm_config) -> None:  # type: ignore[no-untyped-def]
    tools = asyncio.run(build_server(vm_config).list_tools())
    names = [t.name for t in tools]
    assert len(names) == len(set(names))


def test_every_tool_has_description_and_schema(vm_config) -> None:  # type: ignore[no-untyped-def]
    tools = asyncio.run(build_server(vm_config).list_tools())
    for t in tools:
        assert (t.description or "").strip(), f"{t.name} has no description"
        assert isinstance(t.inputSchema, dict), f"{t.name} has no object inputSchema"
        assert t.inputSchema.get("type") == "object", f"{t.name} schema is not an object"
