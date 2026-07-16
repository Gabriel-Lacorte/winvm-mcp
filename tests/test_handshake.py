"""End-to-end stdio handshake: initialize + tools/list (no VM required).

Replaces the old manual ``tests/handshake.py`` script.
"""

from __future__ import annotations

import contextlib
import json
import os
import select
import subprocess
import sys
import time

import pytest

_PROTO = "2024-11-05"


def _read_jsonl(proc: subprocess.Popen, timeout: float = 15.0):
    deadline = time.time() + timeout
    buf = b""
    while time.time() < deadline:
        ready, _, _ = select.select([proc.stdout], [], [], 0.2)
        if not ready:
            continue
        assert proc.stdout is not None
        ch = proc.stdout.read(1)
        if not ch:
            break
        buf += ch
        if ch == b"\n":
            line = buf.decode("utf-8", "replace").strip()
            buf = b""
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                continue
    if buf:
        with contextlib.suppress(json.JSONDecodeError):
            yield json.loads(buf.decode("utf-8", "replace"))


def _send(proc: subprocess.Popen, obj: dict) -> None:
    assert proc.stdin is not None
    proc.stdin.write((json.dumps(obj) + "\n").encode())
    proc.stdin.flush()


@pytest.mark.timeout(45)
def test_stdio_handshake(tmp_path) -> None:  # type: ignore[no-untyped-def]
    cfg = tmp_path / "config.toml"
    cfg.write_text(
        '[vm]\nvmx = "/x/w.vmx"\nusername = "u"\npassword = "p"\nssh_host = "127.0.0.1"\n'
    )
    env = dict(os.environ)
    env["WINVM_MCP_CONFIG"] = str(cfg)
    env["PYTHONUNBUFFERED"] = "1"

    proc = subprocess.Popen(
        [sys.executable, "-m", "winvm_mcp"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        bufsize=0,
        env=env,
    )
    try:
        _send(
            proc,
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": _PROTO,
                    "capabilities": {},
                    "clientInfo": {"name": "selftest", "version": "0"},
                },
            },
        )
        init = next((m for m in _read_jsonl(proc, 20.0) if m.get("id") == 1), None)
        assert init is not None, "no initialize reply"
        assert init["result"]["serverInfo"]["name"] == "winvm-mcp"

        _send(proc, {"jsonrpc": "2.0", "method": "notifications/initialized"})
        _send(proc, {"jsonrpc": "2.0", "id": 2, "method": "tools/list"})

        listed = next((m for m in _read_jsonl(proc, 20.0) if m.get("id") == 2), None)
        assert listed is not None, "no tools/list reply"
        tools = listed["result"]["tools"]
        assert len(tools) >= 78, f"expected >=78 tools, got {len(tools)}"
    finally:
        if proc.stdin is not None:
            proc.stdin.close()
        try:
            proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            proc.terminate()
