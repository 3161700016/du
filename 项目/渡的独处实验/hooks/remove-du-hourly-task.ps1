[CmdletBinding()]
param(
    [switch]$Apply
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$taskName = 'DuHourlyHeartbeat'

if (-not $Apply) {
    Write-Host 'No task was removed.'
    Write-Host "To remove the Windows Task Scheduler entry, run: .\hooks\remove-du-hourly-task.ps1 -Apply"
    exit 0
}

& schtasks.exe /Delete /TN $taskName /F
if ($LASTEXITCODE -ne 0) { throw "schtasks exited with code $LASTEXITCODE" }
Write-Host "Removed task: $taskName"
