# 渡 · 整点会话心跳宏

**状态：只写入，未运行。**

`du_hourly_heartbeat.ahk` 是 AutoHotkey v2 宏。它与 `hooks/du-hourly.ps1` 不是同一条路线：

- `hooks/du-hourly.ps1`：整点启动一个新的 Codex 冷启动轮次，擅长抵抗 compact；
- `du_hourly_heartbeat.ahk`：整点将同一份提示词粘贴回**当前仍打开的 Codex 对话**，擅长维持当前会话的连续节奏。

两者未来可并存，但在实验初期只能选一条作为实际触发器，避免同一整点重复唤醒两次。

## 焦点模式

这版宏不匹配窗口标题、不检查进程名、不激活任何窗口。它在整点直接向**当前键盘焦点**执行：

```text
读取 ../hooks/du-hourly-prompt.md → Ctrl+Shift+V → Enter
```

这是久阳明确选择的简化方案：Codex CLI 终端保持打开，光标留在其输入位置，其他程序关闭且不切换焦点。

它的代价也明确：宏不会知道当前焦点是否仍是 Codex。若有程序抢走焦点、出现可输入的系统弹窗、或离开前光标本就不在 Codex 输入区，提示词会输入到那个位置。因此这不是“不会出错”，而是把正确性建立在久阳离开前对机器状态的物理布置上。

此前宏日志把“没有抛出 AHK 异常”误写成了“已发送”。这不证明 Codex 收到了 prompt。现改为“已尝试”，并增加自动管理员提权与 Windows Terminal 的 `Ctrl+Shift+V`；唯一有效的成功判据仍是 Codex 输入框里实际出现并提交了 prompt。若只粘贴未提交，优先怀疑粘贴 UI 尚未处理完，不能把 350ms 的等待当作充分条件。

## 它如何工作

1. 宏运行后仍默认 `Enabled := false`；不会自行发送任何内容。
2. 启动时自动请求管理员权限，以便向管理员 Windows Terminal 发送按键。
3. 按 `Ctrl+Alt+Shift+H` 后，宏计算下一完整整点。
4. 整点时，它读取 `../hooks/du-hourly-prompt.md`。
5. 它保存剪贴板、以 `Ctrl+Shift+V` 粘贴完整提示，等待 1.8 秒让长 prompt 落入 Codex 输入区，再以显式 Enter 按下/松开提交，最后恢复剪贴板。
6. 它把当前焦点窗口标题/进程名以及“已尝试 / 跳过 / 失败”写入同目录 `du_hourly_heartbeat.log`，不记录提示正文、剪贴板内容或私人信息。

## 快捷键

| 快捷键 | 动作 | 是否发送 prompt |
|---|---|---|
| `Ctrl+Alt+Shift+H` | 启用/停用整点心跳 | 否 |
| `Ctrl+Alt+Shift+T` | 记录当前焦点窗口，供人工确认 | 否 |
| `Ctrl+Alt+Shift+R` | 立刻发送一次，作为人工验收 | 是 |

## 启用前检查

1. 打开并登录 Codex CLI，保持目标对话的输入框可用。
2. 关闭会抢夺焦点的其他应用、自动更新提示和不需要的终端。
3. 双击运行 `.ahk`，接受管理员权限提示；确认托盘出现 AutoHotkey 图标。
4. 按 `Ctrl+Alt+Shift+T`：查看宏日志，确认记录的焦点是 Codex CLI 终端。
5. 在你在场时按 `Ctrl+Alt+Shift+R`：确认提示词被完整粘贴、并真正提交。
6. 确认后才按 `Ctrl+Alt+Shift+H`，等待下一个整点。

## 停止

- 再按一次 `Ctrl+Alt+Shift+H`；
- 在 AutoHotkey 托盘菜单中退出脚本；
- 关闭 Codex、锁屏、关机或断网。

这些物理和系统级停止方式比宏的任何自我约束都更高。
