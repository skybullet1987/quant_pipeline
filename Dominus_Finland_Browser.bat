@echo off
title Dominus Finland Tunnel Browser (0 MB VM Overhead)
echo =====================================================================
echo   DOMINUS FINLAND TUNNEL BROWSER (0 MB VM Chrome/Xorg Overhead)
echo   Routing isolated Edge window via kraken-finland (SOCKS5 :1088)...
echo =====================================================================

netstat -ano | findstr "127.0.0.1:1088" | findstr "LISTENING" >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo Starting background SSH SOCKS5 tunnel to kraken-finland on 127.0.0.1:1088...
    powershell -NoProfile -WindowStyle Hidden -Command "Start-Process ssh -WindowStyle Hidden -ArgumentList '-N','-D','127.0.0.1:1088','-o','BatchMode=yes','-o','ExitOnForwardFailure=yes','-o','ServerAliveInterval=30','-o','ServerAliveCountMax=3','kraken-finland'"
    timeout /t 3 /nobreak >nul
) else (
    echo SSH SOCKS5 tunnel already active on 127.0.0.1:1088.
)

netstat -ano | findstr "127.0.0.1:1088" | findstr "LISTENING" >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] SOCKS5 tunnel on 127.0.0.1:1088 failed to start! Aborting browser launch fail-closed.
    pause
    exit /b 1
)

set "EDGE_EXE=C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
if not exist "%EDGE_EXE%" set "EDGE_EXE=C:\Program Files\Microsoft\Edge\Application\msedge.exe"
if not exist "%EDGE_EXE%" (
    echo [ERROR] Microsoft Edge executable not found. Aborting fail-closed.
    pause
    exit /b 1
)

echo Launching isolated Finland-routed Edge window (your normal browsers stay on Ontario IP)...
start "" "%EDGE_EXE%" --user-data-dir="%LOCALAPPDATA%\DominusFinlandEdge" --proxy-server="socks5://127.0.0.1:1088" --host-resolver-rules="MAP * ~NOTFOUND , EXCLUDE 127.0.0.1" --proxy-bypass-list="<-loopback>" --force-webrtc-ip-handling-policy=disable_non_proxied_udp --disable-background-mode --no-first-run "https://polymarket.com/settings?tab=builder"
