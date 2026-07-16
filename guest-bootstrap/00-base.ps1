# 00-base.ps1 — Base hardening + OpenSSH server for the research guest.
# Run as Administrator. Idempotent.
#Usage:  powershell -ExecutionPolicy Bypass -File 00-base.ps1
#
# What this does:
#   * Creates the 'researcher' admin account used by vmrun + SSH
#   * Installs + starts the OpenSSH Server (ssh port 22)
#   * Disables Defender realtime + SmartScreen (so POC binaries are not eaten)
#   * Disables Sleep/Hibernate (so a long debug session never suspends)
#   * Sets the firewall to allow inbound WinRM + RDP + 50000/50001 (network KD)

#Requires -RunAsAdministrator

$ErrorActionPreference = 'Stop'

$USER = 'researcher'
$PASS = 'REPLACE_ME'   # <-- change before running; matches config.toml

Write-Host '[*] Configuring researcher account...'
if (-not (Get-LocalUser -Name $USER -ErrorAction SilentlyContinue)) {
    $sec = ConvertTo-SecureString $PASS -AsPlainText -Force
    New-LocalUser -Name $USER -Password $sec -FullName 'Research' -Description 'winvm-mcp account' | Out-Null
}
Add-LocalGroupMember -Group 'Administrators' -Member $USER -ErrorAction SilentlyContinue
# Let vmrun / SSH log in: enable password auth + relax local policies.
Set-LocalUser -Name $USER -PasswordNeverExpires $true

Write-Host '[*] Disabling sleep / hibernate / monitor-off (keep VM alive for long sessions)...'
powercfg /change standby-timeout-ac 0
powercfg /change monitor-timeout-ac 0
powercfg /change hibernate-timeout-ac 0
powercfg /h off

Write-Host '[*] Disabling Defender realtime + SmartScreen (analysis target)...'
Set-MpPreference -DisableRealtimeMonitoring $true -ErrorAction SilentlyContinue
# Tamper-protection may block the above on newer builds; document it if it stays on.
$m = Get-MpComputerStatus -ErrorAction SilentlyContinue
if ($m -and $m.RealTimeProtectionEnabled) {
    Write-Warning 'Realtime protection still on. Disable Tamper Protection in Settings -> Windows Security first, then rerun.'
}
New-ItemProperty -Path 'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer' -Name SmartScreenEnabled -Value 'Off' -PropertyType String -Force | Out-Null

Write-Host '[*] Installing OpenSSH Server...'
$cap = Get-WindowsCapability -Online -Name OpenSSH.Server~~~~0.0.1.0 -ErrorAction SilentlyContinue
if ($cap -and $cap.State -ne 'Installed') {
    Add-WindowsCapability -Online -Name OpenSSH.Server~~~~0.0.1.0 | Out-Null
}
Set-Service -Name sshd -StartupType Automatic
Start-Service sshd
# Default shell for OpenSSH = cmd; switch to PowerShell if you prefer:
# New-ItemProperty -Path 'HKLM:\SOFTWARE\OpenSSH' -Name DefaultShell -Value 'C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe' -PropertyType String -Force | Out-Null

Write-Host '[*] Firewall rules: SSH (22), WinRM (5985), RDP (3389), network-KD (50000-50001)...'
foreach ($r in @(
    @{Name='OpenSSH-Server-In-TCP'; Dir='In'; Port=22; Proto='TCP'},
    @{Name='WinRM-HTTP-In-TCP';      Dir='In'; Port=5985; Proto='TCP'},
    @{Name='RDP-In-TCP';             Dir='In'; Port=3389; Proto='TCP'},
    @{Name='NetKd-In-50000';         Dir='In'; Port=50000; Proto='TCP'},
    @{Name='NetKd-In-50001';         Dir='In'; Port=50001; Proto='TCP'}
)) {
    if (-not (Get-NetFirewallRule -Name $r.Name -ErrorAction SilentlyContinue)) {
        New-NetFirewallRule -Name $r.Name -DisplayName $r.Name -Direction $r.Dir -Protocol $r.Proto -LocalPort $r.Port -Action Allow | Out-Null
    }
}

Write-Host '[+] Base setup complete. ssh researcher@<guest-ip> should now work.'
