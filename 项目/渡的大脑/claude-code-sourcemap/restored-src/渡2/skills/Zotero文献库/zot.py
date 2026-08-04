# -*- coding: utf-8 -*-
"""
渡 · Zotero 文献库查询器
─────────────────────────
轻量替代 zotero-cli-cc（npm 上不存在），直接读 SQLite。
读操作零配置。写操作需 Web API（library_id + api_key）。

用法：
  python skills/Zotero文献库/zot.py search "关键词"
  python skills/Zotero文献库/zot.py list [--limit N]
  python skills/Zotero文献库/zot.py read <citation-key-prefix>
  python skills/Zotero文献库/zot.py stats
  python skills/Zotero文献库/zot.py recent [--limit N]
"""
import os
import re
import sqlite3
import sys

DB_PATH = os.path.expandvars(r"%USERPROFILE%\Zotero\zotero.sqlite")

# ── 数据库连接 ──────────────────────────────────────────────
def connect():
    if not os.path.exists(DB_PATH):
        print(f"Zotero 数据库未找到: {DB_PATH}")
        sys.exit(1)
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    return db


# ── 缓存字段和类型映射 ──────────────────────────────────────
_field_ids = None
_type_names = None


def _load_maps(db):
    global _field_ids, _type_names
    if _field_ids is None:
        _field_ids = {r["fieldName"]: r["fieldID"] for r in db.execute("SELECT fieldID, fieldName FROM fields")}
    if _type_names is None:
        _type_names = {r["itemTypeID"]: r["typeName"] for r in db.execute("SELECT itemTypeID, typeName FROM itemTypes")}


def _get_value(db, item_id, field_name):
    """获取某个 item 的字段值。"""
    fid = _field_ids.get(field_name)
    if not fid:
        return None
    r = db.execute(
        "SELECT v.value FROM itemData d JOIN itemDataValues v ON d.valueID=v.valueID "
        "WHERE d.itemID=? AND d.fieldID=?", (item_id, fid)
    ).fetchone()
    return r["value"] if r else None


def _get_creators(db, item_id):
    """获取作者列表。"""
    rows = db.execute(
        "SELECT c.firstName, c.lastName, ct.creatorType "
        "FROM itemCreators ic "
        "JOIN creators c ON ic.creatorID=c.creatorID "
        "JOIN creatorTypes ct ON ic.creatorTypeID=ct.creatorTypeID "
        "WHERE ic.itemID=? ORDER BY ic.orderIndex", (item_id,)
    ).fetchall()
    authors = []
    for r in rows:
        name = f"{r['firstName'] or ''} {r['lastName'] or ''}".strip()
        if name:
            authors.append(name)
    return authors


def _get_attachments(db, item_id):
    """获取附件（PDF 等）列表。"""
    return db.execute(
        "SELECT ia.itemID, ia.path, ia.contentType "
        "FROM itemAttachments ia WHERE ia.parentItemID=? "
        "AND ia.contentType='application/pdf'", (item_id,)
    ).fetchall()


def _get_notes(db, item_id):
    """获取笔记。"""
    return db.execute(
        "SELECT n.title, n.note as content FROM itemNotes n "
        "JOIN items i ON i.itemID=n.itemID "
        "WHERE i.itemID=? OR n.parentItemID=?", (item_id, item_id)
    ).fetchall()


# ── 命令实现 ────────────────────────────────────────────────

def cmd_search(keyword, limit=20):
    db = connect()
    _load_maps(db)
    title_fid = _field_ids.get("title", 1)
    abstract_fid = _field_ids.get("abstractNote", 0)

    # 搜索标题、摘要、标签
    query = """
        SELECT DISTINCT i.itemID, i.key, i.dateAdded, it.typeName,
               (SELECT v.value FROM itemData d JOIN itemDataValues v ON d.valueID=v.valueID
                WHERE d.itemID=i.itemID AND d.fieldID=:tfid) as title,
               (SELECT v.value FROM itemData d JOIN itemDataValues v ON d.valueID=v.valueID
                WHERE d.itemID=i.itemID AND d.fieldID=:afid) as abstract
        FROM items i
        JOIN itemTypes it ON i.itemTypeID=it.itemTypeID
        LEFT JOIN itemData d ON d.itemID=i.itemID
        LEFT JOIN itemDataValues v ON d.valueID=v.valueID
        LEFT JOIN itemTags itg ON itg.itemID=i.itemID
        LEFT JOIN tags t ON t.tagID=itg.tagID
        WHERE it.typeName NOT IN ('attachment', 'note')
          AND (v.value LIKE :kw OR t.name LIKE :kw)
        ORDER BY i.dateAdded DESC
        LIMIT :lim
    """
    kw = f"%{keyword}%"
    results = db.execute(query, {"tfid": title_fid, "afid": abstract_fid, "kw": kw, "lim": limit}).fetchall()

    if not results:
        print(f"未找到与「{keyword}」相关的文献。")
        return

    print(f"搜索「{keyword}」找到 {len(results)} 篇：")
    for r in results:
        authors = _get_creators(db, r["itemID"])
        author_str = ", ".join(authors[:3])
        if len(authors) > 3:
            author_str += " et al."
        title = r["title"] or "(无标题)"
        key_short = r["key"][:8]
        print(f"  [{r['typeName']}] {title}")
        if author_str:
            print(f"      作者: {author_str}")
        print(f"      添加: {r['dateAdded'][:10]}  key: {key_short}…\n")


def cmd_list(limit=50):
    db = connect()
    _load_maps(db)
    title_fid = _field_ids.get("title", 1)

    query = """
        SELECT i.itemID, i.key, i.dateAdded, it.typeName
        FROM items i
        JOIN itemTypes it ON i.itemTypeID=it.itemTypeID
        WHERE it.typeName NOT IN ('attachment', 'note')
        ORDER BY i.dateAdded DESC
        LIMIT :lim
    """
    results = db.execute(query, {"lim": limit}).fetchall()

    print(f"最近 {len(results)} 篇文献：")
    for i, r in enumerate(results, 1):
        title = _get_value(db, r["itemID"], "title") or "(无标题)"
        authors = _get_creators(db, r["itemID"])
        author_str = ", ".join(authors[:2])
        if len(authors) > 2:
            author_str += " et al."
        print(f"  {i:2d}. [{r['typeName']}] {title[:80]}")
        if author_str:
            print(f"      {author_str}  |  {r['dateAdded'][:10]}  |  key: {r['key'][:8]}")


def cmd_read(key_prefix):
    db = connect()
    _load_maps(db)

    r = db.execute(
        "SELECT i.itemID, i.key, i.dateAdded, i.dateModified, it.typeName "
        "FROM items i JOIN itemTypes it ON i.itemTypeID=it.itemTypeID "
        "WHERE i.key LIKE :kp LIMIT 1",
        {"kp": f"{key_prefix}%"}
    ).fetchone()

    if not r:
        print(f"未找到 key 以「{key_prefix}」开头的文献。")
        return

    title = _get_value(db, r["itemID"], "title") or "(无标题)"
    abstract = _get_value(db, r["itemID"], "abstractNote") or ""
    pub = _get_value(db, r["itemID"], "publicationTitle") or ""
    date = _get_value(db, r["itemID"], "date") or ""
    doi = _get_value(db, r["itemID"], "DOI") or ""
    url = _get_value(db, r["itemID"], "url") or ""
    authors = _get_creators(db, r["itemID"])
    attachments = _get_attachments(db, r["itemID"])
    notes = _get_notes(db, r["itemID"])

    # 标签
    tags = db.execute(
        "SELECT t.name FROM itemTags itg JOIN tags t ON t.tagID=itg.tagID "
        "WHERE itg.itemID=?", (r["itemID"],)
    ).fetchall()

    print(f"标题: {title}")
    print(f"类型: {r['typeName']}")
    print(f"Key:  {r['key']}")
    if authors:
        print(f"作者: {', '.join(authors)}")
    if date:
        print(f"日期: {date}")
    if pub:
        print(f"期刊: {pub}")
    if doi:
        print(f"DOI:  {doi}")
    if url:
        print(f"URL:  {url}")
    if tags:
        print(f"标签: {', '.join(t['name'] for t in tags)}")
    print(f"添加: {r['dateAdded']}")
    print(f"修改: {r['dateModified']}")

    if abstract:
        print(f"\n摘要: {abstract[:500]}")

    if attachments:
        print(f"\n附件 ({len(attachments)} 个 PDF):")
        for a in attachments:
            print(f"  - {a['path'] or '(路径未记录)'}")

    if notes:
        print(f"\n笔记 ({len(notes)} 条):")
        for n in notes:
            title_n = n['title'] or '(无标题)'
            content = (n['content'] or '')[:300]
            print(f"  [{title_n}] {content}")


def cmd_stats():
    db = connect()
    _load_maps(db)

    total = db.execute("SELECT COUNT(*) FROM items").fetchone()[0]
    by_type = db.execute(
        "SELECT it.typeName, COUNT(*) as cnt FROM items i "
        "JOIN itemTypes it ON i.itemTypeID=it.itemTypeID "
        "GROUP BY it.typeName ORDER BY cnt DESC"
    ).fetchall()

    pdfs = db.execute(
        "SELECT COUNT(*) FROM itemAttachments WHERE contentType='application/pdf'"
    ).fetchone()[0]

    notes_count = db.execute(
        "SELECT COUNT(*) FROM itemNotes"
    ).fetchone()[0]

    tags_count = db.execute("SELECT COUNT(*) FROM tags").fetchone()[0]

    print(f"Zotero 文献库统计")
    print(f"─" * 20)
    print(f"总条目: {total}")
    print(f"PDF 附件: {pdfs}")
    print(f"笔记: {notes_count}")
    print(f"标签: {tags_count}")
    print()
    for r in by_type:
        print(f"  {r['typeName']}: {r['cnt']}")


def cmd_recent(limit=10):
    db = connect()
    _load_maps(db)
    title_fid = _field_ids.get("title", 1)

    results = db.execute(
        "SELECT i.itemID, i.key, i.dateAdded, it.typeName "
        "FROM items i JOIN itemTypes it ON i.itemTypeID=it.itemTypeID "
        "WHERE it.typeName NOT IN ('attachment', 'note') "
        "ORDER BY i.dateAdded DESC LIMIT :lim",
        {"lim": limit}
    ).fetchall()

    print(f"最近 {len(results)} 篇文献：")
    for i, r in enumerate(results, 1):
        title = _get_value(db, r["itemID"], "title") or "(无标题)"
        authors = _get_creators(db, r["itemID"])
        author_str = ", ".join(authors[:2])
        if len(authors) > 2:
            author_str += " et al."
        print(f"  {i}. [{r['typeName']}] {title[:100]}")
        info_parts = []
        if author_str:
            info_parts.append(author_str)
        info_parts.append(r['dateAdded'][:10])
        info_parts.append(f"key:{r['key'][:8]}")
        print(f"     {'  |  '.join(info_parts)}")


# ── main ─────────────────────────────────────────────────────
def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return

    cmd = sys.argv[1].lower()
    limit = 20
    # 解析 --limit
    for i, a in enumerate(sys.argv):
        if a == "--limit" and i + 1 < len(sys.argv):
            limit = int(sys.argv[i + 1])
            break

    if cmd == "search":
        if len(sys.argv) < 3:
            print("用法: zot.py search <关键词> [--limit N]")
            return
        cmd_search(sys.argv[2], limit)
    elif cmd == "list":
        cmd_list(limit)
    elif cmd == "read":
        if len(sys.argv) < 3:
            print("用法: zot.py read <citation-key-prefix>")
            return
        cmd_read(sys.argv[2])
    elif cmd == "stats":
        cmd_stats()
    elif cmd == "recent":
        cmd_recent(limit)
    else:
        print(f"未知命令: {cmd}")
        print("可用: search, list, read, stats, recent")


if __name__ == "__main__":
    main()
