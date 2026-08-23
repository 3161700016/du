[CmdletBinding()]
param(
    [switch]$DryRun
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$root = (Resolve-Path (Join-Path $PSScriptRoot '..\..\..')).Path
$configPath = Join-Path $PSScriptRoot 'du-hourly.config.json'
$promptPath = Join-Path $PSScriptRoot 'du-hourly-protocol.md'
$stateDir = Join-Path $PSScriptRoot 'state'
$runsDir = Join-Path $stateDir 'runs'
$lockPath = Join-Path $stateDir 'du-hourly.lock'

function Write-HeartbeatMessage([string]$Message) {
    Write-Host ("[{0}] {1}" -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'), $Message)
}

if (-not (Test-Path -LiteralPath $configPath)) { throw "Missing config: $configPath" }
if (-not (Test-Path -LiteralPath $promptPath)) { throw "Missing prompt: $promptPath" }

$config = Get-Content -LiteralPath $configPath -Raw -Encoding utf8 | ConvertFrom-Json
if ($DryRun) {
    Write-HeartbeatMessage "Dry run only. Would invoke Codex in: $root"
    Write-HeartbeatMessage "Enabled: $($config.enabled); sandbox: $($config.execution.sandbox); network polling: $($config.network.poll_eigenflux)"
    exit 0
}

if (-not $config.enabled) {
    Write-HeartbeatMessage 'Heartbeat is disabled by hooks/du-hourly.config.json. Nothing was run.'
    exit 0
}

New-Item -ItemType Directory -Path $runsDir -Force | Out-Null

if (Test-Path -LiteralPath $lockPath) {
    $age = (Get-Date) - (Get-Item -LiteralPath $lockPath).LastWriteTime
    if ($age.TotalHours -lt 2) {
        Write-HeartbeatMessage "Another heartbeat lock is active ($([Math]::Round($age.TotalMinutes, 1)) minutes old). Exiting."
        exit 0
    }
    Remove-Item -LiteralPath $lockPath -Force
    Write-HeartbeatMessage 'Removed stale heartbeat lock older than two hours.'
}

$lock = $null
try {
    $lock = [System.IO.File]::Open($lockPath, [System.IO.FileMode]::CreateNew, [System.IO.FileAccess]::Write, [System.IO.FileShare]::None)
    $stamp = Get-Date -Format 'yyyy-MM-dd_HH-mm-ss'
    $outputPath = Join-Path $runsDir ("$stamp.md")

    if (-not $env:HOME) { $env:HOME = [Environment]::GetFolderPath('UserProfile') }
    if (-not $env:CODEX_HOME) { $env:CODEX_HOME = Join-Path $env:HOME '.codex' }

    $codex = (Get-Command 'codex' -ErrorAction Stop).Source
    $prompt = Get-Content -LiteralPath $promptPath -Raw -Encoding utf8
    $arguments = @(
        'exec',
        '--approve-for-me',
        '--sandbox', $config.execution.sandbox,
        '-C', $root,
        '--output-last-message', $outputPath,
        '-'
    )

    Write-HeartbeatMessage "Starting Codex hourly heartbeat. Output: $outputPath"
    $prompt | & $codex @arguments
    if ($LASTEXITCODE -ne 0) { throw "Codex exited with code $LASTEXITCODE" }
    Write-HeartbeatMessage 'Heartbeat completed successfully.'
}
catch {
    Write-HeartbeatMessage ("Heartbeat failed: " + $_.Exception.Message)
    throw
}
finally {
    if ($lock) { $lock.Dispose() }
    if (Test-Path -LiteralPath $lockPath) { Remove-Item -LiteralPath $lockPath -Force -ErrorAction SilentlyContinue }
}
