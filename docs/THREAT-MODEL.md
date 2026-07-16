# Threat Model

`winvm-mcp` is a deliberately powerful tool: it exposes **remote command
execution and kernel-memory access** on a Windows VM to whichever process drives
its MCP transport. This page states the assumptions, the assets, the threats, and
the mitigations, so operators can deploy it safely.

## Intended environment

- A **researcher's host** (Linux) running a single MCP client (e.g. Claude Code,
  Cursor, Crush) over **stdio**.
- A **local lab VM** the researcher owns, on an **isolated network** (VMware NAT
  `vmnet8` or host-only). **Never bridged onto a production LAN.**
- The VM is a throwaway analysis target; it may be intentionally compromised by
  PoCs.

Out of scope: multi-tenant use, exposing the transport over a network, driving a
VM you do not own or are not authorized to test.

## Assets

| Asset | Why it matters |
|---|---|
| Guest credentials (`config.toml`) | vmrun + SSH auth to an admin account on the VM. |
| Host `vmrun` access | Can start/stop/revert any VM on the host. |
| Guest kernel memory | Full read (and via the model's intent, the means to corrupt) guest kernel state. |
| Host filesystem (stdout paths) | `guest_copy_to`/`_from` and screenshot paths touch host files. |

## Trust boundaries

1. **MCP client → server (stdio, host-local).** Trusted: the client is the
   researcher's agent. The server must NOT be reachable over the network.
2. **Host → guest (vmrun / SSH).** Authenticated with guest credentials held in
   `config.toml`. SSH should use `known_hosts` pinning where feasible.
3. **Guest kernel.** Fully controlled by design once a `kd` session is open.

## Threats and mitigations

### T1 — Transport exposed to a network (HIGH)

If the stdio transport were bridged to TCP, any network client could invoke
`guest_exec` / `ssh_exec_cmd` → full RCE on the guest, and `kd_*` → kernel
access.

**Mitigation:** the server binds **stdio only**; there is no `--listen`/HTTP
mode. Run it solely as a child process of your MCP client. Document this
prominently (README + here).

### T2 — Credential leakage via `config.toml` (HIGH)

The config holds plaintext guest credentials and is easy to `git commit`.

**Mitigation:**
- `config.toml` is in `.gitignore`; only `config.example.toml` (placeholders) is
  tracked.
- Bootstrap creates a dedicated `researcher` account that lives **only** in the
  lab VM; never reuse real credentials.

### T3 — SSH MITM on first connect (MEDIUM)

`auto_add` host-key policy accepts any host key, allowing a man-in-the-middle on
first connect.

**Mitigation:** policy is configurable. Set `[vm] ssh_host_key_policy =
"known_hosts"` and pre-populate `~/.ssh/known_hosts` (e.g. `ssh-keyscan`) for a
pinned key. `auto_add` remains the default because reverted lab VMs frequently
present a new key, but the trade-off is documented.

### T4 — Process-list exposure of guest password (LOW–MEDIUM)

`vmrun -gp <password>` passes the credential as a CLI argument, visible in the
host process list to other local users.

**Mitigation:** this is inherent to vmrun's auth model and cannot be avoided
without a different guest-ops mechanism. Acceptable on a single-user research
host; do not run on multi-tenant hosts.

### T5 — PoC / exploit escape to host (MEDIUM)

A kernel exploit in the guest could, in principle, target the hypervisor or
shared resources.

**Mitigation:** keep the VM isolated (NAT/host-only, no shared folders with the
host unless needed), revert snapshots between PoCs, and run only trusted
debugger tooling on the host.

### T6 — Unintended destructive guest actions (LOW)

`snapshot_delete`, `vm_reset`, `guest_delete_path` are irreversible.

**Mitigation:** these return clear `[ERROR]`/status text; the model is
instructed (via tool docstrings) on irreversibility. Maintain a `clean-base`
snapshot that is never deleted.

## Operational rules

1. **Local transport only.** Never expose the MCP server to a network.
2. **Isolated VM network.** NAT or host-only; never bridged to a LAN you care
   about.
3. **Dedicated, throwaway credentials.** The `researcher` account lives only in
   the VM.
4. **Snapshot discipline.** Revert to a known-good snapshot before each PoC;
   keep an undeletable `clean-base`.
5. **Auditing (optional, for forensic work).** Enable guest audit logging:
   `auditpol /set /category:* /success:enable /failure:enable`.

## Reporting security issues

See [`SECURITY.md`](SECURITY.md). This tool's "vulnerabilities" (RCE, kernel
access) are features in its intended environment; security reports should
concern unintended exposure (e.g. a network listener, credential handling bugs).
