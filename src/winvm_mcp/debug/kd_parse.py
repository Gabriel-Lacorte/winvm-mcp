"""Pure parsers for ``cdb``/``kd`` debugger output.

Every function here is pure (``str`` → ``str`` / ``bool``) so it can be
unit-tested without a live debugger session. The
:class:`~winvm_mcp.debug.kd_engine.KDEngine` delegates all fragile text
handling to this module.
"""

from __future__ import annotations

import re

# cdb/kd prompts appear in several forms, all matched by one shape:
#   "kd>"      plain
#   "lkd>"     livekd
#   "0: kd>"   indexed by current processor
#   "3: lkd>"  indexed livekd
_HEAD = r"(?:\d+:\s*)?"  # optional "N: " processor index
_BODY = r"l?kd>"

_ANSI_RE = re.compile(r"\x1b\[[0-9;]*[a-zA-Z]|\x1b\][^\x07]*\x07?")
PROMPT_LINE_RE = re.compile(rf"^{_HEAD}{_BODY}\s*$")
PROMPT_PREFIX_RE = re.compile(rf"^{_HEAD}{_BODY}\s*")
PROMPT_TAIL_RE = re.compile(rf"\b{_HEAD}{_BODY}\s*$")


def strip_ansi(text: str) -> str:
    """Remove CSI / OSC ANSI escape sequences."""
    return _ANSI_RE.sub("", text)


def looks_like_prompt(line: str) -> bool:
    """True if the whole (stripped) line is a debugger prompt."""
    return bool(PROMPT_LINE_RE.match(line.strip()))


def has_trailing_prompt(text: str) -> bool:
    """True if the buffer ends with a debugger prompt (after rstrip)."""
    return bool(PROMPT_TAIL_RE.search(text.rstrip()))


def strip_trailing_prompt(text: str) -> str:
    """Drop trailing prompt lines (``0: kd>`` / ``lkd>`` / ``kd>``)."""
    lines = text.splitlines()
    while lines and looks_like_prompt(lines[-1]):
        lines.pop()
    return "\n".join(lines)


def strip_command_echo(text: str, command: str) -> str:
    """Remove the echoed command from the start of the output.

    The PTY echoes the typed command, usually right after the prompt
    (``"0: kd> kb"``) or on its own (``"kb"``). We strip a leading prompt
    from the first non-empty line, then drop that line iff it equals the
    command. Unlike the old ``lstrip("0:l")`` heuristic this never mangles
    real output (e.g. a value line beginning ``0xffff...``).
    """
    lines = text.splitlines()
    while lines and not lines[0].strip():
        lines.pop(0)
    if not lines:
        return ""
    cmd = command.strip()
    if not cmd:
        return "\n".join(lines).rstrip()
    first = PROMPT_PREFIX_RE.sub("", lines[0], count=1).strip()
    if first == cmd:
        lines = lines[1:]
    return "\n".join(lines)


def clean_command_output(output: str, command: str) -> str:
    """Full cleanup pipeline: ANSI → echo → trailing prompt → trim."""
    text = strip_ansi(output)
    text = strip_command_echo(text, command)
    text = strip_trailing_prompt(text)
    return text.strip()
