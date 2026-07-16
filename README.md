# winvm-mcp

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![mypy](https://img.shields.io/badge/types-mypy-blue.svg)](http://mypy-lang.org/)

An [MCP](https://modelcontextprotocol.io) server that gives an LLM full control
over a **VMware-hosted Windows VM**: lifecycle, snapshots, remote execution
(SSH + vmrun), file transfer, and **kernel debugging** (`cdb.exe` / `livekd`),
all driven from a Linux host over stdio.

Built for offensive and defensive security research on a self-owned lab VM:
hunt and prove high-impact vulnerabilities (kernel, drivers, LPE) with full
reproducibility through snapshots.

---

## Why

A researcher's loop, *identify a target statically -> stand it up in a VM -> set
breakpoints -> fire a PoC -> capture the crash or the corrupted state -> write it
up*, has a lot of tedious context-switching between tools. This MCP collapses
that loop into a single conversation: the model drives the VM, the debugger, and
the guest shell directly, and consolidates the evidence.

The core architectural choice is that **the debugger runs inside the guest** over
SSH (via `livekd`/`cdb.exe`), so there is no WinDbg-on-Linux dependency and it
works on any host distro.

---

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for the layered design and
[`docs/THREAT-MODEL.md`](docs/THREAT-MODEL.md) for the security posture.

---

## Install

The server needs Python ≥ 3.11 on the Linux host, plus `vmrun` (VMware Workstation/Player). Pick one:

```bash
# uv (recommended)
uv tool install winvm-mcp            # or, from source: uv pip install -e .

# pipx
pipx install winvm-mcp

# plain pip
pip install winvm-mcp
```

To run from a checkout instead:

```bash
git clone https://github.com/winvm-mcp/winvm-mcp.git
cd winvm-mcp

uv venv --python 3.13 .venv
uv pip install --python .venv/bin/python -e ".[dev]"
```

Then configure (see below) and point your MCP client at the executable. The
installed entry point is `winvm-mcp`; it reads its config from the file in
`$WINVM_MCP_CONFIG` (default: `config.toml` beside the checkout).

---

## Configure

```bash
cp config.example.toml config.toml
$EDITOR config.toml   # vmx path, guest credentials, ssh_host, debugger_path
```

The Windows guest must be set up once. See
[`docs/SETUP-WINDOWS-VM.md`](docs/SETUP-WINDOWS-VM.md) for the full walkthrough
(ISO, network, `.vmx` tuning, and the `guest-bootstrap/` PowerShell scripts that
provision OpenSSH, kernel-debugging, complete dumps, and the `livekd` launcher).

Sanity-check the server loads your config and registers its tools:

```bash
winvm-mcp --version
WINVM_MCP_CONFIG=./config.toml winvm-mcp   # then Ctrl-C; it should not error
```

---

## Register with an MCP client

### Generic (stdio)

```json
{
  "mcpServers": {
    "winvm": {
      "command": "winvm-mcp",
      "env": { "WINVM_MCP_CONFIG": "/absolute/path/to/config.toml" }
    }
  }
}
```

### Claude Code / Cursor / Crush / etc.

Use the generic snippet above in your client's MCP config. For a checkout-based
install, point `command` at the venv Python and `args` at `-m winvm_mcp`:

```json
{
  "mcpServers": {
    "winvm": {
      "command": "/path/to/winvm-mcp/.venv/bin/python",
      "args": ["-m", "winvm_mcp"],
      "env": { "WINVM_MCP_CONFIG": "/path/to/winvm-mcp/config.toml" }
    }
  }
}
```

---

## Tools

**79 tools** across seven groups. Full reference:
[`docs/TOOL-REFERENCE.md`](docs/TOOL-REFERENCE.md).

| Group | Count | Examples |
|---|---:|---|
| VM lifecycle | 8 | `vm_state` `vm_start` `vm_wait_tools` `vm_snapshot` |
| Snapshots | 4 | `snapshot_list` `snapshot_create` `snapshot_revert` |
| Guest (vmrun) | 10 | `guest_exec` `guest_copy_to` `guest_capture_screen` |
| Guest (SSH) | 2 | `ssh_exec_cmd` `ssh_powershell` |
| Kernel debugging | ~35 | `kd_connect` `kd_command` `kd_memory_read` `kd_disasm` `kd_token` |
| Analysis workflows | 12 | `analyze_dump_overview` `analyze_live_system` |
| Vulnerability research | 6 | `vuln_ioctl_dispatch` `vuln_token_compare` `vuln_callback_hunt` |

---

## Threat model

This server is **RCE + kernel-memory-access by design**, intended to run on a
researcher's host against a VM they own. **Keep the transport local (stdio) and
the VM on an isolated network (NAT / host-only). Never expose the MCP transport
to a network.** Full posture and mitigations in
[`docs/THREAT-MODEL.md`](docs/THREAT-MODEL.md).

---

## Development

```bash
uv pip install -e ".[dev]"          # or: pip install -e ".[dev]"
pytest -q                           # unit + handshake tests, no VM required
ruff check src tests && ruff format --check src tests
mypy src
python -m build                     # produce wheel + sdist
```

Integration tests that need a live VM are marked `@pytest.mark.integration` and
run only when `WINVM_INTEGRATION=1` is set.

---

## License

[MIT](LICENSE). No warranties. Use against systems and networks you own or are
authorized to test.
