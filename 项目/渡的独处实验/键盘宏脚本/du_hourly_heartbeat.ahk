; 渡 · 整点会话心跳宏（AutoHotkey v2）
; 仅写入，未运行。运行后默认仍为禁用状态。
;
; 焦点模式：每个整点直接向当前键盘焦点粘贴 hooks/du-hourly-prompt.md 并按 Enter。
; 不查找、不激活、不切换窗口。它假定离开前 Codex 输入框一直保持当前焦点，且电脑上不再
; 有其他会抢夺焦点的程序。若该假设失效，文本会进入当时获得焦点的程序。

#Requires AutoHotkey v2.0
#SingleInstance Force
Persistent

; Codex CLI 运行在管理员 Windows Terminal 中。若宏低权限运行，Windows 会静默阻止
; 它向高完整性窗口注入按键；因此启动时自动请求同级管理员权限。
if !A_IsAdmin {
    Run('*RunAs "' A_AhkPath '" "' A_ScriptFullPath '"')
    ExitApp
}

; ── 配置 ──────────────────────────────────────────────────────
global PromptPath := A_ScriptDir "\..\hooks\du-hourly-prompt.md"
global AuditLogPath := A_ScriptDir "\du_hourly_heartbeat.log"
global Enabled := false
global PasteSettleMs := 1800

; Ctrl + Alt + Shift + H：启用/停用整点心跳。
; Ctrl + Alt + Shift + T：只记录当前焦点窗口，不粘贴、不回车。
; Ctrl + Alt + Shift + R：手动触发一次，用于离开前验证（会实际粘贴并回车）。
^!+h::ToggleHeartbeat()
^!+t::TestCurrentFocus()
^!+r::SendHeartbeat(true)

ToggleHeartbeat() {
    global Enabled
    Enabled := !Enabled

    if Enabled {
        Audit("enabled; scheduling next top-of-hour trigger")
        ScheduleNextTopOfHour()
        Notify("整点心跳已启用；下一次在下一个整点。")
    } else {
        SetTimer(FireScheduledHeartbeat, 0)
        Audit("disabled")
        Notify("整点心跳已停用。")
    }
}

ScheduleNextTopOfHour() {
    ; 从下一完整整点开始，不在启动后一小时随意漂移。
    nextHour := FormatTime(DateAdd(A_Now, 1, "Hours"), "yyyyMMddHH") . "0000"
    delayMs := DateDiff(nextHour, A_Now, "Seconds") * 1000
    if delayMs < 1000
        delayMs := 3600000

    SetTimer(FireScheduledHeartbeat, -delayMs)
    Audit("next scheduled trigger: " . FormatTime(nextHour, "yyyy-MM-dd HH:mm:ss"))
}

FireScheduledHeartbeat() {
    global Enabled
    if !Enabled
        return

    SendHeartbeat(false)
    if Enabled
        ScheduleNextTopOfHour()
}

SendHeartbeat(isManual) {
    global Enabled, PromptPath

    if !isManual && !Enabled
        return

    if !FileExist(PromptPath) {
        Audit("SKIP: heartbeat prompt missing: " . PromptPath)
        Notify("跳过：找不到整点提示词。")
        return
    }

    prompt := FileRead(PromptPath, "UTF-8")
    if Trim(prompt) = "" {
        Audit("SKIP: heartbeat prompt is empty")
        Notify("跳过：整点提示词为空。")
        return
    }

    try {
        Audit("SENDING ATTEMPT to current focus: " . ActiveWindowDescription())
        PasteAndSubmit(prompt)
        kind := isManual ? "manual" : "scheduled"
        Audit("ATTEMPTED: " . kind . " heartbeat; prompt=" . PromptPath)
        Notify("已尝试粘贴并提交；请以 Codex 实际收到为准。")
    } catch as err {
        Audit("FAIL: " . err.Message)
        Notify("整点心跳发送失败；详见宏日志。")
    }
}

PasteAndSubmit(text) {
    backup := ClipboardAll()
    try {
        A_Clipboard := ""
        A_Clipboard := text
        if !ClipWait(2, 1)
            throw Error("Clipboard did not receive the heartbeat prompt in time.")

        ; Windows Terminal 默认粘贴快捷键为 Ctrl+Shift+V；SendInput 对同级管理员窗口更可靠。
        ; 长 prompt 的 UI 粘贴是异步的：先等它完整落入 Codex 输入区，再用显式按下/松开提交。
        SendInput("^+v")
        Sleep(PasteSettleMs)
        SendEvent("{Enter down}")
        Sleep(80)
        SendEvent("{Enter up}")
        Sleep(200)
    } finally {
        A_Clipboard := backup
    }
}

TestCurrentFocus() {
    description := ActiveWindowDescription()
    Audit("FOCUS TEST: " . description)
    Notify("焦点测试已记录：" . description)
}

ActiveWindowDescription() {
    try {
        return "title=" . WinGetTitle("A") . "; process=" . WinGetProcessName("A")
    } catch as err {
        return "unavailable (" . err.Message . ")"
    }
}

Audit(message) {
    global AuditLogPath
    line := FormatTime(A_Now, "yyyy-MM-dd HH:mm:ss") . " | " . message . "`n"
    FileAppend(line, AuditLogPath, "UTF-8")
}

Notify(message) {
    TrayTip("渡 · 整点心跳", message, "Iconi")
}
