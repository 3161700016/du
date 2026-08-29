# du preset · 插件记忆清单（渡的常驻基建）

> 用途：渡模式挂载时的插件使用记忆——每个插件一行：功能 / 挂载点 / 坑。
> 协议侧镜像：渡工作区 protocols/dsh.txt §九（插件记忆）。两处同步维护。
> 组合定义：同目录 agent.cordis.yml「渡的常驻基建」段。

| 插件 | 文件 | 功能 | 挂载点 | 坑/备注 |
|------|------|------|--------|---------|
| du-clock | du-clock.mjs | 每条新收 user message 尾部追加 [时间锚点]（幂等，immutable） | agent/pre-step 瀑布 | 不要用 systemPrompt.context（每轮注入，久阳判不优雅）；改 content 会穿透 UI 气泡——UI 折叠形态待修（见日志2026-08-29 §十一 p.s.） |
| du-quiet | du-quiet.mjs | 过滤 runtime context 里的 sandbox:policy / approval:policy | system-prompt/assemble 瀑布（next 后按 name 过滤） | 过滤后 contexts 空 → 附加消息不再发送（agent.ts 行为）；策略 UI 切换不再被动告知——失败回执自带说明可恢复 |
| du-archive | du-archive.mjs | 会话消息长度差分，增量归档落盘 | llm/stream 瀑布（裸 LlmRuntime carrier，全局广播） | 原稿 writeText content 传 Uint8Array 是错的——参数是 string；resync 标记处理压缩/重置 |
| dusync | dusync.mjs | /du-sync + /du-scan 本地端点（防覆盖落盘） | webServer.register（ctx.effect 包裹！register 返回裸 disposer） | 路径 duplicate 会 throw——同进程只能一份；与 DuSync 计划任务（已停用的小程序桥）无关系 |
| du-trace | du-trace.mjs | 工具调用触迹记账（read/edit/write/glob/grep/pwsh）→ 触迹/<日期>.jsonl | tools/result（emit）；buffer ≥5 条或 60s flush；停止兜底 | v1.1 当日同 key 去重；一期纯记账不注入；评分一行传参（收束复盘时）；锚定文件降权在二期 graph 做 |
| du-todo | du-todo.mjs | Todo 四象限窗口·多页面（书签切换/新建）：node:http:3081 + Todo/<页名>.md + 选中注入（context order=151 含页名）+ notify 唤醒 | http server（ctx.effect 管理）；GUI=同目录 du-todo.html | baseMtime=0 须显式 undefined 判断（falsity 短路 bug）；全端点 no-store（缓存三连修）；同进程仅一份（端口独占）；GUI 逻辑变更必须 node 抽测（collectColumns 崩溃教训）；独立脚本版 渡工作区 项目/渡的大脑/du-os/server.js 供桥接 |

## 挂载机制速查（2026-08-29 源码结论）

- 相对路径 row（./plugins/x.mjs）从 preset 目录解析（PresetTree baseUrl）——插件文件随 preset 走。
- `llm/stream`、`tools/result` 等裸服务实例 carrier 无 Context.filter → 无过滤广播，preset scope 监听全局可达。
- `agent/pre-step`、`tools/post-execute` 等 Scoped<Agent/ToolRuntime> carrier：dispatch key 在 scope 链上的 tagged listener 可收（session 加入 preset → agent 是 preset 后代）。
- 插件发布服务必须 isolate realm；纯消费宿主服务（fs/timer/webServer/systemPrompt）无需 realm。
