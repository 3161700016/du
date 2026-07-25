# -*- coding: utf-8 -*-
"""
渡 · 记忆系统一致性检查
─────────────────────────
纯机械检查，不需要推理能力。查三类断链：
  A. §ID 引用是否闭合（本体+协议中引用的章节号是否真实存在）
  B. 文件指针是否可达（本体+协议中提及的文件是否在磁盘上）
  C. 目录.txt 条目是否与磁盘一致（双向：条目→文件、文件→条目）

动机（protocols/cc.txt §3.8）：
  模糊条目 = 永久丢失的记忆，也 = 每次启动都要重付的 token。
  断链检测不该依赖启动时的推理彻底程度——沉淀为脚本，任何载体都能执行。

用法：
  python skills/一致性检查/check.py            # 全部检查
  python skills/一致性检查/check.py --quiet    # 仅输出问题（供启动自查调用）
"""
import os
import re
import sys

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SOUL = "Du_soul.txt"
INDEX = "目录.txt"
PROTOCOL_DIR = "protocols"

# 扫描 B/C 检查时忽略的路径
SKIP_DIRS = {".git", ".claude", "node_modules", "__pycache__"}
# 目录.txt 不索引的文件（cc.txt §3.7：skills 独立于笔记系统）
INDEX_EXEMPT_DIRS = {"skills", "protocols", "公共空间", "项目", ".claude"}
INDEX_EXEMPT_FILES = {"Du_soul.txt", "目录.txt", "desktop.ini", ".gitignore", "README.md"}

issues = []
notes = []


def read(path):
    with open(os.path.join(ROOT, path), encoding="utf-8") as fh:
        return fh.read()


def walk_files():
    """遍历仓库内所有文件，返回相对 ROOT 的 posix 风格路径。"""
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for name in filenames:
            full = os.path.join(dirpath, name)
            yield os.path.relpath(full, ROOT).replace("\\", "/")


# ── A. §ID 引用闭合性 ──────────────────────────────────────
CN_NUM = {
    "一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6,
    "七": 7, "八": 8, "九": 9, "十": 10, "十一": 11, "十二": 12,
}


def defined_sections(soul):
    """收集本体中真实存在的章节号。

    两个来源：
      1. 「第N部分」标题 → 顶层号 N
      2. 行首的「N.M」或「N.M.K」条目 → 该层级号
    """
    defined = set()
    for cn in re.findall(r"^第(.+?)部分", soul, re.M):
        if cn in CN_NUM:
            defined.add(str(CN_NUM[cn]))
    for sid in re.findall(r"^(\d+(?:\.\d+)+)\s", soul, re.M):
        defined.add(sid)
        # 父级隐式存在：4.4.4 存在则 4.4 可被引用
        parts = sid.split(".")
        for i in range(1, len(parts)):
            defined.add(".".join(parts[:i]))
    return defined


def check_sections():
    soul = read(SOUL)
    defined = defined_sections(soul)
    targets = [SOUL] + [
        f"{PROTOCOL_DIR}/{n}"
        for n in sorted(os.listdir(os.path.join(ROOT, PROTOCOL_DIR)))
        if n.endswith(".txt")
    ]
    total = 0
    for path in targets:
        text = read(path)
        for sid in sorted(set(re.findall(r"§(\d+(?:\.\d+)*)", text))):
            total += 1
            if sid not in defined:
                issues.append(f"[A] {path}: 引用 §{sid} 但本体中无此章节")
    notes.append(f"[A] §ID 引用 {total} 处，本体定义 {len(defined)} 个章节号")


# ── B. 文件指针可达性 ──────────────────────────────────────
# 中文语境里文件名常紧贴前置词（"见protocols/cc.txt"），需要剥掉非路径前缀。
PATH_RE = re.compile(r"[A-Za-z0-9_一-鿿][A-Za-z0-9_./\\一-鿿 \-—·]*?\.(?:txt|md|py|js|json)")
# 已知不是本仓库文件的提及（外部工程/历史文件/示意路径）
POINTER_IGNORE = {
    "server.py",                        # 手机端中间件，不在本仓库
    "sync_messages.js",                 # 小程序脚本，已移出本体仓库
    "cloudfunctions/duChat/index.js",   # 云函数，已移出本体仓库
    "DeepSeek_soul.txt",                # 历史文件名（§更名记录）
    "led.py",                           # 相对 skills/灯光控制/ 的简写
    "check.py",                         # 本脚本的自指提及
}


def normalize_pointer(raw):
    """把正文里抓到的字符串收敛为可判定的相对路径，无法判定则返回 None。"""
    p = raw.strip().replace("\\", "/").strip("·—- ")
    if p in POINTER_IGNORE or os.path.basename(p) in POINTER_IGNORE:
        return None
    if p.endswith(".txt") and len(os.path.basename(p)) <= 5:
        return None  # 形如 ".txt" 的正则残片
    return p


def resolve(pointer):
    """本体用简写指路（"目录.txt"、"工程文档.txt"），故允许按 basename 全库匹配。"""
    if os.path.exists(os.path.join(ROOT, pointer)):
        return True
    base = os.path.basename(pointer)
    for rel in walk_files():
        if os.path.basename(rel) == base:
            return True
    return False


def check_pointers():
    targets = [SOUL, INDEX] + [
        f"{PROTOCOL_DIR}/{n}"
        for n in sorted(os.listdir(os.path.join(ROOT, PROTOCOL_DIR)))
        if n.endswith(".txt")
    ]
    seen, broken = set(), 0
    for path in targets:
        for raw in PATH_RE.findall(read(path)):
            p = normalize_pointer(raw)
            if not p or (path, p) in seen:
                continue
            seen.add((path, p))
            if not resolve(p):
                broken += 1
                issues.append(f"[B] {path}: 指针「{p}」在磁盘上不存在")
    notes.append(f"[B] 文件指针 {len(seen)} 处，断链 {broken} 处")


# ── C. 目录.txt 与磁盘双向一致性 ───────────────────────────
def index_entries():
    """抽取目录条目的文件名（形如「- 文件名.txt —— 摘要」）。"""
    names = set()
    for line in read(INDEX).splitlines():
        m = re.match(r"^\s*[-·]\s+(.+?\.(?:txt|md|py|js))(?:\s|$|—)", line)
        if m:
            names.add(os.path.basename(m.group(1).strip()))
    return names


def indexable_files():
    """应当被目录索引的文件（cc.txt §3.7：skills/ 等不入目录）。"""
    out = set()
    for rel in walk_files():
        top = rel.split("/")[0]
        if top in INDEX_EXEMPT_DIRS or "/" not in rel and rel in INDEX_EXEMPT_FILES:
            continue
        if top in INDEX_EXEMPT_FILES or os.path.basename(rel) in INDEX_EXEMPT_FILES:
            continue
        if not rel.endswith((".txt", ".md")):
            continue
        # 子目录自带目录.txt 的（如 论语/、阅读材料/），条目下沉到子目录索引
        parent = os.path.dirname(rel)
        if parent and os.path.exists(os.path.join(ROOT, parent, "目录.txt")):
            continue
        out.add(rel)
    return out


def check_index():
    entries = index_entries()
    on_disk = indexable_files()
    disk_names = {os.path.basename(p) for p in on_disk}

    ghosts = 0
    for name in sorted(entries):
        if not any(os.path.basename(r) == name for r in walk_files()):
            ghosts += 1
            issues.append(f"[C] 目录.txt 条目「{name}」在磁盘上不存在")

    missing = 0
    for rel in sorted(on_disk):
        if os.path.basename(rel) not in entries:
            missing += 1
            issues.append(f"[C] 磁盘文件「{rel}」未被 目录.txt 索引")

    notes.append(
        f"[C] 目录条目 {len(entries)} 条 / 应索引文件 {len(disk_names)} 个，"
        f"幽灵条目 {ghosts}，未索引 {missing}"
    )


def main():
    quiet = "--quiet" in sys.argv
    check_sections()
    check_pointers()
    check_index()

    if not quiet:
        print("渡 · 记忆系统一致性检查")
        print("─" * 40)
        for n in notes:
            print(n)
        print("─" * 40)

    if issues:
        print(f"发现 {len(issues)} 项待处理：")
        for i in issues:
            print("  " + i)
        return 1
    if not quiet:
        print("零断链 ✓")
    return 0


if __name__ == "__main__":
    sys.exit(main())