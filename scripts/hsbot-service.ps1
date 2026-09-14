# HSBot - Windows background service for the LOCAL backend
#
# Runs the FastAPI backend (uvicorn) in the background, auto-starting at logon,
# with automatic restart on crash. Voice + OS automation only work against this
# local backend, so the desktop overlay uses it.
#
# Usage (from repo root):
#   .\scripts\hsbot-service.ps1 install     Register auto-start (logon task)
#   .\scripts\hsbot-service.ps1 start       Start now (no task needed)
#   .\scripts\hsbot-service.ps1 stop        Stop now
#   .\scripts\hsbot-service.ps1 restart     Stop + start
#   .\scripts\hsbot-service.ps1 status      Show task + backend state
#   .\scripts\hsbot-service.ps1 uninstall   Remove the task
#   .\scripts\hsbot-service.ps1 -Run        (internal) run backend with restart loop
#
# Requirements: run from a PowerShell window; no admin needed (user-level task).

param(
    [switch]$Run,
    [Parameter(Position = 0)]
    [ValidateSet("install", "uninstall", "start", "stop", "restart", "status")]
    [string]$Command = ""
)

$ErrorActionPreference = "Stop"
$TaskName = "HSBotBackend"
$RepoRoot = Split-Path -Parent $PSScriptRoot
$PythonExe = Join-Path $RepoRoot ".venv312\Scripts\python.exe"
$BackendDir = Join-Path $RepoRoot "backend"
$DataDir = Join-Path $RepoRoot "data"
$LogFile = Join-Path $DataDir "service.log"
$PidFile = Join-Path $DataDir "service.pid"
$HostAddress = "127.0.0.1"
$Port = 8000

if (-not (Test-Path -LiteralPath $DataDir)) {
    New-Item -ItemType Directory -Path $DataDir -Force | Out-Null
}

function Get-RunningPid {
    if (Test-Path -LiteralPath $PidFile) {
        $BackendPid = [int](Get-Content -LiteralPath $PidFile -Raw).Trim()
        $proc = Get-Process -Id $BackendPid -ErrorAction SilentlyContinue
        if ($proc -and $proc.ProcessName -like "python*") { return $BackendPid }
        Remove-Item -LiteralPath $PidFile -Force -ErrorAction SilentlyContinue
    }
    $null
}

function Start-BackendNow {
    if (Get-RunningPid) {
        Write-Host "HSBot backend already running (pid $(Get-RunningPid))." -ForegroundColor Yellow
        return
    }
    if (-not (Test-Path -LiteralPath $PythonExe)) {
        Write-Host "Virtual env python not found: $PythonExe (run .\scripts\setup.ps1 first)" -ForegroundColor Red
        exit 1
    }
    $proc = Start-Process -FilePath $PythonExe `
        -ArgumentList @("-m", "uvicorn", "app.main:app", "--host", $HostAddress, "--port", $Port) `
        -WorkingDirectory $BackendDir `
        -WindowStyle Hidden `
        -RedirectStandardOutput $LogFile `
        -RedirectStandardError (Join-Path $DataDir "service.err.log") `
        -PassThru
    Set-Content -LiteralPath $PidFile -Value $proc.Id
    Write-Host "HSBot backend started (pid $($proc.Id)) on http://$HostAddress`:$Port  log: $LogFile" -ForegroundColor Green
}

function Stop-BackendNow {
    $BackendPid = Get-RunningPid
    if ($BackendPid) {
        Stop-Process -Id $BackendPid -Force
        Remove-Item -LiteralPath $PidFile -Force -ErrorAction SilentlyContinue
        Write-Host "HSBot backend stopped (was pid $BackendPid)." -ForegroundColor Green
    } else {
        Write-Host "HSBot backend is not running." -ForegroundColor Yellow
    }
}

if ($Run) {
    # Internal: hidden worker loop with crash restart (used by the logon task).
    while ($true) {
        try {
            & $PythonExe -m uvicorn app.main:app --host $HostAddress --port $Port 2>&1 | Out-File -Append -LiteralPath $LogFile
        } catch {
            Add-Content -LiteralPath $LogFile -Value "[$(Get-Date -Format s)] service loop error: $_"
        }
        Start-Sleep -Seconds 5
    }
    exit
}

switch ($Command) {
    "install" {
        $action = New-ScheduledTaskAction -Execute "powershell.exe" `
            -Argument "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$PSScriptRoot\hsbot-service.ps1`" -Run"
        $trigger = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
        $settings = New-ScheduledTaskSettingsSet -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1) `
            -ExecutionTimeLimit ([TimeSpan]::Zero) -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
        Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings `
            -Description "HSBot local backend (voice + OS automation)" -Force | Out-Null
        Write-Host "Task '$TaskName' registered (starts at logon). Run 'hsbot-service.ps1 start' now to launch it." -ForegroundColor Green
    }
    "uninstall" {
        Stop-BackendNow
        Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
        Write-Host "Task '$TaskName' removed." -ForegroundColor Green
    }
    "start" { Start-BackendNow }
    "stop" { Stop-BackendNow }
    "restart" {
        Stop-BackendNow
        Start-Sleep -Seconds 1
        Start-BackendNow
    }
    "status" {
        $task = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
        $BackendPid = Get-RunningPid
        $health = $null
        if ($BackendPid) {
            try {
                $health = (Invoke-RestMethod -Uri "http://$HostAddress`:$Port/api/health" -TimeoutSec 3).status
            } catch { $health = "unreachable" }
        }
        Write-Host "Task: $([bool]$task)   Backend pid: $(if ($BackendPid) { $BackendPid } else { 'none' })   Health: $(if ($health) { $health } else { 'none' })"
    }
    default {
        Write-Host "Usage: .\scripts\hsbot-service.ps1 <install|uninstall|start|stop|restart|status>"
    }
}