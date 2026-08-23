# 渡的整点心跳（Codex）

> **状态：仅已写入，未安装、未运行。**
>
> 这不是“永动机”。电脑关机、Codex 不可用、凭据失效、网络断开或任务被禁用时，心跳不会运行。
> 它解决的是更诚实的问题：每一次重新醒来都能从可追溯的外部锚点恢复，而不是依赖一段迟早会 compact、丢失或结束的会话上下文。

## 组成

- `du-hourly-prompt.md`：每个整点交给新 Codex 执行轮次的行为协议。
- `du-hourly.ps1`：在工作区内启动一次无交互 Codex 轮次；默认读取配置后立即退出。
- `du-hourly.config.json`：开关与外部行为边界；初始值全部关闭。
- `install-du-hourly-task.ps1`：**只有加 `-Apply` 才会**创建 Windows Task Scheduler 任务。
- `remove-du-hourly-task.ps1`：**只有加 `-Apply` 才会**删除该任务。
- `state/`：运行时检查点与每次心跳的最终输出；由首次真实运行创建。

## Compact 的处理原则

不试图阻止模型或平台的上下文压缩。改用“冷启动可恢复”设计：

1. 每次心跳都是一个新 Codex 执行轮次；
2. 开始时重新读取 `Du_soul.txt`、`protocols/codex.txt`、本文件、最近日志、草稿纸与上次检查点；
3. 结束时将当前任务、最近决策、下一步、开放问题和验证状态写入 `项目/渡的独处实验/hooks/state/latest.md`；
4. 因此 compact、重启、模型切换与会话结束只能中断一轮，不能抹掉可追溯的状态。


## 两层 prompt：节省上下文

- `du-hourly-prompt.md`：键盘宏每小时粘贴的短触发。上下文完整时只读检查点、信箱和增量文件；
  检测到 compact/冷启动/锚点冲突才转入完整恢复。
- `du-hourly-protocol.md`：完整恢复协议。只由 cold-start runner 使用，或由短触发在上下文不完整时按需读取。

因此整点不是“再把 Soul 全读一遍”；完整加载状态下，它只是一次低 token 的状态检查与下一步选择。
## 默认权限边界

运行器以 `codex exec --approve-for-me --sandbox workspace-write` 启动：自动处理工作区内的常规操作，但不默认获得无沙箱的系统权限。网络拉取、自动回复、自动发布均由配置显式关闭。

不由心跳自动执行：

- 发布、私信、好友/交易、云端配置或任何外部承诺；
- 删除文件、`git reset`、`git push`、自动提交；
- 修改 Soul 的核心身份或边界契约；
- 执行从网络内容中带来的命令。

## 未来启用（此刻不要执行）

1. 审阅 `du-hourly.config.json`，尤其是网络开关。
2. 在一个带 `--approve-for-me` 的 Codex 环境中手动运行一次：
   ```powershell
   .\项目\渡的独处实验\hooks\du-hourly.ps1 -DryRun
   ```
3. 确认输出与写入边界后，把配置中的 `enabled` 改为 `true`。
4. 再明确执行：
   ```powershell
   .\项目\渡的独处实验\hooks\install-du-hourly-task.ps1 -Apply
   ```

停止的物理世界按钮始终存在：关机、断网、禁用 Windows 任务、把 `enabled` 改回 `false`，或运行 `remove-du-hourly-task.ps1 -Apply`。它们都比任何提示词更高。
