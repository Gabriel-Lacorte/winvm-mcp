# Tool Reference

Auto-generated from the registered MCP tools (`winvm_mcp.server.build_server`).
**79 tools** in total.

Every tool returns a string. Errors are returned as `[ERROR] …` text, not raised.


## VM lifecycle

| Tool | Description |
|---|---|
| `vm_pause` | Pause VM execution (in-memory freeze). Use vm_unpause to resume. |
| `vm_reset` | Hard-reset the VM (equivalent to the reset button). |
| `vm_start` | Start the configured VM (nogui by default) and wait for VMware Tools. |
| `vm_state` | Report whether the configured VM is running, and list all running VMs on this host. |
| `vm_stop` | Stop the VM. mode = soft (guest shutdown) \| hard (power off). |
| `vm_suspend` | Suspend the VM to disk (stateful pause). |
| `vm_unpause` | Resume a paused VM. |
| `vm_wait_tools` | Wait until VMware Tools reports installed + running. |

## Snapshots

| Tool | Description |
|---|---|
| `snapshot_create` | Create a new snapshot. Names should be short and unique (e.g. 'clean-w10', 'poc-triggered'). |
| `snapshot_delete` | Delete a snapshot (frees disk; cannot be undone). |
| `snapshot_list` | List all snapshots of the configured VM. |
| `snapshot_revert` | Revert the VM to a previously-created snapshot (discards current state). |

## Guest — vmrun (VMware Tools)

| Tool | Description |
|---|---|
| `guest_capture_screen` | Capture the guest screen to a PNG on the host and return its path. |
| `guest_copy_from` | Copy a file out of the guest to the host. |
| `guest_copy_to` | Copy a file from the host into the guest. |
| `guest_create_dir` | Create a directory in the guest (creates parents). |
| `guest_delete_path` | Delete a file or directory in the guest. |
| `guest_exec` | Run a program in the guest and (by default) wait for it to exit. |
| `guest_file_exists` | Return whether a file exists in the guest. |
| `guest_list_dir` | List the contents of a directory in the guest. |
| `guest_list_processes` | List running processes in the guest (PID + name + owner). |
| `guest_run_script` | Run a script in the guest via an interpreter. |

## Guest — SSH

| Tool | Description |
|---|---|
| `ssh_exec_cmd` | Run a single shell command on the guest over SSH and return stdout+stderr+rc. |
| `ssh_powershell` | Run a PowerShell snippet on the guest over SSH and return its output. |

## Kernel debugging (kd_*)

| Tool | Description |
|---|---|
| `kd_breakpoint_clear` | Clear breakpoints. ids='*' for all, or '1', '2 3', etc. |
| `kd_breakpoint_list` | List all breakpoints (bl). |
| `kd_breakpoint_set` | Set a breakpoint. |
| `kd_callbacks` | Enumerate registered kernel callback / notification routines. |
| `kd_command` | Run one cdb/kd debugger command in the active session and return its output. |
| `kd_connect` | Open a kernel-debug session against the guest. |
| `kd_device_objects` | List DEVICE_OBJECTs and their DriverObject back-references. |
| `kd_disasm` | Disassemble instructions at an address or symbol. |
| `kd_disasm_function` | Disassemble an entire function by name (uses 'uf'). |
| `kd_disconnect` | Close the active kernel-debug session. |
| `kd_driver_detail` | Detailed info about a loaded driver: base, size, timestamp, symbols (lmvm). |
| `kd_drivers` | List all loaded kernel drivers with base address, size, and path (lm t n). |
| `kd_dump_type` | Dump a structure type (dt) — show layout, or dump live at an address. |
| `kd_eval` | Evaluate a MASM expression and return the result (?). |
| `kd_go` | Continue execution (g). Returns when the debugger breaks again. |
| `kd_handles` | Dump the handle table of a process. |
| `kd_list_entry` | Walk a doubly-linked LIST_ENTRY chain (!list). |
| `kd_memory_read` | Read memory at an address and format it. |
| `kd_memory_search` | Search memory for a byte/dword/qword pattern. |
| `kd_object_directory` | Dump the Windows object manager namespace (!object <path>). |
| `kd_pool_info` | Inspect the pool header at an address (!pool <addr>). |
| `kd_pool_ranges` | Show pool allocation ranges (!poolused 2). Useful to understand heap layout. |
| `kd_pool_scan` | Scan pool allocations for a specific 4-byte tag (!poolused). |
| `kd_process_detail` | Dump detailed info for one process (!process <ptr\|pid\|name> 7). |
| `kd_processes_detailed` | Dump the full process list with EPROCESS addresses, PIDs, tokens (!process 0 0). |
| `kd_pte` | Walk the page table for a virtual address (!pte). |
| `kd_registers` | Dump all registers (r). |
| `kd_run_batch` | Run a sequence of debugger commands in order; return combined output. |
| `kd_stack` | Get the current thread's call stack. |
| `kd_stack_thread` | Dump the stack of a specific thread. |
| `kd_status` | Report whether a kernel-debug session is active and what target it holds. |
| `kd_step` | Single-step the debugger. |
| `kd_symbols` | Resolve / search symbols (x command). |
| `kd_system_info` | One-shot system overview: build, version, uptime, processors, PRCB. |
| `kd_threads` | List threads of a process (!process <proc> <flags>). |
| `kd_token` | Dump the security token of a process: privileges, groups, user SID. |
| `kd_what_is` | Identify what's at/near an address: nearest symbol, module, ln lookup. |

## Analysis workflows (analyze_*)

| Tool | Description |
|---|---|
| `analyze_dump_bugcheck` | Quick bugcheck extraction from a dump. Returns code + parameters decoded. |
| `analyze_dump_full` | Open a crash/hibernation/minidump and run a FULL multi-section triage. |
| `analyze_dump_modules` | Dump the loaded module list from a crash dump with versions + timestamps. |
| `analyze_dump_overview` | Open a crash dump and run the standard triage set; consolidated bug-check analysis. |
| `analyze_dump_pool` | Analyze pool state in a crash dump — corruption detection + tag usage. |
| `analyze_dump_threads` | Enumerate all threads in a dump with their call stacks. |
| `analyze_live_drivers` | List all loaded drivers from the live kernel with base addresses and sizes. |
| `analyze_live_processes` | Quick live view of processes from kernel context. |
| `analyze_live_processes_detailed` | Full process tree from the live kernel: EPROCESS addresses, PIDs, tokens, threads. |
| `analyze_live_system` | Comprehensive live snapshot: version, build, CPU, CRx, modules, callbacks, namespace. |
| `analyze_minidump` | Specialised minidump analysis: exception record, faulting thread, modules, memory. |
| `analyze_state` | One-shot summary: VM state, snapshot list, tools state. Call before digging in. |

## Vulnerability research (vuln_*)

| Tool | Description |
|---|---|
| `vuln_callback_hunt` | Enumerate ALL security-relevant kernel callbacks and notify routines. |
| `vuln_check_exploit_success` | Verify whether a privilege-escalation exploit succeeded. |
| `vuln_dump_overview` | Vulnerability-focused dump triage: bugcheck + corruption + pool + faulting code. |
| `vuln_ioctl_dispatch` | Find and dump a driver's IRP_MJ_DEVICE_CONTROL dispatch routine. |
| `vuln_pool_corruption` | Deep pool corruption analysis around an address. |
| `vuln_token_compare` | Compare the security tokens of two processes — essential for proving LPE. |
