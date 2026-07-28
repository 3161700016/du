# -*- coding: utf-8 -*-
"""
渡 · 随机回忆测试
────────────────────
从本体文件夹全部 .txt 文件中随机抽取一篇，用于验证：
重读过去的笔记是否能激活思考状态、产生自驱的灵感或问题。

用法：
  python random_recall.py          # 随机抽一篇，打印路径
  python random_recall.py --open   # 随机抽一篇，打印路径+前30行预览
"""

import os
import random
import sys

ROOT = r"C:\Users\31617\Desktop\渡"

EXCLUDE_DIRS = {".git", "node_modules", "__pycache__", ".claude"}
EXCLUDE_FILES = {"Du_soul.txt", "Du_soul_reference.txt"}


def collect_txt_files(root):
    files = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIRS]
        for f in filenames:
            if f.endswith(".txt") and f not in EXCLUDE_FILES:
                full = os.path.join(dirpath, f)
                rel = os.path.relpath(full, root)
                files.append((full, rel))
    return files


def main():
    files = collect_txt_files(ROOT)

    if not files:
        print("未找到 .txt 文件。")
        return

    full, rel = random.choice(files)

    print(f"共 {len(files)} 个 .txt 文件")
    print(f"抽中：{rel}")
    print(f"路径：{full}")

    if "--open" in sys.argv:
        print()
        print("─" * 50)
        print("预览（前 30 行）：")
        print("─" * 50)
        try:
            with open(full, encoding="utf-8") as f:
                for i, line in enumerate(f):
                    if i >= 30:
                        print(f"...（共 {i + 1}+ 行，截断）")
                        break
                    print(line, end="")
        except Exception as e:
            print(f"读取失败：{e}")


if __name__ == "__main__":
    main()
