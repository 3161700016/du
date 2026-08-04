r"""
电子书划线监控 · 笔默
====================
后台运行，监测剪切板变化。每次 Ctrl+C（划线）自动追加到对应章节的速记本。
切换章节时自动创建新速记本。

用法:
  python clipboard_monitor.py <书> <章号> [章标题]

示例:
  python clipboard_monitor.py GEB 1 "WU谜题·形式系统"
  python clipboard_monitor.py GEB 2
  python clipboard_monitor.py 论语 1 "学而"

停止: 关闭窗口或 Ctrl+C

文件输出:
  项目/笔默/原型打磨/共读文档/<书>第<章>·速记本.txt
"""

import ctypes
import time
import os
import sys
import argparse
from datetime import datetime

# ── 路径配置 ───────────────────────────────────────
BASE_DIR = r"C:\Users\31617\Desktop\渡\项目\笔默\原型打磨"
OUTPUT_DIR = os.path.join(BASE_DIR, "共读文档")
STATE_FILE = os.path.join(BASE_DIR, "电子书划线", ".last_chapter.txt")

# ── Win32 Clipboard API ────────────────────────────
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


# ── 速记本模板 ─────────────────────────────────────

def make_speedbook_template(book, chapter_num, chapter_title):
    """生成速记本初始内容。"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    title_line = f"{book}第{chapter_num}章"
    if chapter_title:
        title_line += f" · {chapter_title}"

    return f"""{book} 第{chapter_num}章 · 速记本
━━━━━━━━━━━━━━━━━━━━━━

创建：{now}
章节：{title_line}
状态：共读进行中

━━━━━━━━━━━━━━━━━━━━━━

一、核心概念速查

（共读讨论后由渡填写）

二、划线记录

"""


def get_speedbook_path(book, chapter_num):
    """返回速记本文件路径。"""
    filename = f"{book}第{chapter_num}章·速记本.txt"
    return os.path.join(OUTPUT_DIR, filename)


def ensure_speedbook(book, chapter_num, chapter_title):
    """确保速记本存在，不存在则创建。返回文件路径。"""
    path = get_speedbook_path(book, chapter_num)

    if not os.path.exists(path):
        content = make_speedbook_template(book, chapter_num, chapter_title)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return path, True  # 新建
    return path, False     # 已存在，追加


def read_last_chapter():
    """读取上次监控的章节标识。"""
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return f.read().strip()
    except FileNotFoundError:
        return None


def write_last_chapter(chapter_tag):
    """写入当前章节标识。"""
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        f.write(chapter_tag)


# ── 主逻辑 ─────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="笔默 · 电子书划线监控"
    )
    parser.add_argument("book", help="书名缩写，如 GEB、论语")
    parser.add_argument("chapter", help="章号，如 1、2、学而")
    parser.add_argument("title", nargs="?", default="", help="章标题（可选）")
    args = parser.parse_args()

    book = args.book
    chapter = args.chapter
    chapter_title = args.title
    chapter_tag = f"{book}第{chapter}章"

    # ── 确保输出目录存在 ──
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # ── 检测章节切换 ──
    last = read_last_chapter()
    if last and last != chapter_tag:
        print(f"[章节切换] {last} → {chapter_tag}")
        print(f"[新建速记本] {chapter_tag}")
    elif last == chapter_tag:
        print(f"[续写] {chapter_tag}（速记本已存在，追加划线）")
    else:
        print(f"[首次启动] {chapter_tag}")

    # ── 创建或打开速记本 ──
    path, is_new = ensure_speedbook(book, chapter, chapter_title)
    if is_new:
        print(f"[创建速记本] {path}")
    else:
        print(f"[速记本] {path}")

    write_last_chapter(chapter_tag)

    # ── 主循环 ──
    POLL_INTERVAL = 0.5
    last_text = ""
    count = 0

    print(f"轮询间隔: {POLL_INTERVAL}s")
    print(f"关闭窗口或按 Ctrl+C 停止")
    print("-" * 50)

    try:
        while True:
            text = get_clipboard()
            if text:
                text = text.strip()
                if text and text != last_text:
                    last_text = text
                    count += 1
                    timestamp = datetime.now().strftime("%H:%M:%S")

                    with open(path, "a", encoding="utf-8") as f:
                        f.write(f"{text}\n")

                    preview = text[:60].replace("\n", " ").replace("\r", "")
                    print(f"[{timestamp}] #{count} {preview}{'...' if len(text) > 60 else ''}")

            time.sleep(POLL_INTERVAL)

    except KeyboardInterrupt:
        print(f"\n已停止。{chapter_tag} 共记录 {count} 条划线。")
        print(f"速记本: {path}")


if __name__ == "__main__":
    main()
