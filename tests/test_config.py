"""Tests for config loading & validation (no VM required)."""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from winvm_mcp import config
from winvm_mcp.config import load_config
from winvm_mcp.errors import ConfigError


def _write(tmp_path: Path, body: str) -> Path:
    p = tmp_path / "config.toml"
    p.write_text(textwrap.dedent(body))
    return p


def test_loads_full_config(tmp_path: Path) -> None:
    p = _write(
        tmp_path,
        """
        [vm]
        vmx = "/x/w.vmx"
        username = "researcher"
        password = "secret"
        ssh_host = "1.2.3.4"
        ssh_port = 2222
        ssh_host_key_policy = "known_hosts"
        """,
    )
    cfg = load_config(p)
    assert cfg.vmx == "/x/w.vmx"
    assert cfg.ssh_port == 2222
    assert cfg.ssh_username == "researcher"  # defaults from username
    assert cfg.ssh_password == "secret"  # defaults from password
    assert cfg.ssh_host_key_policy == "known_hosts"


def test_defaults_applied(tmp_path: Path) -> None:
    p = _write(
        tmp_path,
        """
        [vm]
        vmx = "/x/w.vmx"
        username = "u"
        password = "p"
        """,
    )
    cfg = load_config(p)
    assert cfg.ssh_port == 22
    assert cfg.ssh_host_key_policy == "auto_add"
    assert cfg.vmrun.endswith("vmrun")
    assert cfg.debugger_path.endswith("cdb.exe")


def test_missing_file(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="not found"):
        load_config(tmp_path / "nope.toml")


def test_missing_required_key(tmp_path: Path) -> None:
    p = _write(
        tmp_path,
        """
        [vm]
        vmx = "/x/w.vmx"
        username = "researcher"
        """,
    )
    with pytest.raises(ConfigError, match="password"):
        load_config(p)


def test_missing_vm_table(tmp_path: Path) -> None:
    p = _write(tmp_path, '[other]\nkey = "value"\n')
    with pytest.raises(ConfigError, match=r"\[vm\]"):
        load_config(p)


def test_bad_policy(tmp_path: Path) -> None:
    p = _write(
        tmp_path,
        """
        [vm]
        vmx = "/x/w.vmx"
        username = "u"
        password = "p"
        ssh_host_key_policy = "yes"
        """,
    )
    with pytest.raises(ConfigError, match="ssh_host_key_policy"):
        load_config(p)


def test_bad_port(tmp_path: Path) -> None:
    p = _write(
        tmp_path,
        """
        [vm]
        vmx = "/x/w.vmx"
        username = "u"
        password = "p"
        ssh_port = 99999
        """,
    )
    with pytest.raises(ConfigError, match="ssh_port"):
        load_config(p)


def test_env_override(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    p = _write(
        tmp_path,
        """
        [vm]
        vmx = "/env.vmx"
        username = "u"
        password = "p"
        """,
    )
    monkeypatch.setenv("WINVM_MCP_CONFIG", str(p))
    cfg = load_config()  # no explicit path -> honors env
    assert cfg.vmx == "/env.vmx"


def test_malformed_toml(tmp_path: Path) -> None:
    p = tmp_path / "config.toml"
    p.write_text("this is = = not toml [[[")
    with pytest.raises(ConfigError, match="Could not read"):
        load_config(p)


# Silence "imported but unused" for the module reference kept for clarity.
_ = config
