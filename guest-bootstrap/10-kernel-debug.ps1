# 10-kernel-debug.ps1 — Enable kernel debugging + complete memory dumps.
# Run as Administrator. Requires a reboot for bcdedit settings to take effect.
#Usage:  powershell -ExecutionPolicy Bypass -File 10-kernel-debug.ps1
#
# Two complementary debug transports are configured so you can choose later:
#   1) Network-mode KD  (host runs WinDbg, debugs the VM over TCP)  -> recommended
#   2) Local debug/test mode (cdb -k / livekd works on this same box)

#Requires -RunAsAdministrator
$ErrorActionPreference = 'Stop'

# --- 1. Network-mode KD ----------------------------------------------------
# hostip = the VMware host (your Linux box) that will run the debugger client.
# key    = any 5-octet string you like; reuse the SAME one in WinDbg on the host.
$HOST_IP = '192.168.184.1'    # <-- the vmnet8 host-side address (see `ip a` on Linux)
$KEY     = '1.2.3.4.5'

Write-Host "[*] Setting network KD: hostip=$HOST_IP port=50000 key=$KEY"
bcdedit /dbgsettings net hostip:$HOST_IP port:50000 key:$KEY | Out-Null
bcdedit /debug on | Out-Null

# --- 2. Test/debug mode so cdb -k / livekd can attach locally --------------
Write-Host '[*] Enabling testsigning + debug boot for local cdb/livekd...'
bcdedit /set testsigning on | Out-Null
bcdedit /set debug on        | Out-Null

# --- 3. Full memory dumps on bugcheck --------------------------------------
Write-Host '[*] Switching crash dumps to "Complete" (kernel/full is enough for most)...'
# 0 = none, 1 = complete, 2 = kernel, 3 = small (minidump, default)
$key = 'HKLM:\SYSTEM\CurrentControlSet\Control\CrashControl'
Set-ItemProperty -Path $key -Name CrashDumpEnabled -Value 1 -Type DWord
Set-ItemProperty -Path $key -Name DumpFile -Value '%SystemRoot%\MEMORY.DMP' -Type ExpandString
Set-ItemProperty -Path $key -Name MinidumpDir -Value '%SystemRoot%\Minidump' -Type ExpandString
Set-ItemProperty -Path $key -Name AutoReboot -Value 0 -Type DWord   # freeze so we can inspect
Set-ItemProperty -Path $key -Name Overwrite -Value 1 -Type DWord
# Make sure the pagefile covers RAM (full dumps need >= RAM).
$pf = (Get-CimInstance Win32_PageFileUsage -ErrorAction SilentlyContinue)
if (-not $pf) {
    Write-Host '[*] Creating system-managed pagefile so dumps can be written...'
    Set-CimInstance -Query 'Select * from Win32_ComputerSystem' -Property @{AutomaticManagedPagefile=$true}
}

Write-Host ''
Write-Host '[!] Reboot now for bcdedit changes to apply:'
Write-Host '      shutdown /r /t 0'
Write-Host ''
Write-Host '[i] After reboot, verify with:   bcdedit /enum {current}'
Write-Host '[i] From the Linux host, attach WinDbg with:'
Write-Host "      windbg -k net:port=50000,key=$KEY"
