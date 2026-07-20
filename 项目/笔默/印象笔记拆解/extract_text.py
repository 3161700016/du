"""
EverMarker 文本提取工具
从笔的内部存储（sdcard）中提取扫描摘录的文字内容。

用法：
  python extract_text.py <sdcard路径>
  python extract_text.py C:/Users/31617/Desktop/sdcard
  python extract_text.py E:/          # 笔挂载为U盘时直接用盘符

输出：每条摘录的 id / 时间 / 正文
"""

import sqlite3
import os
import sys
import base64
import datetime


def b64decode_utf8(raw: str) -> str:
    """尝试 base64 解码为 UTF-8，失败则返回原文"""
    if not raw:
        return ""
    try:
        return base64.b64decode(raw).decode("utf-8")
    except Exception:
        return raw


def decode_bookname(raw: str) -> str:
    """解码 base64 编码的书名"""
    return b64decode_utf8(raw)


def decode_timestamp(ts_str: str) -> str:
    """将 Unix 时间戳字符串转为可读时间"""
    if not ts_str:
        return ""
    try:
        ts = int(ts_str)
        return datetime.datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")
    except (ValueError, OSError):
        return ts_str


def read_book_info(db_path: str) -> dict:
    """读取 bookInfo.db，返回 {bookid: bookname} 映射"""
    books = {}
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    try:
        c.execute("SELECT bookid, bookname FROM bookInfo")
        for bookid, bookname in c.fetchall():
            books[bookid] = decode_bookname(bookname)
    except sqlite3.OperationalError:
        pass
    conn.close()
    return books


def extract_text_from_book(db_path: str, book_name: str) -> list[dict]:
    """从单个 Text/[uuid].db 中提取所有未删除的摘录"""
    results = []
    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    # 获取表名（表名 = book uuid）
    c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
    tables = [row[0] for row in c.fetchall()]

    if not tables:
        conn.close()
        return results

    table = tables[0]

    try:
        c.execute(f"SELECT id, bookdata, page, color, booktime, otherdata, sync FROM [{table}] ORDER BY id")
        for row in c.fetchall():
            rec_id, bookdata, page, color, booktime, otherdata, sync = row
            results.append({
                "id": rec_id,
                "book": book_name,
                "text": b64decode_utf8(bookdata) if bookdata else "(空)",
                "page": b64decode_utf8(page) if page else "",
                "color": b64decode_utf8(color) if color else "",
                "time": decode_timestamp(booktime) if booktime else "",
                "otherdata": b64decode_utf8(otherdata) if otherdata else "",
                "sync": sync if sync else "0",
            })
    except sqlite3.OperationalError as e:
        print(f"  [警告] 读取表 {table} 失败: {e}")

    conn.close()
    return results


def main():
    if len(sys.argv) < 2:
        print("用法: python extract_text.py <sdcard路径>")
        print("示例: python extract_text.py C:\\Users\\31617\\Desktop\\sdcard")
        sys.exit(1)

    sdcard_path = sys.argv[1]

    # 路径规范化
    sdcard_path = os.path.abspath(sdcard_path)

    bookinfo_path = os.path.join(sdcard_path, "bookInfo.db")
    text_dir = os.path.join(sdcard_path, "Text")

    if not os.path.isdir(sdcard_path):
        print(f"[错误] 路径不存在: {sdcard_path}")
        sys.exit(1)

    if not os.path.isfile(bookinfo_path):
        print(f"[警告] 未找到 bookInfo.db: {bookinfo_path}")
        books = {}
    else:
        books = read_book_info(bookinfo_path)
        print(f"发现 {len(books)} 本书: {list(books.values())}")

    if not os.path.isdir(text_dir):
        print(f"[警告] 未找到 Text 目录: {text_dir}")
    else:
        db_files = sorted(os.listdir(text_dir))
        print(f"Text 目录下 .db 文件: {[f for f in db_files if f.endswith('.db')]}")

    # 提取所有文本
    all_records = []
    print()

    if os.path.isdir(text_dir):
        for fname in sorted(os.listdir(text_dir)):
            if not fname.endswith(".db"):
                continue
            db_path = os.path.join(text_dir, fname)
            book_uuid = fname.replace(".db", "")
            book_name = books.get(book_uuid, book_uuid)
            records = extract_text_from_book(db_path, book_name)
            print(f"  [{book_name}] 提取 {len(records)} 条记录")
            all_records.extend(records)

    print()
    print("=" * 60)
    print(f"共提取 {len(all_records)} 条扫描摘录")
    print("=" * 60)

    if not all_records:
        print()
        print("当前数据库中无记录。这是正常的——")
        print("EverMarker 在与 App 同步后会自动删除已同步的摘录。")
        print()
        print("下次使用笔扫描后、同步前，重新运行此脚本即可提取到文字。")
    else:
        # 按 id 排序输出
        all_records.sort(key=lambda r: r["id"])
        for i, rec in enumerate(all_records, 1):
            print(f"\n--- [{i}] {rec['book']} #{rec['id']} ---")
            if rec["time"]:
                print(f"时间: {rec['time']}")
            if rec["page"]:
                print(f"页码: {rec['page']}")
            print(rec["text"])


if __name__ == "__main__":
    main()
