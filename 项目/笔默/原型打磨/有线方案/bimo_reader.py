"""
笔默有线原型 — 主程序
=====================
MTP 拉取笔的扫描 → 逐条展示 → 键盘输入感想 → 配对存入共读文档。

使用方法:
  python bimo_reader.py                      # 交互模式
  python bimo_reader.py --batch              # 批量模式（全部拉取后不逐条交互）
  python bimo_reader.py --output 我的共读.txt  # 指定输出路径

交互命令 (逐条展示时):
  <输入感想>    → 配对存入
  <回车>        → 跳过本条，仅存扫描文本
  s               → 跳过本条
  q               → 停止展示，剩余扫描下次再处理
"""

import sys
import io
import os
import time
import json
import subprocess
import tempfile
import sqlite3
import base64
import re
import threading
from datetime import datetime

# Fix Windows GBK console encoding
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# ============================================================================
# 路径配置
# ============================================================================

DESKTOP = os.path.expanduser("~/Desktop")
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
PROTOTYPE_DIR = os.path.dirname(PROJECT_DIR)  # 原型打磨/
CODOC_PATH = os.path.join(PROTOTYPE_DIR, "共读文档")

DEFAULT_OUTPUT = None  # 由书名+日期自动生成
STATE_FILE = os.path.join(PROJECT_DIR, ".bimo_last_id.txt")

# ============================================================================
# MTP 拉取模块
# ============================================================================

PS_SCRIPT = r"""
$shell = New-Object -ComObject Shell.Application
$computer = $shell.NameSpace(0x11)
$scanos = $null
foreach ($item in $computer.Items()) { if ($item.Name -eq "ScanOS") { $scanos = $item; break } }
if (-not $scanos) { Write-Output "MTP:ScanOS_NOT_FOUND"; exit 1 }
$scanosFolder = $shell.NameSpace($scanos)
$yxm2 = $null
foreach ($item in $scanosFolder.Items()) { if ($item.Name -eq "YX-M2") { $yxm2 = $item; break } }
if (-not $yxm2) { Write-Output "MTP:YX-M2_NOT_FOUND"; exit 1 }
$yxm2Folder = $shell.NameSpace($yxm2)
$sdcard = $null
foreach ($item in $yxm2Folder.Items()) { if ($item.Name -eq "sdcard") { $sdcard = $item; break } }
if (-not $sdcard) { Write-Output "MTP:SDCARD_NOT_FOUND"; exit 1 }
$sdcardFolder = $shell.NameSpace($sdcard)
$textFolder = $null
foreach ($item in $sdcardFolder.Items()) { if ($item.Name -eq "Text") { $textFolder = $item; break } }
$cacheFolder = $null
foreach ($item in $sdcardFolder.Items()) { if ($item.Name -eq "cache") { $cacheFolder = $item; break } }
$destPath = $args[0]
if (-not (Test-Path $destPath)) { New-Item -ItemType Directory -Path $destPath -Force | Out-Null }
$dest = $shell.NameSpace($destPath)

# Copy with retry + size verify (MTP CopyHere is async and unreliable)
$cpFlags = 0x0614  # FOF_SILENT|FOF_NOCONFIRMATION|FOF_NOERRORUI|FOF_NOCONFIRMMKDIR
function SafeCopy($srcItem, $destName) {
    $destFile = Join-Path $destPath $destName
    for ($i = 0; $i -lt 5; $i++) {
        Remove-Item $destFile -Force -ErrorAction SilentlyContinue
        $dest.CopyHere($srcItem, $cpFlags)
        Start-Sleep -Seconds 3
        if (Test-Path $destFile) {
            $sz = (Get-Item $destFile).Length
            if ($sz -gt 5000) { return $true }
        }
    }
    return $false
}

$bookInfo = $null
foreach ($item in $sdcardFolder.Items()) { if ($item.Name -eq "bookInfo.db") { $bookInfo = $item; break } }
if ($bookInfo) { SafeCopy $bookInfo "bookInfo.db" | Out-Null }

if ($textFolder) {
    foreach ($item in $shell.NameSpace($textFolder).Items()) {
        if ($item.Name -like "*.db") { SafeCopy $item $item.Name | Out-Null }
    }
}
if ($cacheFolder) {
    foreach ($item in $shell.NameSpace($cacheFolder).Items()) {
        if (-not $item.IsFolder) { SafeCopy $item $item.Name | Out-Null }
    }
}
Write-Output "MTP:OK"
""".strip()


def pull_from_pen(target_dir: str) -> bool:
    """从笔 MTP 拉取 db 文件。"""
    ps_path = os.path.join(tempfile.gettempdir(), "_bimo_pull.ps1")
    with open(ps_path, 'w', encoding='utf-8') as f:
        f.write(PS_SCRIPT)
    try:
        r = subprocess.run(
            ["powershell.exe", "-ExecutionPolicy", "Bypass", "-File", ps_path, target_dir],
            capture_output=True, text=True, timeout=30
        )
        return "MTP:OK" in r.stdout
    except:
        return False
    finally:
        try: os.unlink(ps_path)
        except: pass


# ============================================================================
# 数据库解析
# ============================================================================

def extract_scans(db_dir: str) -> list:
    """提取所有扫描记录。先尝试 SQLite，失败则回退到原始字节提取。"""
    scans = []
    book_names = {}

    bi_path = os.path.join(db_dir, "bookInfo.db")
    if os.path.exists(bi_path):
        try:
            conn = sqlite3.connect(bi_path)
            c = conn.cursor()
            c.execute("SELECT bookid, bookname FROM bookInfo")
            for bookid, name_b64 in c.fetchall():
                try:
                    book_names[bookid] = base64.b64decode(name_b64).decode('utf-8')
                except:
                    book_names[bookid] = name_b64
            conn.close()
        except:
            pass

    for fname in os.listdir(db_dir):
        if not fname.endswith('.db') or fname == 'bookInfo.db':
            continue
        fpath = os.path.join(db_dir, fname)

        # 方法 A: SQLite 正常读取
        try:
            conn = sqlite3.connect(fpath)
            c = conn.cursor()
            c.execute("PRAGMA quick_check")
            ok = c.fetchone()[0] == 'ok'
            if ok:
                c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite%'")
                for (tbl,) in c.fetchall():
                    try:
                        c.execute(f"SELECT id, bookdata, booktime FROM [{tbl}] ORDER BY id")
                        for scan_id, data_b64, ts_str in c.fetchall():
                            try:
                                text = base64.b64decode(data_b64).decode('utf-8')
                            except:
                                text = ""
                            try:
                                ts = int(ts_str)
                            except:
                                ts = 0
                            scans.append((scan_id, text, ts, book_names.get(tbl, tbl)))
                    except:
                        pass
                conn.close()
                continue  # 成功，跳过原始提取
            conn.close()
        except:
            pass

        # 方法 B: 原始字节回退 — MTP 拷贝不完整时 SQLite 拒绝打开
        try:
            with open(fpath, 'rb') as f:
                raw = f.read()

            # 提取所有 base64 块，记录文件位置
            b64_matches = list(re.finditer(rb'[A-Za-z0-9+/=]{12,}', raw))
            # 提取所有时间戳
            ts_matches = re.findall(rb'1[7-8]\d{8}', raw)

            candidates = []
            for m in b64_matches:
                try:
                    decoded = base64.b64decode(m.group())
                    text = decoded.decode('utf-8', errors='replace')
                    # 过滤纯乱码：至少包含 2 个 CJK 或 ASCII 可读字符
                    readable = sum(1 for c in text if c.isalpha() or '一' <= c <= '鿿')
                    if readable >= 2 and len(text) >= 2:
                        candidates.append((m.start(), text))
                except:
                    pass

            timestamps = [int(t) for t in ts_matches if 1577836800 < int(t) < 1893456000]

            # 按文件位置排序，就近匹配时间戳
            candidates.sort(key=lambda x: x[0])
            book_name = book_names.get('1111-1111-1111-1111', '速记本')

            # 清理：去除 SQLite 页结构尾随垃圾
            import unicodedata
            def clean_tail(t: str) -> str:
                # 从尾部找到最后一个合理的中文/英文/标点，截断后续二进制垃圾
                for i in range(len(t) - 1, max(len(t) - 40, 0), -1):
                    c = t[i]
                    if c.isalpha() or '一' <= c <= '鿿' or c in '。，！？；：""''）】」》·…—':
                        return t[:i+1]
                return t

            candidates = [(pos, clean_tail(text)) for pos, text in candidates]

            # 为每个候选找最近的时间戳（也在文件中的位置）
            ts_positions = [(m.start(), int(m.group()))
                          for m in re.finditer(rb'1[7-8]\d{8}', raw)
                          if 1577836800 < int(m.group()) < 1893456000]
            ts_positions.sort(key=lambda x: x[0])

            used_ts = set()
            for pos, text in candidates:
                # 找最近未使用的时间戳
                best_ts = 0
                best_dist = 999999
                for ts_pos, ts_val in ts_positions:
                    if ts_val not in used_ts:
                        dist = abs(pos - ts_pos)
                        if dist < best_dist:
                            best_dist = dist
                            best_ts = ts_val
                if best_ts:
                    used_ts.add(best_ts)
                scans.append((9000 + len(scans), text, best_ts, book_name))
        except:
            pass

    return sorted(scans, key=lambda s: s[0])


def load_last_id() -> int:
    try:
        with open(STATE_FILE, 'r') as f:
            return int(f.read().strip())
    except:
        return 0


def save_last_id(scan_id: int):
    with open(STATE_FILE, 'w') as f:
        f.write(str(scan_id))


# ============================================================================
# 共读文档写入
# ============================================================================

def init_codoc(output_path: str, book_name: str):
    """初始化共读文档，写入头部元信息。"""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    if not os.path.exists(output_path):
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(f"# {book_name} 共读记录\n")
            f.write(f"# 开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"# \n")
            f.write(f"# 格式说明:\n")
            f.write(f"#   [扫描] = 笔扫描的原文段落\n")
            f.write(f"#   [感想] = 久阳的阅读反思/问题\n")
            f.write(f"#   [渡]   = AI 导读回应 (共读模式触发后写入)\n")
            f.write(f"# \n")
            f.write("=" * 60 + "\n\n")


def append_codoc(output_path: str, scan_id: int, ts: int, text: str, reflection: str = ""):
    """追加一条扫描+感想配对到共读文档。"""
    dt = datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S') if ts > 0 else "???"
    with open(output_path, 'a', encoding='utf-8') as f:
        f.write(f"---\n")
        f.write(f"### [{dt}]  #{scan_id}\n\n")
        f.write(f"[扫描]\n{text}\n\n")
        if reflection.strip():
            f.write(f"[感想]\n{reflection.strip()}\n\n")
        else:
            f.write(f"[感想]\n(未填写)\n\n")


# ============================================================================
# 交互式展示
# ============================================================================

def interactive_review(scans: list, output_path: str):
    """
    逐条展示新扫描，等待用户输入感想。
    命令: q=退出, s=跳过, Enter=跳过本条
    """
    count = 0
    for i, (scan_id, text, ts, book_name) in enumerate(scans):
        dt = datetime.fromtimestamp(ts).strftime('%H:%M:%S') if ts > 0 else "???"
        print(f"\n{'─' * 50}")
        print(f"[{i+1}/{len(scans)}]  {dt}  #{scan_id}  {book_name}")
        print(f"{'─' * 50}")
        print(f"  {text}")
        print(f"{'─' * 50}")
        print(f"  输入感想 (s=跳过 q=退出): ", end="", flush=True)

        try:
            user_input = input().strip()
        except (EOFError, KeyboardInterrupt):
            print("\n  已中断。")
            break

        if user_input.lower() == 'q':
            print(f"  已处理 {count} 条，剩余 {len(scans)-i} 条下次再处理。")
            save_last_id(scan_id - 1)  # 下次从这条开始
            break
        elif user_input.lower() == 's' or user_input == '':
            append_codoc(output_path, scan_id, ts, text, "(未填写)")
            save_last_id(scan_id)
            count += 1
        else:
            append_codoc(output_path, scan_id, ts, text, user_input)
            save_last_id(scan_id)
            count += 1
            print(f"  [v] 已保存。")

    return count


def batch_collect(scans: list, output_path: str):
    """批量模式：所有扫描直接写入，不等待用户输入。"""
    for scan_id, text, ts, book_name in scans:
        append_codoc(output_path, scan_id, ts, text, "")
        save_last_id(scan_id)
    return len(scans)


# ============================================================================
# 主流程
# ============================================================================

def rewrite_codoc(output_path: str, book_name: str, scans: list):
    """用内存中的扫描列表完全重写共读文档。scans = [(id, text, ts, book, reflection), ...]"""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(f"# {book_name} 共读记录\n")
        f.write(f"# 更新时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"# \n")
        f.write(f"# [扫描] = 笔扫描的原文段落\n")
        f.write(f"# [感想] = 久阳的阅读反思\n")
        f.write(f"# [渡]   = AI 导读回应\n")
        f.write(f"# \n")
        f.write("=" * 60 + "\n\n")

        for scan_id, text, ts, book, reflection in scans:
            dt = datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S') if ts > 0 else "???"
            f.write(f"---\n")
            f.write(f"### [{dt}]  #{scan_id}\n\n")
            f.write(f"[扫描]\n{text}\n\n")
            f.write(f"[感想]\n{reflection if reflection else '(未填写)'}\n\n")


def stdin_listener(queue, stop_event):
    """后台线程：持续监听 stdin，将用户输入放入队列。"""
    while not stop_event.is_set():
        try:
            line = input()
            if line.strip():
                queue.put(line.strip())
        except (EOFError, OSError):
            break


def loop_mode(output_path: str = None, interval: int = 15):
    """
    循环监控模式：每 interval 秒拉取笔数据。
    新增扫描自动追加到共读文档。
    用户可随时输入中文感想 → 自动匹配最近一条扫描。
    Ctrl+C 退出。
    """
    import threading
    import queue as qu

    start_time = datetime.now()
    session_scans = []  # 内存中持有全部扫描
    output = output_path
    book_name = "未知"
    input_queue = qu.Queue()
    stop_event = threading.Event()

    # 启动后台输入监听线程
    stdin_thread = threading.Thread(
        target=stdin_listener,
        args=(input_queue, stop_event),
        daemon=True
    )
    stdin_thread.start()

    print("=" * 60)
    print("  笔默 — 循环监控模式")
    print(f"  间隔: {interval}s | 启动: {start_time.strftime('%H:%M:%S')}")
    print("=" * 60)
    print()
    print("  边读边扫。直接输入中文感想，自动匹配最近一条划线。")
    print("  Ctrl+C 退出。")
    print()

    last_flush_id = 0  # 记录上次刷新到文件的最后 id

    # 清理历史临时目录
    tmp_root = tempfile.gettempdir()
    for d in os.listdir(tmp_root):
        dp = os.path.join(tmp_root, d)
        if d.startswith("bimo_") and os.path.isdir(dp):
            try:
                for f in os.listdir(dp):
                    os.unlink(os.path.join(dp, f))
                os.rmdir(dp)
            except:
                pass

    try:
        while True:
            tick = datetime.now()
            elapsed = (tick - start_time).seconds
            elapsed_str = f"{elapsed // 60}m{elapsed % 60}s"

            # ── 处理用户输入（非阻塞）──
            comments_processed = 0
            while True:
                try:
                    comment = input_queue.get_nowait()
                except qu.Empty:
                    break

                if comment.lower() == 'q':
                    raise KeyboardInterrupt

                # 找最近一条无感想的扫描
                matched = None
                for i in range(len(session_scans) - 1, -1, -1):
                    if session_scans[i][4] is None:  # reflection is None
                        matched = i
                        break

                if matched is not None:
                    sid, txt, ts, bk, _ = session_scans[matched]
                    session_scans[matched] = (sid, txt, ts, bk, comment)
                    # 立即刷新文件
                    if output:
                        rewrite_codoc(output, book_name, session_scans)
                    preview = txt[:40].replace('\n', ' ')
                    print(f"  [v] 已匹配 #{sid} | {preview}...")
                    comments_processed += 1
                else:
                    print(f"  [!] 暂无待匹配的扫描，先划几行字吧。")

            # ── 拉取笔数据 ──
            # 每次用独立时间戳目录，避免 MTP CopyHere 同名弹窗
            pull_id = datetime.now().strftime('%H%M%S_%f')[:10]
            tmp_dir = os.path.join(tempfile.gettempdir(), f"bimo_{pull_id}")
            os.makedirs(tmp_dir, exist_ok=True)

            if pull_from_pen(tmp_dir):
                all_scans = extract_scans(tmp_dir)
                # 合并新扫描：ID去重 + 文本去重（原始回退会产生重复）
                existing_ids = {s[0] for s in session_scans}
                existing_texts = {s[1].strip()[:60] for s in session_scans}  # 前60字符指纹
                new_scans = []
                for s in all_scans:
                    if s[0] not in existing_ids:
                        text_key = s[1].strip()[:60]
                        if text_key not in existing_texts:
                            new_scans.append(s)
                            existing_texts.add(text_key)

                if new_scans:
                    book_name = new_scans[0][3] if new_scans else book_name
                    if output is None:
                        os.makedirs(CODOC_PATH, exist_ok=True)
                        output = output_path or os.path.join(
                            CODOC_PATH,
                            f"{book_name}_{start_time.strftime('%Y-%m-%d')}.txt"
                        )

                    for s in new_scans:
                        # (id, text, ts, book, reflection=None)
                        session_scans.append((s[0], s[1], s[2], s[3], None))
                        save_last_id(s[0])

                    session_scans.sort(key=lambda x: x[0])

                    # 刷新文件
                    rewrite_codoc(output, book_name, session_scans)

                    # 显示新增
                    for s in new_scans:
                        preview = s[1][:60].replace('\n', ' ') + ("..." if len(s[1]) > 60 else "")
                        print(f"  [{tick.strftime('%H:%M:%S')}] #{s[0]} | {preview}")

                    total = len(session_scans)
                    filled = sum(1 for s in session_scans if s[4] is not None)
                    print(f"  --- {len(new_scans)} 条新增 | 共 {total} 条 ({filled} 条有感想) | {elapsed_str} ---")

            # 状态行 (无新扫描时显示)
            if not locals().get('new_scans'):
                total = len(session_scans)
                filled = sum(1 for s in session_scans if s[4] is not None)
                if total > 0:
                    print(f"  [{tick.strftime('%H:%M:%S')}] 等待扫描... | {total} 条 ({filled} 条有感想) | {elapsed_str}", end="\r", flush=True)
                else:
                    print(f"  [{tick.strftime('%H:%M:%S')}] 等待扫描... | {elapsed_str}", end="\r", flush=True)

            time.sleep(interval)

    except KeyboardInterrupt:
        stop_event.set()
        print(f"\n\n{'=' * 60}")
        print(f"  监控结束。")
        total = len(session_scans)
        filled = sum(1 for s in session_scans if s[4] is not None)
        print(f"  共收录 {total} 条扫描，其中 {filled} 条有感想。")
        if output:
            rewrite_codoc(output, book_name, session_scans)
            print(f"  共读文档: {output}")
        print(f"  在对话中输入 '1' → 渡进入共读模式")
        print(f"{'=' * 60}")
    return 0


def main():
    import argparse
    parser = argparse.ArgumentParser(description="笔默有线阅读原型")
    parser.add_argument("--batch", action="store_true", help="批量模式（不逐条交互）")
    parser.add_argument("--loop", "-l", action="store_true", help="循环监控模式（边读边记）")
    parser.add_argument("--interval", "-i", type=int, default=15, help="循环间隔/秒（默认15）")
    parser.add_argument("--output", "-o", type=str, help="共读文档输出路径")
    args = parser.parse_args()

    # ── 循环模式 ──
    if args.loop:
        return loop_mode(args.output, args.interval)

    # ── 单次模式 ──
    # 1. 拉取笔数据
    tmp_dir = os.path.join(tempfile.gettempdir(), "bimo_tmp")
    os.makedirs(tmp_dir, exist_ok=True)
    for f in os.listdir(tmp_dir):
        try: os.unlink(os.path.join(tmp_dir, f))
        except: pass

    print("=" * 60)
    print("  笔默 — 有线阅读原型")
    print("=" * 60)
    print()
    print("[1/3] 从笔拉取扫描数据...")
    if not pull_from_pen(tmp_dir):
        print("  [FAIL] 未检测到笔。请确认 USB 已连接且笔已开机。")
        print("  提示: 文件资源管理器中应能看到 ScanOS/YX-M2。")
        return 1
    print("  [v] 数据已拉取")

    # 2. 解析
    print("[2/3] 解析扫描记录...")
    all_scans = extract_scans(tmp_dir)
    if not all_scans:
        print("  笔中暂无扫描记录。")
        return 0

    last_id = load_last_id()
    new_scans = [s for s in all_scans if s[0] > last_id]
    print(f"  共 {len(all_scans)} 条 / 新增 {len(new_scans)} 条")

    if not new_scans:
        print("  [EMPTY] 无新增。再划几行字吧。")
        return 0

    # 确定输出路径
    book_name = new_scans[0][3] if new_scans else "未知"
    output_path = args.output or os.path.join(
        CODOC_PATH,
        f"{book_name}_{datetime.now().strftime('%Y-%m-%d')}.txt"
    )
    init_codoc(output_path, book_name)

    # 3. 写入
    print(f"[3/3] {'交互式记录' if not args.batch else '批量导入'} -> {output_path}")
    print(f"  (共读文档路径: {output_path})")
    print()

    if args.batch:
        cnt = batch_collect(new_scans, output_path)
    else:
        cnt = interactive_review(new_scans, output_path)

    print(f"\n{'=' * 60}")
    print(f"  完成: {cnt} 条已写入 共读文档")
    print(f"  下次在对话中输入 '1' 或直接回车 → 渡进入共读模式")
    print(f"{'=' * 60}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
