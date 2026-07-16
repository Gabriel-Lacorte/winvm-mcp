# 20-windbg.ps1 — Install Debugging Tools for Windows (cdb.exe/kd.exe) + LiveKd.
# Run as Administrator. No reboot needed.
#Usage:  powershell -ExecutionPolicy Bypass -File 20-windbg.ps1
#
# Installs:
#   * Windows Debugging Tools (x64) -> gives cdb.exe, kd.exe, dbghelp
#   * Sysinternals LiveKd          -> lets cdb debug the *running* kernel

#Requires -RunAsAdministrator
$ErrorActionPreference = 'Stop'

$work = 'C:\winvm-mcp'
New-Item -ItemType Directory -Force -Path $work | Out-Null

# ------------------------------------------------------------------ winget --
Write-Host '[*] Ensuring winget is available...'
$winget = Get-Command winget -ErrorAction SilentlyContinue
if (-not $winget) {
    Write-Host '[*] Installing App Installer (provides winget) from the Store...'
    # On Server SKUs without Store, fall back to direct SDK download (below).
    Get-AppxPackage -Name '*WindowsStore*' -ErrorAction SilentlyContinue | ForEach-Object {
        Add-AppxPackage -DisableDevelopmentMode -Register "$($_.InstallLocation)\AppXManifest.xml"
    }
}

# ------------------------------------------------------- Debugging Tools ----
$kits = 'C:\Program Files (x86)\Windows Kits\10\Debuggers\x64'
if (-not (Test-Path "$kits\cdb.exe")) {
    Write-Host '[*] Installing Windows Debugging Tools via winget (SDK subset)...'
    if ($winget) {
        winget install --id Microsoft.WinDbg --silent --accept-source-agreements --accept-package-agreements | Out-Null
    }
    # Belt-and-suspenders: download the standalone SDK installer and extract just the debuggers.
    if (-not (Test-Path "$kits\cdb.exe")) {
        Write-Host '[*] Falling back to direct SDK redist download...'
        $iso = Join-Path $work 'sdksetup.exe'
        Invoke-WebRequest 'https://go.microsoft.com/fwlink/?linkid=2231951' -OutFile $iso -UseBasicParsing
        Start-Process -FilePath $iso -ArgumentList '/quiet','/features OptionId.WindowsDesktopDebuggers','/ce ipathoff' -Wait
    }
}

if (Test-Path "$kits\cdb.exe") {
    Write-Host "[+] Debugging Tools OK: $kits\cdb.exe"
} else {
    Write-Warning "cdb.exe not found at $kits. Install WinDbg manually from the Microsoft Store."
}

# --------------------------------------------------------------- LiveKd ------
if (-not (Get-Command livekd.exe -ErrorAction SilentlyContinue)) {
    Write-Host '[*] Installing Sysinternals LiveKd...'
    $sys = 'C:\Sysinternals'
    New-Item -ItemType Directory -Force -Path $sys | Out-Null
    $zip = Join-Path $work 'SysinternalsSuite.zip'
    Invoke-WebRequest 'https://download.sysinternals.com/files/SysinternalsSuite.zip' -OutFile $zip -UseBasicParsing
    Expand-Archive -Path $zip -DestinationPath $sys -Force
    # Put livekd where PATH can find it (and where the SSH kd_* tools assume it).
    [Environment]::SetEnvironmentVariable('Path', $sys + ';' + [Environment]::GetEnvironmentVariable('Path','Machine'), 'Machine')
    $env:Path = $sys + ';' + $env:Path
}
if (Get-Command livekd.exe -ErrorAction SilentlyContinue) {
    Write-Host '[+] LiveKd OK.'
} else {
    Write-Warning 'livekd.exe not on PATH. Re-open the shell or copy C:\Sysinternals\livekd64.exe to livekd.exe in a PATH dir.'
}

Write-Host ''
Write-Host '[+] Done. Smoke-test from this box:'
Write-Host '      livekd.exe -k "C:\Program Files (x86)\Windows Kits\10\Debuggers\x64\cdb.exe"'
