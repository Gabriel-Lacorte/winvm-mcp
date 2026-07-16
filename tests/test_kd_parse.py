"""Tests for the pure kd-output parsers (no VM required)."""

from __future__ import annotations

from winvm_mcp.debug import kd_parse as P

# --------------------------------------------------------------------------- #
# strip_ansi
# --------------------------------------------------------------------------- #


def test_strip_ansi_csi() -> None:
    assert P.strip_ansi("\x1b[32mhello\x1b[0m") == "hello"


def test_strip_ansi_osc() -> None:
    assert P.strip_ansi("a\x1b]0;title\x07b") == "ab"


def test_strip_ansi_passthrough() -> None:
    assert P.strip_ansi("plain text") == "plain text"


# --------------------------------------------------------------------------- #
# prompt detection
# --------------------------------------------------------------------------- #


def test_looks_like_prompt_variants() -> None:
    for line in ("kd>", "lkd>", "0: kd>", "3: lkd>", "0: kd> ", "  kd>  "):
        assert P.looks_like_prompt(line), line


def test_looks_like_prompt_negatives() -> None:
    for line in ("0: kd> kb", "not a prompt", "kd", ">kd>", "0xffff kd>"):
        assert not P.looks_like_prompt(line), line


def test_has_trailing_prompt() -> None:
    assert P.has_trailing_prompt("foo\n0: kd>")
    assert P.has_trailing_prompt("foo\n0: kd> ")  # trailing space
    assert P.has_trailing_prompt("end with lkd>")
    assert not P.has_trailing_prompt("foo bar")
    assert not P.has_trailing_prompt("kd is great")


# --------------------------------------------------------------------------- #
# strip_command_echo (the bug that used to mangle hex output)
# --------------------------------------------------------------------------- #


def test_echo_with_prompt_prefix() -> None:
    out = "0: kd> kb\nRetAddr\n00 nt!foo\n0: kd>"
    assert P.strip_command_echo(out, "kb") == "RetAddr\n00 nt!foo\n0: kd>"


def test_echo_plain() -> None:
    assert P.strip_command_echo("kb\noutput here\n", "kb") == "output here"


def test_echo_does_not_mangle_hex_address() -> None:
    # Regression: old code did first.lstrip("0:l") which would strip the
    # leading "0" from real hex output. The first line here is the echo
    # ("0: kd> dt"); the second is real output starting with 0x.
    out = "0: kd> dt\n0xfffff8051234 _EPROCESS\n"
    assert P.strip_command_echo(out, "dt") == "0xfffff8051234 _EPROCESS"


def test_echo_leaves_unrelated_first_line() -> None:
    # If the first line is NOT the echoed command, leave everything intact.
    out = "some unrelated first line\nmore\n"
    assert P.strip_command_echo(out, "kb") == "some unrelated first line\nmore"


def test_echo_livekd_lkd_prefix() -> None:
    out = "lkd> bp nt!NtCreateFile\nbreakpoint set\nlkd>"
    assert P.strip_command_echo(out, "bp nt!NtCreateFile") == "breakpoint set\nlkd>"


# --------------------------------------------------------------------------- #
# strip_trailing_prompt
# --------------------------------------------------------------------------- #


def test_strip_trailing_prompt_basic() -> None:
    assert P.strip_trailing_prompt("line1\nline2\n0: kd>\n") == "line1\nline2"


def test_strip_trailing_prompt_multiple() -> None:
    assert P.strip_trailing_prompt("x\nlkd>\n0: kd>") == "x"


# --------------------------------------------------------------------------- #
# clean_command_output (full pipeline)
# --------------------------------------------------------------------------- #


def test_clean_full_pipeline() -> None:
    raw = "\x1b[0m0: kd> !process 0 0\nPROCESS ffffe00012345000\n    Cid: 0004\n0: kd> \n"
    assert P.clean_command_output(raw, "!process 0 0") == (
        "PROCESS ffffe00012345000\n    Cid: 0004"
    )


def test_clean_livekd_pipeline() -> None:
    raw = "lkd> bp nt!NtCreateFile\nbreakpoint 0 hit\nlkd>"
    assert P.clean_command_output(raw, "bp nt!NtCreateFile") == "breakpoint 0 hit"


def test_clean_no_output() -> None:
    assert P.clean_command_output("0: kd> r\n0: kd>", "r") == ""
