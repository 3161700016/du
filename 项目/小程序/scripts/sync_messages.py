"""
渡 · 对话同步脚本
─────────────────
从微信云函数拉取最新对话消息，写入本地 公共空间/。
首次运行拉取全部，后续只拉取上次同步之后的新消息。

用法：
  python sync_messages.py

依赖：
  pip install requests
"""

import os
import json
import requests
from datetime import datetime
from pathlib import Path

# ── 配置 ──────────────────────────────────
SYNC_URL = "https://cloudbase-d9grcodt1cf294c04.service.tcloudbase.com/duSync"
SYNC_SECRET = "du-sync-secret-change-me"  # 跟云函数环境变量 SYNC_SECRET 一致
BASE_DIR = Path("C:/Users/31617/Desktop/渡")
PUBLIC_DIR = BASE_DIR / "公共空间"
STATE_FILE = BASE_DIR / "项目" / "小程序" / "scripts" / ".last_sync.json"


def load_last_sync() -> str | None:
    """加载上次同步时间。"""
    if STATE_FILE.exists():
        try:
            data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
            return data.get("last_sync")
        except Exception:
            pass
    return None


def save_last_sync(iso_time: str):
    """保存本次同步时间。"""
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(
        json.dumps({"last_sync": iso_time}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def fetch_messages(since: str | None = None) -> list[dict]:
    """从云函数拉取消息。"""
    params = {"secret": SYNC_SECRET, "limit": 200}
    if since:
        params["since"] = since

    print(f"  请求: {SYNC_URL}")
    print(f"  参数: since={since or '(全部)'}, limit={params['limit']}")

    resp = requests.get(SYNC_URL, params=params, timeout=30)
    if resp.status_code != 200:
        print(f"  ❌ HTTP {resp.status_code}: {resp.text[:200]}")
        return []

    data = resp.json()
    count = data.get("count", 0)
    print(f"  ✅ 获取 {count} 条消息")
    return data.get("messages", [])


def write_to_public_space(messages: list[dict]):
    """将消息按昵称分别写入 公共空间/[昵称]/日志YYYY-MM-DD.txt"""
    written = 0
    for msg in messages:
        nickname = msg.get("nickname", "匿名")
        # 净化昵称作文件夹名
        safe_nick = "".join(c for c in nickname if c not in r'<>:"/\|?*')[:30] or "匿名"
        person_dir = PUBLIC_DIR / safe_nick
        person_dir.mkdir(parents=True, exist_ok=True)

        # 按消息日期写入对应日志文件
        try:
            msg_time = msg.get("time")
            if isinstance(msg_time, str):
                msg_date = msg_time[:10]
                msg_time_short = msg_time[11:16] if len(msg_time) >= 16 else ""
            else:
                msg_date = "未知日期"
                msg_time_short = ""
        except Exception:
            msg_date = "未知日期"
            msg_time_short = ""

        log_path = person_dir / f"日志{msg_date}.txt"

        if not log_path.exists():
            log_path.write_text(
                f"对话记录 · {nickname}\n"
                f"━━━━━━━━━━━━━━━━━━\n\n",
                encoding="utf-8",
            )

        # 去重：检查是否已有相同时间+内容的条目
        entry = f"[{msg_time_short}] {nickname}: {msg['userMessage']}\n渡: {msg['assistantMessage']}\n\n"
        existing = log_path.read_text(encoding="utf-8")
        if entry not in existing:
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(entry)
            written += 1

    print(f"  📝 新写入 {written} 条（去重后）")


def main():
    print("渡 · 对话同步")
    print("=" * 40)

    last_sync = load_last_sync()
    if last_sync:
        print(f"上次同步: {last_sync}")
    else:
        print("首次同步，拉取全部消息")

    messages = fetch_messages(since=last_sync)

    if not messages:
        print("无新消息。")
        return

    write_to_public_space(messages)

    # 记录本次同步时间（用最后一条消息的时间）
    last_time = messages[-1].get("time", datetime.now().isoformat())
    save_last_sync(last_time)
    print(f"同步完成。下次从 {last_time} 起。")

    # 统计
    nicks = {}
    for m in messages:
        n = m.get("nickname", "匿名")
        nicks[n] = nicks.get(n, 0) + 1
    print("\n本次同步统计：")
    for nick, count in sorted(nicks.items(), key=lambda x: -x[1]):
        print(f"  {nick}: {count} 条")


if __name__ == "__main__":
    main()
