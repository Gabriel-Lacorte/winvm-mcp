"""Shared pytest fixtures."""

from __future__ import annotations

import pytest

from winvm_mcp.config import VMConfig


@pytest.fixture
def vm_config() -> VMConfig:
    """A throwaway in-memory config (no file, no VM)."""
    return VMConfig(
        vmx="/x/w.vmx",
        username="researcher",
        password="secret",
        ssh_host="127.0.0.1",
        ssh_username="researcher",
        ssh_password="secret",
    )
