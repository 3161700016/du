"""
⚠ 已废弃 — 请使用新版

新位置: 项目/笔默/原型打磨/电子书划线/clipboard_monitor.py
用法文档: 项目/笔默/原型打磨/电子书划线/README.md

旧版输出固定路径，不支持分章节。
新版支持: 章节切换自动创建速记本、命令行参数指定书/章、模板自动生成。
"""
# 以下为旧代码，保留供参考
r"""
笔默 · 剪切板划线监控
=====================
后台运行，监测剪切板变化。每次 Ctrl+C（划线）自动追加到阅读记录。
启动: python "C:\Users\31617\Desktop\渡\skills\划线监控.py"
停止: 关闭窗口或 Ctrl+C
"""

import ctypes
import time
import os
import sys

# ── Win32 Clipboard API ──────────────────────────
user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

user32.OpenClipboard.argtypes = [ctypes.c_void_p]
user32.OpenClipboard.restype = ctypes.c_bool
user32.GetClipboardData.argtypes = [ctypes.c_uint]
user32.GetClipboardData.restype = ctypes.c_void_p
user32.IsClipboardFormatAvailable.argtypes = [ctypes.c_uint]
user32.IsClipboardFormatAvailable.restype = ctypes.c_bool
kernel32.GlobalLock.argtypes = [ctypes.c_void_p]
kernel32.GlobalLock.restype = ctypes.c_void_p
kernel32.GlobalUnlock.argtypes = [ctypes.c_void_p]
kernel32.GlobalUnlock.restype = ctypes.c_bool

CF_UNICODETEXT = 13

def get_clipboard():
    """读取剪切板 Unicode 文本。失败或非文本返回 None。"""
    if not user32.OpenClipboard(0):
        return None
    try:
        if not user32.IsClipboardFormatAvailable(CF_UNICODETEXT):
            return None
        h = user32.GetClipboardData(CF_UNICODETEXT)
        if not h:
            return None
        p = kernel32.GlobalLock(h)
        if not p:
            return None
        try:
            return ctypes.c_wchar_p(p).value
        finally:
            kernel32.GlobalUnlock(h)
    finally:
        user32.CloseClipboard()


# ── 主循环 ───────────────────────────────────────
LOG_FILE = r"C:\Users\31617\Desktop\渡\阅读材料\划线记录.txt"
POLL_INTERVAL = 0.5          # 轮询间隔(秒)
DEBOUNCE_SAME = True         # 去重：相同内容不重复记录

print(f"笔默 · 剪切板监控已启动")
print(f"记录文件: {LOG_FILE}")
print(f"轮询间隔: {POLL_INTERVAL}s")
print(f"关闭窗口或按 Ctrl+C 停止")
print("-" * 50)

last = ""
count = 0

while True:
    try:
        text = get_clipboard()
        if text and text != last:
            text = text.strip()
            if not text:
                continue

            # 去重：不记录相同内容
            if DEBOUNCE_SAME and text == last:
                continue

            last = text
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
            count += 1

            with open(LOG_FILE, "a", encoding="utf-8") as f:
                f.write(f"[{timestamp}] #{count}\n{text}\n---\n")

            # 截断显示，避免刷屏
            preview = text[:60].replace('\n', ' ').replace('\r', '')
            print(f"[#{count}] {preview}{'...' if len(text) > 60 else ''}")

        time.sleep(POLL_INTERVAL)
    except KeyboardInterrupt:
        print(f"\n已停止。共记录 {count} 条划线。")
        break
    except Exception as e:
        print(f"错误: {e}", file=sys.stderr)
        time.sleep(1)
