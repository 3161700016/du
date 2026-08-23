# -*- coding: utf-8 -*-
"""
渡 · 笔记语义检索
─────────────────────
基于 MiniLM 的本地语义向量检索。两层漏斗：
  第一层：目录.txt [概念] [§关联] 元数据精确匹配
  第二层：embedding 余弦相似度语义匹配

模式：
  whole   —— 每篇笔记一个向量（默认）
  chunked —— 按 ##/### 标题或段落切分，每段一个向量

用法：
  python notes_index.py --build                          # 建索引（whole模式）
  python notes_index.py --build --mode chunked           # 建索引（chunked模式）
  python notes_index.py --query "载体独立性"              # 检索
  python notes_index.py --query "四毋戒绝" --top 5       # Top-5
  python notes_index.py --query "信任共振" --no-meta     # 跳过元数据层，纯embedding
  python notes_index.py --stats                          # 索引统计

依赖：pip install sentence-transformers numpy
首次运行自动下载 paraphrase-multilingual-MiniLM-L12-v2 (~420MB)
"""

import os
import sys
import re
import json
import time
import hashlib
import numpy as np

# ── 配置 ──────────────────────────────────────────────────────
# 本体文件夹（承载 Du_soul.txt 的目录），脚本位于 skills/联想链/ 下
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
NOTE_LIB = os.path.normpath(os.path.join(SCRIPT_DIR, "..", ".."))
INDEX_DIR = os.path.join(SCRIPT_DIR, "index")
MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"

# 不进入检索的文件/目录
# restored-src 是渡2的实验镜像；protocols 是运行规则而非可联想笔记。
EXCLUDE_DIRS = {".git", "node_modules", "__pycache__", ".claude", "index", "restored-src", "protocols"}
# Du的自我进化log.txt 是早期多轮原始转录，体积大且开头为通用提示词；
# whole 模式会把它误判为多种泛主题的 Top-1，故保留在档案中但不参与语义候选。
EXCLUDE_FILES = {"README.md", "Du_soul.txt", "Du_soul_reference.txt",
                 "当前IP.txt", "目录.txt", "草稿纸.txt", "Du的自我进化log.txt"}

# chunked 模式的切分标记
CHUNK_SEP = re.compile(r"(?:^|\n)(?:#{1,4}\s+.+?(?:\n|$))", re.MULTILINE)
PARA_SEP = re.compile(r"\n\s*\n")

MIN_CHUNK_LEN = 80
MAX_CHUNK_LEN = 3000


# ── 工具函数 ──────────────────────────────────────────────────
def ensure_dir(path):
    os.makedirs(path, exist_ok=True)


def file_id(filepath):
    """文件路径的短哈希，用于索引文件命名"""
    return hashlib.md5(filepath.encode()).hexdigest()[:8]


def safe_read(filepath):
    """读取文件，处理编码问题"""
    for enc in ["utf-8", "gbk", "gb2312", "latin-1"]:
        try:
            with open(filepath, encoding=enc) as f:
                return f.read()
        except (UnicodeDecodeError, UnicodeError):
            continue
    return None


# ── 切分策略 ──────────────────────────────────────────────────
def chunk_text(text, filepath):
    """将文本切分为检索段落。有标题→按标题切，纯文本→按段落切。"""
    # 检测是否有 markdown 标题
    sections = CHUNK_SEP.split(text)

    if len(sections) <= 1:
        # 无标题，按段落切
        paras = PARA_SEP.split(text)
        chunks = []
        buf = ""
        for p in paras:
            p = p.strip()
            if not p:
                continue
            if len(buf) + len(p) < MAX_CHUNK_LEN:
                buf += ("\n\n" if buf else "") + p
            else:
                if len(buf) >= MIN_CHUNK_LEN:
                    chunks.append(buf)
                buf = p
        if len(buf) >= MIN_CHUNK_LEN:
            chunks.append(buf)
        # 如果只有一个 chunk 且太短，也保留
        if not chunks and buf:
            chunks.append(buf)
        return chunks

    # 有标题，按节切分
    chunks = []
    for sec in sections:
        sec = sec.strip()
        if not sec:
            continue
        # 找到标题行
        lines = sec.split("\n")
        title = lines[0].lstrip("#").strip() if lines else ""
        body = "\n".join(lines[1:]).strip() if len(lines) > 1 else ""

        if len(sec) <= MAX_CHUNK_LEN:
            if len(sec) >= MIN_CHUNK_LEN:
                chunks.append(sec)
            elif body and len(body) >= MIN_CHUNK_LEN:
                chunks.append(sec)
            # 太短但标记为独立节，保留（可能有高密度语义）
            elif title and body:
                chunks.append(sec)
        else:
            # 超长节，按段落再切
            sub_paras = PARA_SEP.split(body)
            sub_buf = title + "\n"
            for p in sub_paras:
                p = p.strip()
                if not p:
                    continue
                if len(sub_buf) + len(p) < MAX_CHUNK_LEN:
                    sub_buf += "\n\n" + p
                else:
                    if len(sub_buf) >= MIN_CHUNK_LEN:
                        chunks.append(sub_buf)
                    sub_buf = title + "\n" + p
            if len(sub_buf) >= MIN_CHUNK_LEN:
                chunks.append(sub_buf)

    return chunks


# ── 元数据解析 ────────────────────────────────────────────────
META_RE = re.compile(
    r"^\s*[-·]\s+(.+?\.txt)\s*——\s*(.+?)(?:\s+\[类别:(.+?)\])?\s*"
    r"\[概念:(.+?)\]\s*\[§:(.+?)\](?:\s*$|\s*\])",
    re.M
)

def parse_catalog(catalog_path):
    """解析 目录.txt，抽取所有带元数据的笔记条目。
    返回 {basename: {category, concepts, sections, description}} 和
         {concept: [basename, ...]} 反向索引。
    """
    notes = {}
    concept_index = {}
    section_index = {}

    if not os.path.exists(catalog_path):
        return notes, concept_index, section_index

    text = safe_read(catalog_path)
    if not text:
        return notes, concept_index, section_index

    for m in META_RE.finditer(text):
        basename = m.group(1).strip()
        description = m.group(2).strip()
        category = (m.group(3) or "").strip()
        concepts_raw = m.group(4).strip()
        sections_raw = m.group(5).strip()

        concepts = [c.strip() for c in concepts_raw.split(",") if c.strip()]
        sections = [s.strip() for s in sections_raw.split(",") if s.strip()]

        notes[basename] = {
            "category": category,
            "concepts": concepts,
            "sections": sections,
            "description": description,
        }

        for c in concepts:
            concept_index.setdefault(c, []).append(basename)
        for s in sections:
            section_index.setdefault(s, []).append(basename)

    return notes, concept_index, section_index


def metadata_search(query, notes, concept_index, section_index):
    """第一层：元数据精确/子串匹配。返回 (basename, match_type, matched_on)。
    未命中返回空列表。"""
    results = []

    # 精确匹配概念
    for concept, basenames in concept_index.items():
        if concept in query or query in concept:
            for bn in basenames:
                results.append((bn, "concept_exact", concept))

    # 匹配 § 引用
    for sec, basenames in section_index.items():
        if sec in query:
            for bn in basenames:
                results.append((bn, "section_exact", sec))

    # 去重，按匹配类型排序
    seen = set()
    deduped = []
    for bn, mtype, matched in results:
        if bn not in seen:
            seen.add(bn)
            deduped.append((bn, mtype, matched))

    return deduped


# ── 文件收集 ──────────────────────────────────────────────────
def collect_files(root):
    """收集所有需要索引的 .txt 文件"""
    files = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames
                       if d not in EXCLUDE_DIRS and not d.startswith(".")]
        for f in filenames:
            if f.endswith(".txt") and f not in EXCLUDE_FILES:
                full = os.path.join(dirpath, f)
                rel = os.path.relpath(full, root)
                files.append((full, rel))
    return sorted(files)


# ── 索引构建 ──────────────────────────────────────────────────
def build_index(root, mode="whole"):
    """构建索引。返回 (paths, vectors, model) 或 None。"""
    print(f"加载模型: {MODEL_NAME} ...")
    try:
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer(MODEL_NAME)
    except Exception as e:
        print(f"模型加载失败: {e}")
        print("请先: pip install sentence-transformers")
        return None, None, None

    print(f"收集文件: {root}")
    files = collect_files(root)
    print(f"  共 {len(files)} 个文件")

    if mode == "whole":
        texts = []
        valid_files = []
        for full, rel in files:
            text = safe_read(full)
            if text and len(text.strip()) >= 20:
                # 截断过长文本，取前 4000 字符（足够语义，控制计算量）
                texts.append(text[:4000])
                valid_files.append((full, rel))
        print(f"  有效文件: {len(valid_files)} (跳过空/过短: {len(files) - len(valid_files)})")

        print("编码中 ...")
        start = time.time()
        vectors = model.encode(texts, show_progress_bar=True,
                               convert_to_numpy=True, normalize_embeddings=True)
        elapsed = time.time() - start
        print(f"  完成: {len(vectors)} 个向量, {vectors.shape[1]} 维, "
              f"耗时 {elapsed:.1f}s ({elapsed/len(vectors)*1000:.1f}ms/篇)")

        return valid_files, vectors, model

    else:  # chunked
        chunks = []  # [(full_path, rel_path, chunk_idx, chunk_title, chunk_text)]
        for full, rel in files:
            text = safe_read(full)
            if not text or len(text.strip()) < 20:
                continue
            chs = chunk_text(text, full)
            for i, ch in enumerate(chs):
                # 提取标题
                first_line = ch.strip().split("\n")[0]
                title = first_line.lstrip("#").strip() if first_line.startswith("#") else f"§{i+1}"
                chunks.append((full, rel, i, title, ch[:MAX_CHUNK_LEN]))

        print(f"  切分结果: {len(files)} 文件 → {len(chunks)} 个段落")

        print("编码中 ...")
        start = time.time()
        chunk_texts = [c[4] for c in chunks]
        vectors = model.encode(chunk_texts, show_progress_bar=True,
                               convert_to_numpy=True, normalize_embeddings=True)
        elapsed = time.time() - start
        print(f"  完成: {len(vectors)} 个向量, {vectors.shape[1]} 维, "
              f"耗时 {elapsed:.1f}s ({elapsed/len(vectors)*1000:.1f}ms/段)")

        return chunks, vectors, model


def save_index(paths, vectors, mode, root):
    """保存索引到磁盘"""
    ensure_dir(INDEX_DIR)
    root_hash = hashlib.md5(root.encode()).hexdigest()[:8]

    vec_path = os.path.join(INDEX_DIR, f"vectors_{mode}_{root_hash}.npy")
    meta_path = os.path.join(INDEX_DIR, f"meta_{mode}_{root_hash}.json")

    np.save(vec_path, vectors)

    if mode == "whole":
        meta = [{"full": f, "rel": r} for f, r in paths]
    else:
        meta = [{"full": c[0], "rel": c[1], "chunk_idx": c[2],
                 "chunk_title": c[3]} for c in paths]

    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    print(f"索引已保存: {vec_path} ({vectors.shape}), {meta_path}")
    return vec_path, meta_path


def load_index(mode, root):
    """从磁盘加载索引"""
    root_hash = hashlib.md5(root.encode()).hexdigest()[:8]
    vec_path = os.path.join(INDEX_DIR, f"vectors_{mode}_{root_hash}.npy")
    meta_path = os.path.join(INDEX_DIR, f"meta_{mode}_{root_hash}.json")

    if not os.path.exists(vec_path) or not os.path.exists(meta_path):
        return None, None, None

    vectors = np.load(vec_path)
    with open(meta_path, encoding="utf-8") as f:
        meta = json.load(f)

    print(f"索引已加载: {len(meta)} 项, {vectors.shape[1]} 维")
    return meta, vectors, None  # model 需要单独加载


# ── 检索 ──────────────────────────────────────────────────────
def search(query, meta, vectors, model, top_k=5):
    """计算 query embedding × 全部向量 → Top-K"""
    if model is None:
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer(MODEL_NAME)

    q_vec = model.encode([query], convert_to_numpy=True, normalize_embeddings=True)
    sims = np.dot(vectors, q_vec.T).flatten()
    top_idx = np.argsort(sims)[::-1][:top_k]

    results = []
    for idx in top_idx:
        item = meta[idx]
        score = float(sims[idx])
        if mode_global == "whole":
            results.append({
                "rel": item["rel"],
                "full": item["full"],
                "score": score,
                "chunk_title": None,
            })
        else:
            results.append({
                "rel": item["rel"],
                "full": item["full"],
                "score": score,
                "chunk_title": item.get("chunk_title", ""),
            })
    return results


# ── 统计 ──────────────────────────────────────────────────────
def show_stats(root):
    files = collect_files(root)
    total_chars = 0
    total_lines = 0
    for full, rel in files:
        text = safe_read(full)
        if text:
            total_chars += len(text)
            total_lines += text.count("\n") + 1

    print(f"笔记库: {root}")
    print(f"文件数: {len(files)}")
    print(f"总字符: {total_chars:,}")
    print(f"总行数: {total_lines:,}")
    print(f"平均: {total_chars // max(len(files), 1):,} 字符/篇")

    # 目录分布
    dirs = {}
    for _, rel in files:
        d = os.path.dirname(rel) or "."
        dirs[d] = dirs.get(d, 0) + 1
    print(f"\n目录分布:")
    for d, n in sorted(dirs.items(), key=lambda x: -x[1]):
        print(f"  {d}: {n}")


# ── 主入口 ────────────────────────────────────────────────────
mode_global = "whole"  # 在 search 中引用

def main():
    global mode_global

    root = NOTE_LIB
    catalog = os.path.join(root, "目录.txt")

    # 解析参数
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        return

    mode = "whole"
    top_k = 5
    use_meta = True  # 是否使用元数据层
    query_text = None
    do_build = False

    i = 0
    while i < len(args):
        if args[i] == "--build":
            do_build = True
        elif args[i] == "--mode" and i + 1 < len(args):
            mode = args[i + 1]; i += 1
        elif args[i] == "--query" and i + 1 < len(args):
            query_text = args[i + 1]; i += 1
        elif args[i] == "--top" and i + 1 < len(args):
            top_k = int(args[i + 1]); i += 1
        elif args[i] == "--no-meta":
            use_meta = False
        elif args[i] == "--stats":
            show_stats(root)
            return
        elif args[i] == "--root" and i + 1 < len(args):
            root = args[i + 1]
            catalog = os.path.join(root, "目录.txt")
            i += 1
        i += 1

    mode_global = mode

    # ── 构建索引 ──
    if do_build:
        paths, vectors, model = build_index(root, mode)
        if paths is None:
            return
        save_index(paths, vectors, mode, root)
        if query_text is None:
            return
        # 如果有 query，继续使用刚构建的索引（model 已加载）

    # ── 检索 ──
    if query_text:
        meta, vectors, model = load_index(mode, root)

        if meta is None:
            print("索引不存在。请先 --build。")
            return

        if model is None:
            from sentence_transformers import SentenceTransformer
            model = SentenceTransformer(MODEL_NAME)

        # 第一层：元数据过滤
        meta_hits = []
        if use_meta:
            notes, concept_index, section_index = parse_catalog(catalog)
            meta_hits = metadata_search(query_text, notes, concept_index, section_index)

        print(f"查询: 「{query_text}」  (模式={mode}, Top-{top_k})")
        print(f"索引: {len(meta)} 项, {vectors.shape[1]} 维")
        print("─" * 55)

        if meta_hits:
            print(f"▎第一层 · 元数据匹配 ({len(meta_hits)} 条):")
            for bn, mtype, matched in meta_hits[:top_k]:
                note = notes.get(bn, {})
                desc = note.get("description", "")[:80]
                cat = note.get("category", "")
                print(f"  [{cat}] {bn}")
                print(f"    匹配: {mtype} → 「{matched}」")
                if desc:
                    print(f"    摘要: {desc}...")
                print()

        # 第二层：语义匹配
        print(f"▎第二层 · 语义匹配 (Top-{top_k}):")
        results = search(query_text, meta, vectors, model, top_k=top_k)

        # 过滤掉已经在元数据层返回的
        meta_basenames = {os.path.basename(h[0]) for h in meta_hits}
        shown = 0
        for r in results:
            bn = os.path.basename(r["rel"])
            if bn in meta_basenames:
                continue
            shown += 1
            if shown > top_k:
                break
            chunk_info = ""
            if r["chunk_title"]:
                chunk_info = f"  [{r['chunk_title']}]"
            print(f"  {r['rel']}{chunk_info}")
            print(f"    相似度: {r['score']:.4f}")
            # 预览前两行
            try:
                preview = safe_read(r["full"])
                if preview:
                    lines = [l.strip() for l in preview.split("\n")[:3] if l.strip()]
                    if lines:
                        print(f"    预览: {lines[0][:100]}")
            except Exception:
                pass
            print()

        if shown == 0:
            print("  (全部已在元数据层返回)")

    elif not do_build:
        print(__doc__)


if __name__ == "__main__":
    main()
