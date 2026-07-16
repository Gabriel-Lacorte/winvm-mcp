"""Configuration for winvm-mcp.

Resolved from a single TOML file and validated up front. ``load_config`` is
pure (no module-level singleton), so importing :mod:`winvm_mcp` works even
when no config file is present — the caller (``server.build_server``) loads
it explicitly.
"""

from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, get_args

from .errors import ConfigError

# Two meaningful policies:
#   "auto_add"    — accept and remember any host key (convenient; MITM risk).
#   "known_hosts" — load ~/.ssh/known_hosts and reject unknown hosts (safe).
HostKeyPolicy = Literal["auto_add", "known_hosts"]
_VALID_POLICIES: tuple[str, ...] = get_args(HostKeyPolicy)

_PKG_DIR = Path(__file__).resolve().parent
# src/winvm_mcp -> src -> <repo root>
_DEFAULT_PATH = _PKG_DIR.parent.parent / "config.toml"


def default_config_path() -> Path:
    """Config path from ``$WINVM_MCP_CONFIG``, else ``config.toml`` at the repo root."""
    env = os.environ.get("WINVM_MCP_CONFIG")
    if env:
        return Path(env).expanduser()
    return _DEFAULT_PATH


@dataclass(frozen=True)
class VMConfig:
    """Resolved configuration for a single Windows VM."""

    vmx: str
    username: str
    password: str
    ssh_host: str = ""
    ssh_port: int = 22
    ssh_username: str = ""
    ssh_password: str = ""
    # "auto_add" (default) accepts any host key; "known_hosts" rejects unknown.
    ssh_host_key_policy: HostKeyPolicy = "auto_add"
    # Path to cdb.exe / kd.exe inside the guest (Debugging Tools for Windows).
    debugger_path: str = r"C:\Program Files (x86)\Windows Kits\10\Debuggers\x64\cdb.exe"
    # Default place for transferred files / dumps inside the guest.
    guest_workdir: str = r"C:\winvm-mcp"
    # vmrun binary on the host.
    vmrun: str = "/usr/bin/vmrun"
    # Leave blank on plain Workstation; some installs need "-T ws".
    vmrun_type: str = ""


def load_config(path: Path | None = None) -> VMConfig:
    """Load and validate configuration from a TOML file.

    Raises :class:`~winvm_mcp.errors.ConfigError` if the file is missing,
    unreadable, or fails validation.
    """
    resolved = path or default_config_path()
    if not resolved.exists():
        raise ConfigError(
            f"winvm-mcp config not found at {resolved}. Copy config.example.toml "
            f"to config.toml and fill in your VM details."
        )
    try:
        with resolved.open("rb") as fh:
            data = tomllib.load(fh)
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise ConfigError(f"Could not read config {resolved}: {exc}") from exc

    vm = data.get("vm")
    if not isinstance(vm, dict):
        raise ConfigError("Config file must contain a [vm] table.")

    missing = [k for k in ("vmx", "username", "password") if k not in vm]
    if missing:
        raise ConfigError(f"[vm] is missing required key(s): {', '.join(missing)}.")

    policy = vm.get("ssh_host_key_policy", "auto_add")
    if policy not in _VALID_POLICIES:
        raise ConfigError(f"ssh_host_key_policy must be one of {_VALID_POLICIES}, got {policy!r}.")

    try:
        port = int(vm.get("ssh_port", 22))
    except (TypeError, ValueError) as exc:
        raise ConfigError(f"ssh_port must be an integer, got {vm.get('ssh_port')!r}.") from exc
    if not (0 < port < 65536):
        raise ConfigError(f"ssh_port must be in 1..65535, got {port}.")

    return VMConfig(
        vmx=str(vm["vmx"]),
        username=str(vm["username"]),
        password=str(vm["password"]),
        ssh_host=str(vm.get("ssh_host", "")),
        ssh_port=port,
        ssh_username=str(vm.get("ssh_username", vm["username"])),
        ssh_password=str(vm.get("ssh_password", vm["password"])),
        ssh_host_key_policy=policy,
        debugger_path=str(vm.get("debugger_path", VMConfig.debugger_path)),
        guest_workdir=str(vm.get("guest_workdir", VMConfig.guest_workdir)),
        vmrun=str(vm.get("vmrun", VMConfig.vmrun)),
        vmrun_type=str(vm.get("vmrun_type", "")),
    )
