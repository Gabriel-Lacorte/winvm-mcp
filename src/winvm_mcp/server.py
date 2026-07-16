"""MCP server assembly: build a FastMCP server from a :class:`~winvm_mcp.config.VMConfig`.

The server is constructed lazily from configuration (no import-time side
effects), so importing :mod:`winvm_mcp` works without a config file present.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from . import __version__
from .config import VMConfig, default_config_path, load_config
from .debug.kd_engine import KDEngine
from .log import get_logger
from .tools import ServerContext, register_all
from .transports.ssh import SshClient
from .transports.vmrun import VmrunClient

__all__ = ["build_server", "main"]

_log = get_logger("server")


def build_server(cfg: VMConfig) -> FastMCP:
    """Construct the FastMCP server with every tool registered against ``cfg``."""
    mcp = FastMCP("winvm-mcp")
    ctx = ServerContext(
        cfg=cfg,
        vmrun=VmrunClient(cfg),
        ssh=SshClient(cfg),
        kd=KDEngine(SshClient(cfg), cfg),
    )
    register_all(mcp, ctx)
    return mcp


def main(argv: list[str] | None = None) -> None:
    """CLI entry point: parse flags, load config, run the stdio MCP server."""
    parser = argparse.ArgumentParser(
        prog="winvm-mcp",
        description="MCP server driving a VMware Windows VM for security research.",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=None,
        help="Path to config.toml (default: $WINVM_MCP_CONFIG or ./config.toml).",
    )
    parser.add_argument("--version", action="version", version=f"winvm-mcp {__version__}")
    args = parser.parse_args(argv)

    cfg_path = args.config or default_config_path()
    try:
        cfg = load_config(cfg_path)
    except Exception as exc:  # ConfigError or anything unexpected
        print(f"winvm-mcp: config error: {exc}", file=sys.stderr)
        sys.exit(2)

    mcp = build_server(cfg)
    _log.info("winvm-mcp %s starting (stdio transport)", __version__)
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
