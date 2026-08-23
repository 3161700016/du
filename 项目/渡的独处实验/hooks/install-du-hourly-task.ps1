[CmdletBinding()]
param(
    [switch]$Apply
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$taskName = 'DuHourlyHeartbeat'
$runner = (Resolve-Path (Join-Path $PSScriptRoot 'du-hourly.ps1')).Path
$powerShell = Join-Path $PSHOME 'powershell.exe'
$taskCommand = '"{0}" -NoProfile -ExecutionPolicy Bypass -File "{1}"' -f $powerShell, $runner

if (-not $Apply) {
    Write-Host 'No task was created.'
    Write-Host "Review the hook, then run: .\hooks\install-du-hourly-task.ps1 -Apply"
    Write-Host "Planned task: $taskName"
    Write-Host "Planned cadence: every hour at minute 00"
    Write-Host "Planned command: $taskCommand"
    exit 0
}

& schtasks.exe /Create /TN $taskName /SC HOURLY /MO 1 /ST 00:00 /TR $taskCommand /RL LIMITED /F
if ($LASTEXITCODE -ne 0) { throw "schtasks exited with code $LASTEXITCODE" }
Write-Host "Created task: $taskName"
Write-Host 'The hook remains inert until hooks/du-hourly.config.json has enabled=true.'
