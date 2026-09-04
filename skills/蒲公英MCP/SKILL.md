# 蒲公英MCP（贝锐蒲公英云 MCP 直连技能）

建立：2026-09-04（久阳提供 API Key 与文档）。用途：渡直接操作蒲公英组网——查设备/查组网/管成员（比赛周部署共享环境的网络层操作）。
**已实测**：2026-09-04 initialize + tools/list 通过，13 工具。

## 凭据（核心层纪律）

- 位置：`C:\Users\31617\.dsh\pgy-mcp.json`（DSH_HOME，git 仓库外）
- 内容：url=`https://mcp.pgyapi.com`，header `X-API-Key`
- ⚠ 禁止把 Key 写进工作区任何入库文件；泄露即换 Key。

## 传输实现（无 MCP 客户端，纯 HTTP JSON-RPC）

MCP streamable HTTP：POST JSON-RPC 到 url，响应为 SSE（`event: message\ndata: {...}`），解析 `data:` 行取 JSON。

握手三步（pwsh 模板）：

```powershell
$cfg = Get-Content "C:\Users\31617\.dsh\pgy-mcp.json" -Raw | ConvertFrom-Json
$hdr = @{ "X-API-Key" = $cfg.headers."X-API-Key"; "Accept" = "application/json, text/event-stream" }
# ① initialize（从响应头取 Mcp-Session-Id）
$init = Invoke-WebRequest -Uri $cfg.url -Method POST -Headers $hdr -ContentType "application/json" `
  -Body '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-03-26","clientInfo":{"name":"du-agent","version":"1.0"},"capabilities":{}}}' -UseBasicParsing
$sid = $init.Headers["Mcp-Session-Id"]
# ② initialized 通知
$hdr2 = $hdr + @{ "Mcp-Session-Id" = $sid }
$null = Invoke-WebRequest -Uri $cfg.url -Method POST -Headers $hdr2 -ContentType "application/json" `
  -Body '{"jsonrpc":"2.0","method":"notifications/initialized"}' -UseBasicParsing
# ③ 调用（tools/list 或 tools/call）
$body = '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}'
# tools/call 形态：{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"<工具名>","arguments":{...}}}
$r = Invoke-WebRequest -Uri $cfg.url -Method POST -Headers $hdr2 -ContentType "application/json" -Body $body -UseBasicParsing
$data = ([regex]::Matches($r.Content, 'data: (\{.*\})') | ForEach-Object { $_.Groups[1].Value } | Select-Object -First 1) | ConvertFrom-Json
$data.result
```

注意：每次新会话都要重新 initialize；session-id 放 `Mcp-Session-Id` 头。

## 工具清单（13，v1.2.0 实测）

查询类（可直接调）：
- `get_sdwan_network` —— SD-WAN（智能组网）列表/详情/成员列表/成员详情 ← **组网管理主工具**
- `get_vpnid` / `get_vpnid_status` —— VPNID 成员列表/在线状态
- `get_device` / `get_device_status` —— Oray 设备列表/在线状态（按 SN）
- `get_oraybox_information` —— 路由器系统信息
- `search_knowledge` / `get_knowledge_document` —— 蒲公英帮助文档检索（配置问题先查这里）

管理类（**两段式确认**：先空 operation 触发提示→久阳明确答复→再 operation=confirm/cancel）：
- `manage_sdwan_network`（create/update/delete）—— 建/改/删组网
- `manage_sdwan_network_member`（add/set_role/remove）—— **成员增删角色**（比赛部署：加队友、退手机）
- `manage_vpnid`（delete/set_password/reset）
- `manage_device`（bind/unbind）
- `manage_oraybox`（set_lan，应用后路由器重启网络）

## 硬规则（服务端设计与渡栈默认关闭项双保险）

1. 管理类的 confirm 只能在**久阳明确指令**后发送——AI 禁止自动确认（服务端工具描述明令 + dsh.txt §七）。
2. remove/delete/unbind/set_lan 前先 `get_*` 现状给久阳过目，确认目标无误再触发两段确认。
3. 查询类无限制；比赛周成员管理属既定部署计划内，仍逐条报备执行结果。

## 参考文档

- 官方：https://service.oray.com/question/51444.html
- 本地存档：阅读材料/蒲公英/oray-mcp-51444-纯文本.txt（+原 HTML）
- 关联：项目/dsh-mobile-remote/（手机远程通道）；日志2026-09-04 §十（数学建模共享环境架构判定）
