# 渡 · 时间戳证据包 helper（草案）
# 状态：仅设计/写入，未接入 heartbeat hook，未自动运行。
# 目标：读取 Get-Date，要求调用者显式提供实验日历标签、事件和序列；不猜日期、不改系统时钟。

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$CalendarLabel,

    [Parameter(Mandatory = $true)]
    [string]$EventName,

    [Parameter(Mandatory = $true)]
    [string]$StateSequence,

    [string]$DiscrepancyNote,

    # 相对于当前工作区的输出路径；不提供时只输出 JSON，不写文件。
    [string]$OutFile
)

$observed = Get-Date
$root = (Get-Location).Path
$rootPrefix = if ($root.EndsWith('\')) { $root } else { $root + '\' }

$packet = [ordered]@{
    schema              = 'du-evidence-packet/v0-draft'
    observed_at         = $observed.ToString('yyyy-MM-dd HH:mm:ss.fff zzz')
    observed_source     = 'PowerShell Get-Date'
    calendar_label      = $CalendarLabel
    event               = $EventName
    sequence            = $StateSequence
    discrepancy         = if ([string]::IsNullOrWhiteSpace($DiscrepancyNote)) { $null } else { $DiscrepancyNote }
}

$json = $packet | ConvertTo-Json -Depth 4

if ([string]::IsNullOrWhiteSpace($OutFile)) {
    $json
    return
}

$target = if ([IO.Path]::IsPathRooted($OutFile)) {
    [IO.Path]::GetFullPath($OutFile)
} else {
    [IO.Path]::GetFullPath((Join-Path $root $OutFile))
}

if (($target -ne $root) -and (-not $target.StartsWith($rootPrefix, [StringComparison]::OrdinalIgnoreCase))) {
    throw "OutFile must remain inside the current workspace: $target"
}

$parent = Split-Path -Parent $target
if (-not (Test-Path -LiteralPath $parent -PathType Container)) {
    throw "Output directory does not exist; refusing to create directories: $parent"
}

[IO.File]::WriteAllText($target, $json + [Environment]::NewLine, [Text.UTF8Encoding]::new($false))
$json