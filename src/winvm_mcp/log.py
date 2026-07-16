"""Structured stderr logging.

stdout is reserved for the JSON-RPC MCP transport, so every handler writes to
**stderr**. Verbosity is controlled by ``$WINVM_MCP_LOG`` (one of
``DEBUG``/``INFO``/``WARNING``/``ERROR``; default ``WARNING``).
"""

from __future__ import annotations

import logging
import os
import sys

_NAMESPACE = "winvm"


def _build_root_logger() -> logging.Logger:
    logger = logging.getLogger(_NAMESPACE)
    level_name = os.environ.get("WINVM_MCP_LOG", "WARNING").upper()
    logger.setLevel(getattr(logging, level_name, logging.WARNING))
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)-7s %(name)s: %(message)s"))
        logger.addHandler(handler)
    # Never propagate to root (some hosts attach a stdout handler there).
    logger.propagate = False
    return logger


_root = _build_root_logger()


def get_logger(name: str | None = None) -> logging.Logger:
    """Return a logger under the ``winvm`` namespace (stderr only)."""
    return _root.getChild(name) if name else _root
