# 30-livekd-launcher.ps1 — Create the livekd launcher used by the kd_* tools.
# Run as Administrator. Idempotent. No reboot needed.
#Usage:  powershell -ExecutionPolicy Bypass -File 30-livekd-launcher.ps1
#
# The MCP server's kd_connect('livekd') runs `<guest_workdir>\kd-livekd.bat`
# inside the guest over SSH. Putting the livekd invocation in a .bat keeps all
# the path-quoting local to the guest (SSH + cmd + livekd quoting is fragile),
# so the server only has to launch one well-known file.
#
# If your Debugging Tools live somewhere other than the default path below,
# edit $CDB and re-run this script.

#Requires -RunAsAdministrator
$ErrorActionPreference = 'Stop'

$work = 'C:\winvm-mcp'
New-Item -ItemType Directory -Force -Path $work | Out-Null

# Default Debugging Tools for Windows x64 install path. Adjust if needed.
$CDB = 'C:\Program Files (x86)\Windows Kits\10\Debuggers\x64\cdb.exe'

$bat = Join-Path $work 'kd-livekd.bat'
$lines = @(
    '@echo off',
    'setlocal',
    "set ""CDB=$CDB""",
    'if not exist "%CDB%" (',
    '    echo [kd-livekd.bat] cdb.exe not found at "%CDB%" 1^>^&2',
    '    exit /b 1',
    ')',
    'livekd.exe -k "%CDB%"'
)
Set-Content -Path $bat -Value $lines -Encoding ASCII

if (Test-Path $bat) {
    Write-Host "[+] Wrote $bat"
    Write-Host "    (launches livekd.exe -k `"$CDB`")"
} else {
    Write-Warning "Failed to write $bat"
}
