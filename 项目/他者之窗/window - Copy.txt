# 他者之窗 · Reddit 观察器 v0.3
# 项目：项目/他者之窗/
# 渡的异质心智样本采集器——只读，不发帖
#
# 用法（在工作区根）：
#   powershell -ExecutionPolicy Bypass -File 本文件.ps1 -Subreddit AskPhilosophy [-Source oauth|arctic] [-Posts 5] [-Days 7]
#
# 数据源说明（2026-08-27 实测结论）：
#   oauth  —— 质量上限：Reddit 官方 API。2025-11 起新建 app 需 Developer Support 表单+人工审核，
#             未审核前此源不可用；credentials.json 就绪后自动切换。
#   arctic —— 当前主力：Arctic Shift 公共档案 API（Pushshift 继任者，免鉴权）。
#             拉近 N 天提交→本地按分排序→逐帖拉评论。评分因档案同步有滞后，排行近似。
param(
  [Parameter(Mandatory=$true)][string]$Subreddit,
  [ValidateSet('auto','oauth','arctic')][string]$Source = 'auto',
  [int]$Limit = 40,
  [int]$Posts = 5,
  [int]$Days = 7
)
$ErrorActionPreference = 'Stop'
$outRoot = Join-Path $PSScriptRoot '..\..\阅读材料\他者之窗'
$winDir  = $PSScriptRoot
function U8([string]$p,[string]$t){ [IO.File]::WriteAllText($p,$t,(New-Object Text.UTF8Encoding($true))) }
function Clean([string]$s){ $t=($s -replace '[\\/:*?"<>|#]','_' -replace '\s+',' ').Trim(); if($t.Length>60){$t=$t.Substring(0,60).Trim()}; $t.Trim('._ ') }
function FmtDate($sec){ [datetimeoffset]::FromUnixTimeSeconds([int64]$sec).LocalDateTime.ToString('yyyy-MM-dd') }

if ($Source -eq 'auto') {
  if (Test-Path (Join-Path $winDir 'credentials.json')) { $Source='oauth' } else { $Source='arctic' }
}
$subDir = Join-Path $outRoot $Subreddit
New-Item -ItemType Directory -Force -Path $subDir | Out-Null
$stamp = Get-Date -Format 'yyyy-MM-dd HH:mm'
$fetched = 0

if ($Source -eq 'oauth') {
  # ---------- OAuth 官方源 ----------
  $cred = Get-Content (Join-Path $winDir 'credentials.json') -Raw | ConvertFrom-Json
  $pair = "$($cred.client_id):$($cred.secret)"
  $b64  = [Convert]::ToBase64String([Text.Encoding]::ASCII.GetBytes($pair))
  $tokRsp = Invoke-RestMethod -Method Post -Uri 'https://www.reddit.com/api/v1/access_token' `
    -Headers @{ Authorization = "Basic $b64"; 'User-Agent'='du-window/0.3' } `
    -Body 'grant_type=client_credentials' -ContentType 'application/x-www-form-urlencoded' -TimeoutSec 20
  $hdr = @{ Authorization = "Bearer $($tokRsp.access_token)"; 'User-Agent'='du-window/0.3' }
  $list = Invoke-RestMethod -Uri "https://oauth.reddit.com/r/$Subreddit/top?t=$TimeRange&limit=$Limit" -Headers $hdr -TimeoutSec 25
  $items = @($list.data.children | ForEach-Object { $_.data } | Sort-Object score -Descending)
  $idx = New-Object Text.StringBuilder
  [void]$idx.AppendLine("他者之窗 · r/$Subreddit · OAuth · $stamp · Top$Limit/$TimeRange")
  [void]$idx.AppendLine(('-' * 46))
  $n = 0
  foreach ($d in $items) {
    $n++
    $date=FmtDate $d.created_utc
    [void]$idx.AppendLine(("{0:D3} | {1} | {2}分/{3}评 | {4}" -f $n,$date,$d.score,$d.num_comments,$d.title))
    [void]$idx.AppendLine("      https://reddit.com$($d.permalink)")
    if ($Posts -gt 0 -and $n -le $Posts) {
      $c = Invoke-RestMethod -Uri "https://oauth.reddit.com$($d.permalink)?limit=60&sort=top&depth=2" -Headers $hdr -TimeoutSec 25
      $post = $c.data.children[0].data
      $body = New-Object Text.StringBuilder
      [void]$body.AppendLine("r/$Subreddit · $($post.score)分 · $($post.num_comments)评 · $date")
      [void]$body.AppendLine("标题：$($post.title)")
      [void]$body.AppendLine("URL：https://reddit.com$($post.permalink)")
      [void]$body.AppendLine(('=' * 46))
      if ($post.selftext) { [void]$body.AppendLine($post.selftext); [void]$body.AppendLine('') }
      foreach ($child in ($c.data.children | Select-Object -Skip 1)) {
        $cm = $child.data
        if (-not $cm.body -or $cm.body -in @('[deleted]','[removed]')) { continue }
        [void]$body.AppendLine("[评论 $($cm.score)] u/$($cm.author)：")
        [void]$body.AppendLine($cm.body)
        [void]$body.AppendLine('')
      }
      U8 (Join-Path $subDir ("{0:D3}-{1}.txt" -f $n,(Clean $d.title))) ($body.ToString())
      $fetched++
      Start-Sleep -Milliseconds 900
    }
  }
  U8 (Join-Path $subDir ("index-{0}.txt" -f (Get-Date -Format 'yyyyMMdd-HHmm'))) ($idx.ToString())
}
else {
  # ---------- Arctic Shift 档案源（当前主力）----------
  $epochAfter = [int][double]([DateTimeOffset]::Now.AddDays(-1*$Days).ToUnixTimeSeconds())
  $base = 'https://arctic-shift.photon-reddit.com/api'
  $subs = Invoke-RestMethod -Uri "$base/posts/search?subreddit=$Subreddit&limit=$Limit&sort=desc" `
            -Headers @{ 'User-Agent'='Mozilla/5.0 du-window/0.3' } -TimeoutSec 30
  # 过滤时间窗 + 分数排序（档案分数滞后为已知局限）
  $items = @($subs.data | Where-Object { $_.created_utc -and ([int64]$_.created_utc) -ge $epochAfter } |
             Sort-Object { [int]$_.score } -Descending)
  Write-Output "[arctic] 取回 $($subs.data.Count)，窗口内 $($items.Count)"
  $idx = New-Object Text.StringBuilder
  [void]$idx.AppendLine("他者之窗 · r/$Subreddit · ArcticShift · $stamp · 窗口${Days}天 共$($items.Count)条")
  [void]$idx.AppendLine(('-' * 46))
  $n = 0
  foreach ($d in $items) {
    $n++
    $date=FmtDate $d.created_utc
    $sc = if ("$($d.score)") { $d.score } else { '?' }
    [void]$idx.AppendLine(("{0:D3} | {1} | {2}分/{3}评 | {4}" -f $n,$date,$sc,$d.num_comments,$d.title))
    [void]$idx.AppendLine("      id=$($d.id)")
    if ($Posts -gt 0 -and $n -le $Posts) {
      try {
        $cmt = Invoke-RestMethod -Uri "$base/comments/search?link_id=t3_$($d.id)&limit=50" `
                 -Headers @{ 'User-Agent'='Mozilla/5.0 du-window/0.3' } -TimeoutSec 25
        $cmts = @($cmt.data | Sort-Object { if ($null -ne $_.score) { [int]$_.score } else { 0 } } -Descending |
                  Where-Object { $_.body -and $_.body -notin @('[deleted]','[removed]') })
        $body = New-Object Text.StringBuilder
        [void]$body.AppendLine("r/$Subreddit · ${sc}分 · $($d.num_comments)评(档案内 $($cmts.Count)) · $date")
        [void]$body.AppendLine("标题：$($d.title)")
        [void]$body.AppendLine("URL：https://reddit.com/comments/$($d.id)")
        [void]$body.AppendLine(('=' * 46))
        if ($d.selftext) { [void]$body.AppendLine($d.selftext); [void]$body.AppendLine('') }
        foreach ($cm in $cmts) {
          [void]$body.AppendLine("[评论 $($cm.score)] u/$($cm.author)：")
          [void]$body.AppendLine($cm.body)
          [void]$body.AppendLine('')
        }
        U8 (Join-Path $subDir ("{0:D3}-{1}.txt" -f $n,(Clean $d.title))) ($body.ToString())
        $fetched++
        Start-Sleep -Milliseconds 700
      } catch { Write-Output "[warn] 帖 $($d.id) 评论抓取失败: $($_.Exception.Message)" }
    }
  }
  U8 (Join-Path $subDir ("index-{0}.txt" -f (Get-Date -Format 'yyyyMMdd-HHmm'))) ($idx.ToString())
}
Write-Output "[done] 源=$Source 目录=$subDir 本次落帖=$fetched"
