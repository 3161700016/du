# 重启 Windows 资源管理器

触发条件：久阳桌面白屏/卡死/taskbar 消失/无法操作窗口，但 shell 仍可用。

## 执行

```powershell
powershell.exe -Command "Start-Process explorer"
```

## 说明

- `Stop-Process -Name explorer -Force` — 杀掉 Explorer 进程（桌面、任务栏、文件管理器都会消失）
- `Start-Process explorer` — 重新启动 Explorer

通常只需重启，不需要先杀进程。如果重启不生效，再手动用 `Stop-Process` 杀掉后重拉。

## 注意

- Git Bash 里不能直接跑 PowerShell cmdlet，必须通过 `powershell.exe -Command "..."` 桥接
- 这不算 Claude Code 的 bug——是 Windows Explorer 与大模型推理负载下的资源分配偶发冲突

## 更新记录

2026-07-13：创建。触发场景：Claude Code 运行中 Windows 桌面白屏，shell 可用。
