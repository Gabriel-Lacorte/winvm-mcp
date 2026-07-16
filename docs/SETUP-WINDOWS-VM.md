# Windows VM setup for security research

End-to-end guide for the Windows guest that `winvm-mcp` drives: ISO install,
network, `.vmx` tuning, and the `guest-bootstrap/` scripts that provision
OpenSSH, kernel debugging, complete memory dumps, and the `livekd` launcher.

```
┌────────────────────────────────┐        ┌─────────────────────────────────┐
│  Host (Linux)                  │        │  Guest Windows (VMware)         │
│                                │        │                                 │
│  MCP client + winvm-mcp        │ vmrun  │  VMware Tools (vmrun auth)      │
│   ├─ vm_* / snapshot_*  ───────┼────────┼─▶ ├─ lifecycle + snapshots      │
│   ├─ guest_* (vmrun)    ───────┼────────┼─▶ ├─ exec / files / screen      |
│   ├─ ssh_*              ─── SSH:22 ─────┼─▶ ├─ OpenSSH: PowerShell / cmd  │
│   └─ kd_* / analyze_*   ─── SSH:22 ─────┼─▶ └─ cdb.exe / livekd.exe       │
└────────────────────────────────┘        └─────────────────────────────────┘
```

---

## Step 0 — Host prerequisites

| Item | Check |
|---|---|
| VMware Workstation/Player | `vmrun -v` |
| Python ≥ 3.11 | `python3 --version` |
| `vmrun` on PATH | `which vmrun` |
| vmnets active | `ls /dev/vmnet*` -> vmnet0/1/8 |

---

## Step 1 — Create the Windows VM

### 1.1 ISO and profile

Recommended: **Windows 10 22H2 Enterprise** (or 11 Pro). Suggested hardware:

| Resource | Value | Reason |
|---|---|---|
| vCPU | 4 | debugger + target |
| RAM | 8 GB | full dump + WinDbg |
| Disk | 80 GB (thin) | snapshots |
| Display | Uncheck "Accelerate 3D" | stability |

### 1.2 Network

Use **NAT (`vmnet8`)** for free host↔guest access. The host gets `192.168.184.1`
and the guest DHCPs into `192.168.184.128+`.

```bash
# host-side vmnet8 address (used by network-KD if you enable it)
ip addr show vmnet8
```

### 1.3 `.vmx` tuning (optional, recommended)

Edit the `.vmx` **with the VM powered off** for deterministic analysis:

```ini
# Reserved memory → reliable dumps
prefvmx.useRecommendedLockedMemSize = "TRUE"
mainMem.useNamedFile = "FALSE"

# Stable snapshots
snapshot.disabled = "FALSE"

# Don't fight copy/paste integration
isolation.tools.copy.disable = "FALSE"
isolation.tools.paste.disable = "FALSE"

# Keep the host responsive while the debugger works
priority.grabbed = "normal"
priority.ungrabbed = "normal"
```

> Keep a **`clean-base`** snapshot (OS + tools + debug, no target) and a
> **`target-ready`** snapshot (target installed). Revert between PoCs so every
> analysis starts from the same state.

---

## Step 2 — Bootstrap the guest (PowerShell)

Transfer the `guest-bootstrap/` folder into the guest (e.g. via `guest_copy_to`
once Tools is up, or a shared folder) and run, **as Administrator**:

```powershell
cd C:\winvm-mcp\guest-bootstrap

# BEFORE running: edit 00-base.ps1 -> $PASS, and 10-kernel-debug.ps1 -> $HOST_IP / $KEY
powershell -ExecutionPolicy Bypass -File 00-base.ps1
powershell -ExecutionPolicy Bypass -File 10-kernel-debug.ps1
shutdown /r /t 0          # bcdedit requires a reboot
# ...after reboot...
powershell -ExecutionPolicy Bypass -File 20-windbg.ps1
powershell -ExecutionPolicy Bypass -File 30-livekd-launcher.ps1
```

| Script | What it does |
|---|---|
| `00-base.ps1` | `researcher` admin account, OpenSSH Server, firewall (22/5985/3389/50000-1), disables Defender realtime + SmartScreen, disables sleep/hibernate. |
| `10-kernel-debug.ps1` | `bcdedit /debug on`, network-KD (`port=50000,key=1.2.3.4.5`), `testsigning on`, **complete** dumps in `MEMORY.DMP`, `AutoReboot=0`. |
| `20-windbg.ps1` | Installs Debugging Tools (`cdb.exe`/`kd.exe`) + Sysinternals LiveKd. |
| `30-livekd-launcher.ps1` | Writes `C:\winvm-mcp\kd-livekd.bat`, the launcher `kd_connect('livekd')` runs. |

Post-bootstrap checks:

```powershell
bcdedit /enum {current}                       # debug on, dbgsettings
Get-Service sshd                              # Running
Test-Path 'C:\Program Files (x86)\Windows Kits\10\Debuggers\x64\cdb.exe'
Get-Command livekd.exe
Test-Path C:\winvm-mcp\kd-livekd.bat
```

---

## Step 3 — Validate from the host

### 3.1 vmrun (no SSH, just VMware Tools)

```bash
vmrun -T ws -gu researcher -gp '' listProcessesInGuest /root/vmware/w10/w10.vmx
```

### 3.2 SSH

```bash
ssh researcher@192.168.184.128 'whoami && ver'
```

### 3.3 livekd manually

```bash
ssh researcher@192.168.184.128 'C:\winvm-mcp\kd-livekd.bat'
# inside cdb:  !process 0 0   |   kb   |   !pte   |   q
```

---

## Step 4 — Configure `winvm-mcp`

```bash
cp config.example.toml config.toml
$EDITOR config.toml      # vmx, password, ssh_host, debugger_path, ...
```

Smoke-test:

```bash
winvm-mcp --version
# then start it briefly with WINVM_MCP_CONFIG pointing at your config; it should not error
```

---

## Step 5 — Register with your MCP client

See the README -> "Register with an MCP client". In short, add a stdio server
entry pointing at `winvm-mcp` with `WINVM_MCP_CONFIG` set.

---

## Step 6 — Typical vulnerability-hunting flow

A loop that combines static analysis (IDA/Ghidra MCP) with this server:

1. **Static** find a dangerous `ioctl` handler, an unchecked `memcpy`, etc.
   Note offsets / structs.
2. **Prepare the target**
   ```
   snapshot_revert("target-ready")
   ssh_powershell("Copy-Item C:\\poc.exe C:\\winvm-mcp\\")
   ```
3. **Attach observers**
   ```
   ssh_powershell("wevtutil cl System")
   kd_connect("livekd")
   kd_command("!process 0 0")          # confirm the driver loaded
   kd_command("bp <mod>!<suspect>")    # breakpoint
   kd_command("g")
   ```
4. **Fire the PoC**
   ```
   ssh_exec_cmd("C:\\winvm-mcp\\poc.exe")
   ```
5. **Capture evidence**
   - On bug-check (guest freezes, `AutoReboot=0`): take a dump and triage
     ```
     kd_disconnect()
     analyze_dump_overview('C:\\Windows\\MEMORY.DMP')
     ```
   - On success (privesc/corruption): screen + state
     ```
     guest_capture_screen()
     ssh_powershell("whoami /priv; whoami /groups")
     kd_token("0n<winlogon_pid>")
     ```
6. **Reproduce** `snapshot_revert("target-ready")` and run again.
7. **Report** the model consolidates offsets (static), kernel trace (`kd`),
   and userland evidence (`ssh`) into a single write-up.

---

## Lab hardening (do not skip)

- **Isolated network** NAT/host-only only; never bridged onto a LAN you care
  about.
- **Frequent snapshots** always revert before a new PoC.
- **No real credentials** the `researcher` account lives only in the VM.
- **Local transport only** the server speaks stdio; never expose it to a
  network (see [`THREAT-MODEL.md`](THREAT-MODEL.md)).
- **Forensic auditing (optional)** `auditpol /set /category:* /success:enable
  /failure:enable`.

---

## Troubleshooting

| Symptom | Cause / fix |
|---|---|
| `vmrun: Guest operations are not enabled` | Reinstall/reboot VMware Tools; check `checkToolsState`. |
| `SSH connect failed: Authentication failed` | Check `ssh_username`/`ssh_password`; or `sshd` is stopped. |
| Defender eats the PoC | `Set-MpPreference -DisableRealtimeMonitoring $true` (+ disable Tamper Protection in the UI first). |
| `kd_connect` hangs with no prompt | livekd is slow on large RAM; raise `timeout=180`. |
| No dump generated | `CrashDumpEnabled=1` needs a pagefile ≥ RAM; check `Get-CimInstance Win32_PageFileUsage`. |
| `bcdedit` ignored | Did you reboot? Only effective after the next boot. |
| ASLR shifts offsets per reboot | Snapshots pin state; or `bcdedit /set nx optout` + per-process DEP off. |
| `kd_connect('livekd')` says the launcher is missing | Run `30-livekd-launcher.ps1`; confirm `C:\winvm-mcp\kd-livekd.bat` exists and the `debugger_path` in it matches your install. |
