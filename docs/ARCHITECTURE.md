# Architecture

This document describes the internal structure of `winvm-mcp` and the rationale
behind the central design choices. For the threat model, see
[`THREAT-MODEL.md`](THREAT-MODEL.md); for tool behavior, see
[`TOOL-REFERENCE.md`](TOOL-REFERENCE.md).

## The one decision that shapes everything

> **The debugger runs inside the guest, driven over SSH.**

There is no WinDbg-on-Linux dependency. `livekd.exe`/`cdb.exe` execute inside the
Windows VM; the host controls them by writing commands to a PTY-backed SSH
channel and reading output until the `kd>` prompt re-appears. This works on any
Linux distro with `openssh-client`, removes the need for the native KD UDP
transport, and lets a single persistent session hold breakpoints and state
across many commands.

## Layers

```
src/winvm_mcp/
├── config.py          VMConfig (frozen dataclass) + load_config (lazy, validated)
├── errors.py          WinvmError hierarchy
├── log.py             stderr-only structured logging
├── transports/
│   ├── vmrun.py       VmrunClient  — subprocess argv builder + runner
│   └── ssh.py         SshClient    — one-shot exec/powershell + PTY session
├── debug/
│   ├── kd_parse.py    PURE parsers: strip ANSI, echo, trailing prompt
│   └── kd_engine.py   KDEngine     — persistent cdb session over the PTY
├── tools/             one module per domain; each exposes register(mcp, ctx)
│   ├── vm.py snapshot.py guest.py shell.py kd.py analyze.py vuln.py
│   └── __init__.py    ServerContext, safe(), run_transient(), register_all()
└── server.py          build_server(cfg) -> FastMCP; main() (argparse + stdio)
```

### Dependency direction

`server` → `tools` → `{transports, debug}` → `{config, errors, log}`. Nothing
imports `server`, so the package can be imported without a config file present
and exercised in tests.

## Configuration & dependency injection

There is **no module-level singleton**. `load_config()` is a pure function;
`build_server(cfg)` constructs the three clients once, wraps them in a
`ServerContext`, and passes it to `tools.register_all`, which calls each tool
module's `register(mcp, ctx)`. Tools are defined inside `register` and close
over the context, so the FastMCP `@mcp.tool()` decorator captures fully-bound
functions.

```python
ctx = ServerContext(cfg=cfg, vmrun=VmrunClient(cfg),
                    ssh=SshClient(cfg), kd=KDEngine(SshClient(cfg), cfg))
register_all(mcp, ctx)
```

Because nothing touches the VM at import or registration time, `initialize` /
`tools/list` work with no VM present — connections are opened lazily on the first
tool call that needs them.

## Error handling

`errors.py` defines a small hierarchy rooted at `WinvmError`:

```
WinvmError
├── ConfigError
├── VmrunError
├── SshError
└── KdError
    └── KdNotConnectedError
```

Tool functions are wrapped by `tools.safe`, which maps any `WinvmError` to a
plain `[ERROR] …` string result. The LLM always receives text content; the MCP
transport never crashes on a failed guest operation.

## Pure parsers (`debug/kd_parse.py`)

All fragile debugger-output handling — ANSI stripping, removing the echoed
command, removing the trailing prompt — lives in pure `str → str` functions:

- `strip_ansi`, `looks_like_prompt`, `has_trailing_prompt`
- `strip_trailing_prompt`, `strip_command_echo`, `clean_command_output`

These are unit-tested with captured samples of real `cdb` output and do **not**
depend on a live session. The engine's `_drain` uses `has_trailing_prompt` to
know when a command has finished producing output; `command()` runs
`clean_command_output` before returning.

The echo-stripper is deliberately strict: it strips a leading prompt from the
first line and drops that line **only if** it exactly equals the issued command.
This replaces an earlier `lstrip("0:l")` heuristic that could mangle real output
(for example a value line beginning `0xffff…`).

## The KD session

`KDEngine` keeps one SSH client + one PTY channel open for the life of a
session. Three connect targets:

| target | command run in the guest |
|---|---|
| `live` | `"<debugger_path>" -k` |
| `livekd` | `"<guest_workdir>\kd-livekd.bat"` (provisioned by `guest-bootstrap/30-livekd-launcher.ps1`) |
| `dump:<path>` | `"<debugger_path>" -z "<path>"` |

The launcher `.bat` exists so the path-quoting of `livekd.exe -k "…\cdb.exe"`
stays local to the guest; the host only launches one well-known file. To send a
command, the engine flushes stray bytes, writes the command terminated with
`\r` (a Windows PTY expects carriage return), then drains until the prompt.

`analyze_*` and `vuln_*` tools that need a self-contained session use
`tools.run_transient(kd, target, commands, …)`, which opens, batches, and always
closes — even on error.

## Transports

### `VmrunClient`

A pure argv builder (`build_argv(args, auth=...)`) plus an injectable runner
(default: `subprocess.run`). Host-level commands (`list`, `start`, `snapshot`,
…) pass `auth=False` and omit the `-gu`/`-gp` guest credentials;
`*InGuest` commands pass `auth=True`.

### `SshClient`

- `exec(command)` runs one command and returns `SshResult(rc, out, err)` where
  `rc` comes from `channel.recv_exit_status()` and `out`/`err` are read from the
  **separate** streams paramiko provides. (An earlier implementation echoed
  `%errorlevel%` into stdout, which expanded at parse time and gave an unreliable
  code while merging stderr into stdout.)
- `powershell(script)` runs a snippet via `powershell -EncodedCommand <b64>`,
  where the base64 is the script encoded UTF-16-LE — sidestepping quoting across
  SSH → cmd → PowerShell.
- `open_pty_session(command)` returns `(client, channel)` for the KD engine.

Host-key verification is configurable: `auto_add` (default, convenient) or
`known_hosts` (loads `~/.ssh/known_hosts`, rejects unknown hosts).

## Packaging, typing, tests

- **src layout**, hatchling backend, `[project.scripts] winvm-mcp`.
- **ruff** for lint + format; **mypy --strict** over `src/`.
- **pytest**: pure unit tests (config, kd_parse, vmrun argv, ssh encoding, kd
  engine with fakes), a registry snapshot test (exact set of tool names), and a
  stdio handshake test. VM-requiring tests are marked `integration`.
- **Build**: `python -m build` produces the wheel + sdist.
