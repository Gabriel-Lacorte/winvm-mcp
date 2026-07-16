# Contributing

Thanks for your interest in improving `winvm-mcp`. This is a small, focused
project; these guidelines keep it healthy.

## Scope

`winvm-mcp` drives **one** VMware-hosted Windows VM for security research over
stdio. Changes that fit:

- Bug fixes (especially in debugger-command idioms, parsing, or transport rc).
- New tools that map to a real kernel-debugging / VM-ops primitive not already
  covered.
- Documentation, tests, and packaging improvements.

Changes that don't fit: additional hypervisors, a network/HTTP transport, or
anything that weakens the [threat model](docs/THREAT-MODEL.md) (e.g. exposing
the transport to a network).

## Setup

```bash
git clone https://github.com/winvm-mcp/winvm-mcp.git
cd winvm-mcp
uv venv --python 3.13 .venv
uv pip install --python .venv/bin/python -e ".[dev]"
```

## Before you submit

Run the local checks before submitting:

```bash
ruff check src tests && ruff format --check src tests
mypy src
pytest -q -m "not integration"
```

Conventions:

- **Add a test** for any new pure logic (config, parsers, argv builders). The
  kd-output parsers and vmrun argv builder are fully unit-tested; follow that
  pattern.
- **Update `tests/test_tools_registry.py`** (`EXPECTED`) when you add, rename,
  or remove a tool. The snapshot is intentional — it forces a conscious change.
- **Regenerate `docs/TOOL-REFERENCE.md`** after tool changes:
  ```bash
  .venv/bin/python - <<'PY'
  # see docs/TOOL-REFERENCE.md header for the generator; or re-run the snippet
  PY
  ```
  (The reference is produced from `build_server(...).list_tools()`.)
- **Keep tool docstrings** as the source of truth for tool descriptions — they
  become both the MCP tool description and the reference table.
- **Commit message** style: `feat:`, `fix:`, `docs:`, `test:`, `refactor:`,
  `chore:`. Reference the issue/PR where relevant.

## Integration tests

Tests that need a live VM are marked `@pytest.mark.integration` and run only
when `WINVM_INTEGRATION=1` is set. Don't make unit tests depend on a VM.

## Pull requests

Open a PR against `main`. The local checks must pass. For behavior-changing fixes (especially
debugger idioms), note the before/after in the PR description and update
[`CHANGELOG.md`](CHANGELOG.md).

## Code of conduct

Participation in this project is governed by the [Code of Conduct](CODE_OF_CONDUCT.md).
