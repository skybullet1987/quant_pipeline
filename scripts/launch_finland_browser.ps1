param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$Urls
)

$ErrorActionPreference = "Continue"
Write-Host "=====================================================================" -ForegroundColor Cyan
Write-Host "  DOMINUS FINLAND TUNNEL BROWSER (0 MB VM Chrome/Xorg Overhead)" -ForegroundColor Cyan
Write-Host "  Routing isolated Edge window via kraken-finland (SOCKS5 :1088)..." -ForegroundColor Cyan
Write-Host "=====================================================================" -ForegroundColor Cyan

function Test-FinlandTunnel {
    $trace = & "$env:SystemRoot\System32\curl.exe" -s --max-time 5 --socks5-hostname 127.0.0.1:1088 "https://1.1.1.1/cdn-cgi/trace" 2>$null
    if (-not $trace) { return $null }
    $map = @{}
    foreach ($line in ($trace -split "`r?`n")) {
        if ($line -match "^([^=]+)=(.*)$") {
            $map[$matches[1]] = $matches[2].Trim()
        }
    }
    if ($map["loc"] -eq "FI" -and $map["ip"]) {
        return $map
    }
    return $null
}

$info = Test-FinlandTunnel
if (-not $info) {
    $listeners = Get-NetTCPConnection -LocalAddress 127.0.0.1 -LocalPort 1088 -State Listen -ErrorAction SilentlyContinue
    foreach ($l in $listeners) {
        if ($l.OwningProcess -gt 0) {
            Write-Host "Cleaning up stale listener on 127.0.0.1:1088 (PID $($l.OwningProcess))..." -ForegroundColor Yellow
            Stop-Process -Id $l.OwningProcess -Force -ErrorAction SilentlyContinue
        }
    }

    Write-Host "Starting background SSH SOCKS5 tunnel to kraken-finland on 127.0.0.1:1088..." -ForegroundColor Yellow
    Start-Process -FilePath "ssh" -WindowStyle Hidden -ArgumentList @(
        "-C", "-N", "-D", "127.0.0.1:1088",
        "-o", "BatchMode=yes",
        "-o", "ExitOnForwardFailure=yes",
        "-o", "ServerAliveInterval=30",
        "-o", "ServerAliveCountMax=3",
        "kraken-finland"
    )

    for ($i = 0; $i -lt 8; $i++) {
        Start-Sleep -Seconds 1
        $info = Test-FinlandTunnel
        if ($info) { break }
    }
}

if (-not $info) {
    Write-Host "`n[ERROR] End-to-end Finland SOCKS5 check failed on 127.0.0.1:1088! Aborting fail-closed." -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host "[OK] Verified Finland VM Egress: IP=$($info['ip']) | Country=$($info['loc'])" -ForegroundColor Green

$edgeExe = "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
if (-not (Test-Path $edgeExe)) {
    $edgeExe = "C:\Program Files\Microsoft\Edge\Application\msedge.exe"
}
if (-not (Test-Path $edgeExe)) {
    Write-Host "`n[ERROR] Microsoft Edge executable not found! Aborting fail-closed." -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

$profileDir = Join-Path $env:LOCALAPPDATA "DominusFinlandEdge"

# Detect and clean up any hidden/zombie DominusFinlandEdge processes that lack a visible window
$existingCim = @(Get-CimInstance Win32_Process -Filter "Name='msedge.exe'" -ErrorAction SilentlyContinue |
    Where-Object { $_.CommandLine -match "DominusFinlandEdge" })

if ($existingCim.Count -gt 0) {
    $visibleHandles = @(foreach ($c in $existingCim) {
        $p = Get-Process -Id $c.ProcessId -ErrorAction SilentlyContinue
        if ($p -and $p.MainWindowHandle -ne [IntPtr]::Zero) { $p.MainWindowHandle }
    })
    if ($visibleHandles.Count -eq 0) {
        Write-Host "Cleaning up $($existingCim.Count) hidden background DominusFinlandEdge process(es)..." -ForegroundColor Yellow
        foreach ($c in $existingCim) {
            Stop-Process -Id $c.ProcessId -Force -ErrorAction SilentlyContinue
        }
        Start-Sleep -Milliseconds 600
    }
}

if (-not $Urls -or $Urls.Count -eq 0) {
    $Urls = @(
        "https://1.1.1.1/cdn-cgi/trace",
        "https://polymarket.com/settings?tab=builder"
    )
}

$edgeArgs = @(
    "--user-data-dir=`"$profileDir`"",
    "--new-window",
    "--proxy-server=`"socks5://127.0.0.1:1088`"",
    "--host-resolver-rules=`"MAP * ~NOTFOUND , EXCLUDE 127.0.0.1`"",
    "--proxy-bypass-list=`"<-loopback>`"",
    "--force-webrtc-ip-handling-policy=disable_non_proxied_udp",
    "--disable-quic",
    "--disable-features=msEdgeStartupBoost",
    "--disable-background-mode",
    "--no-first-run"
) + @($Urls | ForEach-Object { "`"$_`"" })

Write-Host "Opening visible Finland-routed Edge window..." -ForegroundColor Cyan
Start-Process -FilePath $edgeExe -WindowStyle Normal -ArgumentList $edgeArgs | Out-Null

$hwnd = [IntPtr]::Zero
for ($i = 0; $i -lt 12; $i++) {
    Start-Sleep -Milliseconds 500
    $procs = @(Get-CimInstance Win32_Process -Filter "Name='msedge.exe'" -ErrorAction SilentlyContinue |
        Where-Object { $_.CommandLine -match "DominusFinlandEdge" })
    foreach ($c in $procs) {
        $p = Get-Process -Id $c.ProcessId -ErrorAction SilentlyContinue
        if ($p -and $p.MainWindowHandle -ne [IntPtr]::Zero) {
            $hwnd = $p.MainWindowHandle
            break
        }
    }
    if ($hwnd -ne [IntPtr]::Zero) { break }
}

if ($hwnd -ne [IntPtr]::Zero) {
    $existingWatcher = @(Get-CimInstance Win32_Process -Filter "Name='powershell.exe'" -ErrorAction SilentlyContinue |
        Where-Object { $_.CommandLine -match "DominusFinlandTunnelWatcher" })
    if ($existingWatcher.Count -eq 0) {
        $watcherCmd = @'
# DominusFinlandTunnelWatcher
$idleChecks = 0
while ($true) {
    Start-Sleep -Seconds 15
    $listeners = @(Get-NetTCPConnection -LocalAddress 127.0.0.1 -LocalPort 1088 -State Listen -ErrorAction SilentlyContinue)
    if ($listeners.Count -eq 0) { break }
    $edgeProcs = @(Get-CimInstance Win32_Process -Filter "Name='msedge.exe'" -ErrorAction SilentlyContinue |
        Where-Object { $_.CommandLine -match "DominusFinlandEdge" })
    if ($edgeProcs.Count -eq 0) {
        $idleChecks++
        if ($idleChecks -ge 2) {
            foreach ($l in $listeners) {
                if ($l.OwningProcess -gt 0) {
                    Stop-Process -Id $l.OwningProcess -Force -ErrorAction SilentlyContinue
                }
            }
            break
        }
    } else {
        $idleChecks = 0
    }
}
'@
        $encodedWatcher = [Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($watcherCmd))
        Start-Process -FilePath "powershell.exe" -WindowStyle Hidden -ArgumentList @(
            "-NoProfile", "-ExecutionPolicy", "Bypass", "-EncodedCommand", $encodedWatcher
        ) | Out-Null
    }
    Write-Host "[OK] Visible Finland Edge window is OPEN (HWND=$hwnd; tunnel auto-closes 30s after window exit)." -ForegroundColor Green
    Start-Sleep -Seconds 2
    exit 0
} else {
    Write-Host "[WARN] Edge started, but no visible window handle was detected yet." -ForegroundColor Yellow
    Read-Host "Press Enter to close this launcher"
    exit 1
}
