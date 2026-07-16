# Changelog

All notable changes to this project are documented here.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [1.0.0] — 2026-07-16

First packaged release. The project is restructured from a single-file
`server.py` research tool into a `src/`-layout Python package with tests,
typing, and documentation. Behavior is preserved unless noted below.

### Added

- **Package layout** (`src/winvm_mcp/`): `config`, `errors`, `log`,
  `transports/{vmrun,ssh}`, `debug/{kd_parse,kd_engine}`, `tools/*`, `server`.
- **Lazy configuration + dependency injection.** No import-time config load;
  `import winvm_mcp` works without a config file. `build_server(cfg)` takes the
  config as an argument.
- **Typed errors** (`WinvmError` → `ConfigError`/`VmrunError`/`SshError`/`KdError`/`KdNotConnectedError`),
  mapped to `[ERROR] …` tool results by `tools.safe`.
- **Pure kd-output parsers** (`debug/kd_parse.py`), unit-tested without a VM.
- **New tool**: `vm_wait_tools` — wait for VMware Tools as a standalone
  primitive (previously only embedded in `vm_start`).
- **Configurable SSH host-key policy** (`[vm] ssh_host_key_policy`):
  `auto_add` (default) or `known_hosts`.
- **`VmrunClient` auth flag** — host-level commands (`list`/`start`/`snapshot`)
  no longer send guest credentials.
- **CLI**: `winvm-mcp --version` / `--config`; `python -m winvm_mcp`.
- **Guest bootstrap**: `30-livekd-launcher.ps1` provisions the `kd-livekd.bat`
  launcher the server expects.
- **Tests**: config validation, kd parsers, vmrun argv, ssh encoding, kd engine
  (with fakes), tool-registry snapshot, stdio handshake. Integration marker for
  VM-requiring tests.
- **Tooling**: ruff (lint+format), mypy --strict, pytest.
- **Docs (English)**: README, ARCHITECTURE, THREAT-MODEL, SETUP-WINDOWS-VM,
  TOOL-REFERENCE, CONTRIBUTING, SECURITY, CODE_OF_CONDUCT. MIT license.

### Changed — bug fixes

These change observable behavior; verify any scripted workflows against the new
output.

- **`ssh_exec_cmd` / `ssh_powershell` exit code** — the rc now comes from the
  SSH channel (`recv_exit_status`) and stderr is a separate stream. The previous
  `cmd /c "… 2>&1 & echo __RC__%errorlevel%"` expanded `%errorlevel%` at parse
  time (unreliable rc) and merged stderr into stdout.
- **`analyze_minidump`** — uses `.ecxr` (exception context record). The previous
  `.excr` is not a valid debugger command.
- **`kd_token` / `kd_handles` / `vuln_token_compare`** — now switch into the
  target process context (`!process <X> 0`) before running `!token` / `!handle`,
  so the dumped token/handles belong to the requested process rather than
  whichever thread happened to be current. `vuln_token_compare` is now symmetric
  across both PIDs.
- **`kd_breakpoint_set`** — defaults to a normal `bp`; the previous code always
  emitted a one-shot `bp /1`. An explicit `one_shot: bool = False` parameter
  restores one-shot behavior on demand.
- **`kd_stack_thread`** — takes a raw TID/KTHREAD pointer and builds the
  `.thread /r <x>` context switch internally (the previous API doubled the
  prefix if the caller already supplied `.thread /r …`).
- **kd output cleanup** — echo/prompt stripping no longer uses the
  `lstrip("0:l")` heuristic, which could mangle value lines starting with `0`
  (e.g. `0xffff…`).

### Removed

- The legacy monolithic `server.py` (replaced by the `winvm_mcp` package).
- `requirements.txt` (dependencies now declared in `pyproject.toml`; install
  via `pip install -e .` or `uv`).
- The `tomli` dependency (Python ≥ 3.11 uses stdlib `tomllib`).

### Migration notes

Tool surface is otherwise unchanged — all original tool names and signatures are
preserved except where a bug fix required a new parameter. Update your MCP
client config from the old `server.py` path to the `winvm-mcp` entry point (or
`python -m winvm_mcp`); everything else (config keys, tool names) is compatible.
