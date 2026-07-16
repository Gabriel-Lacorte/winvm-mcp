# Security Policy

## Supported versions

Only the latest release line receives security fixes.

## What counts as a security issue here

`winvm-mcp` is a tool whose **features** include remote command execution and
kernel-memory access on a VM the operator owns. Those capabilities are intended
and documented in [`docs/THREAT-MODEL.md`](docs/THREAT-MODEL.md). They are not
vulnerabilities.

Report a security issue if you find a way the tool **exceeds its intended
environment or trust boundaries**, for example:

- Any code path that binds a network listener or otherwise exposes the MCP
  transport beyond stdio.
- Credential handling bugs (e.g. credentials written to a world-readable file,
  logged, or sent somewhere unexpected).
- A host-key policy bypass, or SSH connection to a host other than the
  configured `ssh_host`.
- Command/argument injection that lets a tool call escape its intended target
  (e.g. vmrun argument smuggling, debugger-command injection into the host
  shell).
- Path traversal in host-side file operations (`guest_copy_to`/`_from`,
  screenshot paths).

## Reporting

**Please do not open a public GitHub issue for security reports.**

Instead, open a private security advisory via GitHub's "Report a vulnerability"
feature (Security tab → "Report a vulnerability"), or email the maintainers
directly if an advisory contact is listed in the repository description.

Include:

- A description of the issue and the impact.
- The trust boundary it crosses (see the threat model).
- Steps to reproduce, with the minimum config.

You should receive an acknowledgement within a few days. Coordinated disclosure
is fine — please give maintainers time to patch before publishing.

## Hardening reminders for operators

- Run the server over **stdio only**, as a child of your MCP client.
- Keep the VM on an **isolated network** (NAT / host-only).
- `config.toml` is git-ignored and holds plaintext guest credentials — protect
  the host filesystem accordingly.
- Prefer `[vm] ssh_host_key_policy = "known_hosts"` over `auto_add` where the
  reverted-VM key churn is acceptable.
