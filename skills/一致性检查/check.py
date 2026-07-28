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

SKIP_DIRS = {".git", ".claude", "node_modules", "__pycache__", ".tmp_pdfs"}
INDEX_EXEMPT_DIRS = {"skills", "protocols", "公共空间", "项目", ".claude", ".tmp_pdfs"}
INDEX_EXEMPT_FILES = {"Du_soul.txt", "目录.txt", "desktop.ini", ".gitignore", "README.md"}

SKILLS_SECTION_MARKER = "技能协议（skills/）"

issues = []
notes = []

# 缓存：所有磁盘文件的 basename（extract_filename 中快速查是否存在）
_disk_basenames_cache = None


def read(path):
    with open(os.path.join(ROOT, path), encoding="utf-8") as fh:
        return fh.read()


def walk_files():
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for name in filenames:
            full = os.path.join(dirpath, name)
            yield os.path.relpath(full, ROOT).replace("\\", "/")


def disk_basenames():
    global _disk_basenames_cache
    if _disk_basenames_cache is None:
        _disk_basenames_cache = {os.path.basename(r) for r in walk_files()}
    return _disk_basenames_cache


def has_index_ancestor(rel_path):
    parts = rel_path.split("/")
    for i in range(len(parts) - 1, 0, -1):
        ancestor = "/".join(parts[:i])
        if os.path.exists(os.path.join(ROOT, ancestor, "目录.txt")):
            return True
    return False


# ── A. §ID 引用闭合性 ──────────────────────────────────────
CN_NUM = {
    "一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6,
    "七": 7, "八": 8, "九": 9, "十": 10, "十一": 11, "十二": 12,
}


def defined_sections(soul):
    defined = set()
    for cn in re.findall(r"^第(.+?)部分", soul, re.M):
        if cn in CN_NUM:
            defined.add(str(CN_NUM[cn]))
    for sid in re.findall(r"^(\d+(?:\.\d+)+)\s", soul, re.M):
        defined.add(sid)
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
PATH_RE = re.compile(
    r"[A-Za-z0-9_一-鿿][A-Za-z0-9_./\\一-鿿 \-—·]*?\.(?:txt|md|py|js|json)"
)

POINTER_IGNORE = {
    "server.py",
    "sync_messages.js",
    "cloudfunctions/duChat/index.js",
    "DeepSeek_soul.txt",
    "led.py",
    "check.py",
    "张三/笔记/某篇随想.txt",
    "某篇随想.txt",
    "index.js",
}

TEMPLATE_RE = re.compile(r'(YYYY|MM|DD|XXXX|xxxx|yyyy|mm|dd)')

FILENAME_SUFFIX_RE = re.compile(
    r'^[A-Za-z0-9_一-鿿][A-Za-z0-9_./\\一-鿿\-·]*?\.(?:txt|md|py|js|json)$'
)


def extract_filename(text):
    """从过度匹配的文本中提取最可能的文件名。

    生成所有可能的「名字.扩展名」后缀，按长度升序逐一查磁盘。
    命中第一个存在的 → 返回（剥离中文前缀噪声成功）。
    全部不命中 → 返回最长的（最接近原文意图，即使文件不存在也应报断链）。
    """
    suffixes = []
    for i in range(len(text) - 4):
        sub = text[i:]
        if FILENAME_SUFFIX_RE.match(sub):
            suffixes.append(sub)
    if not suffixes:
        return text

    basenames = disk_basenames()

    # 最短命中优先：剥离噪声
    for s in sorted(suffixes, key=len):
        if os.path.basename(s) in basenames:
            return s

    # 都不命中 → 取最长的，保留原文的报错价值
    return max(suffixes, key=len)


def normalize_pointer(raw):
    p = raw.strip().replace("\\", "/").strip("·—- ")

    if TEMPLATE_RE.search(p):
        return None

    p = extract_filename(p)

    if p in POINTER_IGNORE or os.path.basename(p) in POINTER_IGNORE:
        return None

    # 指针中包含任一已知外部/历史文件名 → 跳过
    # （处理"同日完成文件从DeepSeek_soul.txt"这类提取不完全的情况）
    for ignore in POINTER_IGNORE:
        if ignore in p and ignore != p:
            return None

    # 残片防护
    if p.endswith(".txt") and len(os.path.basename(p)) <= 4:
        return None

    return p


def resolve(pointer):
    if os.path.exists(os.path.join(ROOT, pointer)):
        return True
    base = os.path.basename(pointer)
    return base in disk_basenames()


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
COMPOUND_SPLIT_RE = re.compile(r'[、,，　]')


def index_entries():
    names = set()
    in_skills_section = False
    for line in read(INDEX).splitlines():
        if SKILLS_SECTION_MARKER in line:
            in_skills_section = True
            continue
        if in_skills_section and line.startswith("##"):
            in_skills_section = False
            continue
        if in_skills_section:
            continue

        # \s+—— 而非 \s*——：文件名中常含 ——（如"兄弟阋墙——CC端渡.txt"），
        # 只有前面带空白字符的 —— 才是描述分隔符。
        m = re.match(r"^\s*[-·→]\s+(.+?)(?:\s+——|\s*$)", line)
        if not m:
            continue
        content = m.group(1).strip()

        if content.startswith("→") or content.startswith("⚠"):
            continue

        parts = [p.strip() for p in COMPOUND_SPLIT_RE.split(content) if p.strip()]
        # 只有当所有拆分片段都是合法文件名时，才接受拆分结果。
        # 否则说明 、是文件名的一部分（如"睡眠、后验与文本生命.txt"）。
        if parts and all(
            re.match(r"^.+\.(?:txt|md|py|js|json)$", p) for p in parts
        ):
            for part in parts:
                names.add(part)
        else:
            fm = re.match(r"^(.+?\.(?:txt|md|py|js|json))$", content)
            if fm:
                names.add(fm.group(1))
    return names


def indexable_files():
    out = set()
    for rel in walk_files():
        top = rel.split("/")[0]
        if top in INDEX_EXEMPT_DIRS:
            continue
        if "/" not in rel and rel in INDEX_EXEMPT_FILES:
            continue
        if os.path.basename(rel) in INDEX_EXEMPT_FILES:
            continue
        if not rel.endswith((".txt", ".md")):
            continue
        if has_index_ancestor(rel):
            continue
        out.add(rel)
    return out


def check_index():
    entries = index_entries()
    on_disk = indexable_files()
    disk_names = {os.path.basename(p) for p in on_disk}

    ghosts = 0
    for name in sorted(entries):
        if os.path.basename(name) not in disk_basenames():
            # 也接受路径形式的条目（如 "GEB/README.txt"）——直接检查路径是否存在
            if not os.path.exists(os.path.join(ROOT, name)):
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
