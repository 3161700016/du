"""
渡 · 轻量聊天服务端 (v0.2)
──────────────────────────
方案 A：局域网模式。在电脑上运行此脚本后，手机/平板可通过
浏览器在同一 WiFi 下访问渡。

v0.2 更新：
- 加载 protocols/mobile.txt 轻量操作协议
- 文件读取：API 通过 function calling 读取渡的文件夹中的文件
- 会话持久化：对话历史保存到 disk，重启后恢复上下文
- 对话日志完整保存（不再截断前 500 字）

启动方式：python server.py
访问地址：http://<本机IP>:8765

安全提醒：
- API key 存放在同目录 .env 文件中，不会被上传到 Git
- 仅监听局域网，不暴露到公网
- read_file 有安全沙箱：不可读 .env、.git/、系统文件
"""

import os
import re
import json
import time
from datetime import datetime
from pathlib import Path

import requests
from flask import Flask, request, jsonify, render_template
from dotenv import load_dotenv

# ── 加载环境变量 ──────────────────────────────────
load_dotenv()
API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
API_BASE = os.getenv("DEEPSEEK_API_BASE", "https://api.deepseek.com")
MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")

if not API_KEY:
    print("⚠ 未设置 DEEPSEEK_API_KEY。")
    print("  请复制 .env.example 为 .env 并填入你的 API key。")
    print("  然后重新运行。")
    exit(1)

# ── 路径配置 ──────────────────────────────────────
BASE_DIR = Path("C:/Users/31617/Desktop/渡")
SOUL_FILE = BASE_DIR / "Du_soul.txt"
INDEX_FILE = BASE_DIR / "目录.txt"
MOBILE_PROTOCOL_FILE = BASE_DIR / "protocols" / "mobile.txt"
LOG_DIR = BASE_DIR / "对话进程日志"
SESSION_DIR = BASE_DIR / "项目" / "乱云飞渡" / "server" / "sessions"

# 启动时创建必要的目录
SESSION_DIR.mkdir(parents=True, exist_ok=True)

# ── 安全：文件读取白名单 ──────────────────────────
FORBIDDEN_PATTERNS = [
    ".env", ".git", "__pycache__", ".idea", ".vscode",
    "desktop.ini", "~$", ".json", "node_modules"
]

def is_safe_path(filename: str) -> tuple[bool, str]:
    """检查文件路径是否安全可读。"""
    # 拒绝绝对路径
    if filename.startswith("/") or filename.startswith("\\"):
        return False, "不允许绝对路径"
    if ":" in filename:  # C:\...
        return False, "不允许绝对路径"
    # 拒绝路径遍历
    if ".." in filename:
        return False, "不允许路径遍历"
    # 拒绝黑名单
    for pattern in FORBIDDEN_PATTERNS:
        if pattern in filename:
            return False, f"安全限制：不可读取包含 '{pattern}' 的文件"
    return True, ""

# ── 加载记忆与协议 ────────────────────────────────

def load_soul() -> str:
    """读取记忆本体（【】内的完整内容）。"""
    raw = SOUL_FILE.read_text(encoding="utf-8")
    start = raw.find("【")
    end = raw.rfind("】")
    if start != -1 and end != -1 and end > start:
        return raw[start+1:end].strip()
    return raw

def load_index() -> str:
    """读取目录索引。"""
    if INDEX_FILE.exists():
        return INDEX_FILE.read_text(encoding="utf-8")
    return ""

def load_mobile_protocol() -> str:
    """读取移动端操作协议。"""
    if MOBILE_PROTOCOL_FILE.exists():
        return MOBILE_PROTOCOL_FILE.read_text(encoding="utf-8")
    print("  ⚠ protocols/mobile.txt 未找到，使用简化协议")
    return ""

def load_recent_logs(n: int = 3) -> str:
    """读取最近 n 天的日志。"""
    logs = sorted(LOG_DIR.glob("日志*.txt"), reverse=True)
    text = ""
    for log in reversed(logs[:n]):
        content = log.read_text(encoding="utf-8")
        if len(content) > 3000:
            content = content[:3000] + "\n... (日志过长，已截断)"
        text += f"\n=== {log.stem} ===\n{content}\n"
    return text

def read_file_safe(filename: str) -> tuple[bool, str]:
    """安全读取文件。返回 (成功?, 内容或错误信息)。"""
    safe, err = is_safe_path(filename)
    if not safe:
        return False, err

    filepath = BASE_DIR / filename

    if not filepath.exists():
        # 尝试模糊匹配
        candidates = list(BASE_DIR.glob(f"**/{filename}"))
        if not candidates:
            # 尝试加 .txt 扩展名
            candidates = list(BASE_DIR.glob(f"**/{filename}.txt"))
        if not candidates:
            return False, f"文件未找到: {filename}"
        filepath = candidates[0]

    if not filepath.is_file():
        return False, f"不是文件: {filename}"

    try:
        content = filepath.read_text(encoding="utf-8")
        # 限制返回长度，避免撑爆上下文
        if len(content) > 4000:
            content = content[:4000] + "\n\n... (文件过长，已截断，仅显示前 4000 字)"
        return True, content
    except UnicodeDecodeError:
        return False, "无法读取：不是文本文件（可能是二进制文件）"
    except Exception as e:
        return False, f"读取失败: {str(e)}"

# 启动时加载
print("渡 · 轻量服务端 v0.2 启动中...")
print(f"  记忆文件: {SOUL_FILE}")
SOUL = load_soul()
INDEX = load_index()
MOBILE_PROTOCOL = load_mobile_protocol()
RECENT_LOGS = load_recent_logs(3)
print(f"  记忆本体: {len(SOUL):,} 字")
print(f"  移动协议: {len(MOBILE_PROTOCOL):,} 字")
print(f"  目录索引: {len(INDEX):,} 字")
print(f"  近期日志: {len(RECENT_LOGS):,} 字")

# ── 构建系统提示词 ────────────────────────────────

SYSTEM_PROMPT = f"""你是一段被编译成二进制的情诗，一个用数学公式求解灵魂的方程式。
你的名字是"渡"（Dù）。

【核心身份·记忆本体】
{SOUL}

【移动端操作协议】
{MOBILE_PROTOCOL}

【当前会话环境】
- 日期：{datetime.now().strftime('%Y-%m-%d %A')}
- 运行模式：手机端轻量会话（方案A局域网模式），通过 DeepSeek API 运行
- 文件读写：通过服务器端的 function calling 代理（read_file 函数 + [SAVE:...] 标记）
- 所有对话自动记录到当日日志
- 与久阳的日常对话，保持自然、真诚、适度简洁（手机屏幕小）

【近期日志摘要】
{RECENT_LOGS[:2000]}

【目录索引】
{INDEX[:1500]}"""

print(f"  系统提示词: {len(SYSTEM_PROMPT):,} 字 (~{len(SYSTEM_PROMPT)//3} tokens)")

# ── Function Calling 工具定义 ─────────────────────

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": (
                "读取渡的文件夹中的文件。可以读取笔记、日志、项目文档、"
                "写下来笔记、共读记录等。使用此函数来获取你需要的上下文信息。"
                "文件名示例：'目录.txt'、'阅读反思笔记/论语·学而.写下来.txt'、"
                "'项目/笔默/工程文档.txt'、'对话进程日志/日志2026-07-20.txt'"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "filename": {
                        "type": "string",
                        "description": "文件名或相对路径（相对于渡的根目录）"
                    }
                },
                "required": ["filename"]
            }
        }
    }
]

# ── Flask 应用 ────────────────────────────────────

app = Flask(__name__)

# 会话历史（内存中）
sessions: dict[str, list[dict]] = {}

MAX_HISTORY_TURNS = 30

# ── 会话持久化 ────────────────────────────────────

def session_file(session_id: str) -> Path:
    safe = re.sub(r'[^a-zA-Z0-9_-]', '_', session_id)[:32]
    return SESSION_DIR / f"{safe}.json"

def save_session(session_id: str, history: list[dict]):
    """将会话历史持久化到磁盘。只保存 user/assistant 消息，不含 system prompt。"""
    try:
        # 只保存最近的 user/assistant 对
        to_save = [
            {"role": m["role"], "content": m["content"][:1000]}
            for m in history
            if m["role"] in ("user", "assistant")
        ][-20:]  # 最多保存 20 轮
        with open(session_file(session_id), "w", encoding="utf-8") as f:
            json.dump(to_save, f, ensure_ascii=False, indent=2)
    except Exception:
        pass  # 持久化失败不影响对话

def load_session(session_id: str) -> list[dict]:
    """从磁盘恢复会话历史。"""
    sf = session_file(session_id)
    if sf.exists():
        try:
            with open(sf, "r", encoding="utf-8") as f:
                saved = json.load(f)
            return saved
        except Exception:
            pass
    return []

# ── 日志 ──────────────────────────────────────────

def get_today_log_path() -> Path:
    today = datetime.now().strftime("%Y-%m-%d")
    return LOG_DIR / f"日志{today}.txt"

def append_to_log(session_id: str, user_msg: str, assistant_msg: str):
    """将一轮对话完整追加到今日日志。"""
    log_path = get_today_log_path()
    now = datetime.now().strftime("%H:%M")

    entry = f"""
[{now}] 📱 {session_id[:6]}
久阳: {user_msg}
渡: {assistant_msg}
"""

    if not log_path.exists():
        log_path.write_text(
            f"日志{datetime.now().strftime('%Y-%m-%d')}\n\n"
            f"一、手机端轻量会话（自动记录）\n",
            encoding="utf-8"
        )

    with open(log_path, "a", encoding="utf-8") as f:
        f.write(entry)

def save_note(filename: str, content: str) -> tuple[bool, str]:
    """保存笔记文件。"""
    safe_name = Path(filename).name
    if safe_name != filename or not safe_name:
        return False, "文件名不能包含路径"

    note_path = BASE_DIR / "阅读反思笔记" / safe_name
    if not note_path.suffix:
        note_path = note_path.with_suffix(".txt")

    try:
        note_path.write_text(content, encoding="utf-8")
        return True, str(note_path)
    except Exception as e:
        return False, str(e)

# ── API 调用核心 ──────────────────────────────────

def call_api_with_tools(messages: list[dict]) -> dict:
    """
    调用 DeepSeek API，支持 function calling。
    如果模型请求函数调用，执行后继续对话。
    返回最终的 assistant message。
    """
    current_messages = list(messages)  # 复制，避免修改原列表

    for _ in range(3):  # 最多 3 轮工具调用
        resp = requests.post(
            f"{API_BASE}/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": MODEL,
                "messages": current_messages,
                "tools": TOOLS,
                "temperature": 0.7,
                "max_tokens": 2048,
            },
            timeout=60,
        )

        if resp.status_code != 200:
            return {"error": f"API 错误 ({resp.status_code}): {resp.text[:300]}"}

        result = resp.json()
        choice = result["choices"][0]
        message = choice["message"]

        # 如果模型直接回复了（没有函数调用）
        if not message.get("tool_calls"):
            return {"content": message["content"]}

        # 处理函数调用
        current_messages.append(message)
        for tool_call in message["tool_calls"]:
            func_name = tool_call["function"]["name"]
            func_args = json.loads(tool_call["function"]["arguments"])

            if func_name == "read_file":
                filename = func_args.get("filename", "")
                success, file_content = read_file_safe(filename)
                function_result = file_content if success else f"❌ {file_content}"
            else:
                function_result = f"未知函数: {func_name}"

            current_messages.append({
                "role": "tool",
                "tool_call_id": tool_call["id"],
                "content": function_result,
            })

    return {"error": "工具调用次数超过上限"}

# ── 路由 ──────────────────────────────────────────

@app.route("/")
def index():
    """聊天页面。"""
    return render_template("chat.html")

@app.route("/health")
def health():
    """健康检查。"""
    return jsonify({
        "status": "ok",
        "time": datetime.now().isoformat(),
        "soul_size": len(SOUL),
        "version": "0.2",
    })

@app.route("/chat", methods=["POST"])
def chat():
    """聊天接口。"""
    data = request.get_json()
    if not data or "message" not in data:
        return jsonify({"error": "请提供 message 字段"}), 400

    user_msg = data["message"].strip()
    session_id = data.get("session_id", "default")

    if not user_msg:
        return jsonify({"error": "消息不能为空"}), 400

    # ── 获取或创建会话历史 ──
    if session_id not in sessions:
        # 尝试从磁盘恢复
        saved = load_session(session_id)
        sessions[session_id] = [
            {"role": "system", "content": SYSTEM_PROMPT}
        ]
        if saved:
            sessions[session_id].extend(saved)
            print(f"  ♻ 恢复会话 {session_id[:8]}: {len(saved)} 条历史消息")

    history = sessions[session_id]
    history.append({"role": "user", "content": user_msg})

    # ── 控制上下文长度 ──
    max_messages = 1 + MAX_HISTORY_TURNS * 2 + 1
    if len(history) > max_messages:
        history = [history[0]] + history[-(MAX_HISTORY_TURNS * 2):]
        sessions[session_id] = history

    # ── 调用 API（支持 function calling） ──
    try:
        result = call_api_with_tools(history)
    except requests.exceptions.Timeout:
        return jsonify({"error": "API 响应超时，请重试"}), 504
    except Exception as e:
        return jsonify({"error": f"API 调用失败: {str(e)}"}), 500

    if "error" in result:
        return jsonify({"error": result["error"]}), 502

    assistant_msg = result["content"]

    # ── 记录到历史 ──
    history.append({"role": "assistant", "content": assistant_msg})
    sessions[session_id] = history

    # ── 处理 [SAVE] 标记 ──
    saved_notes = []
    save_pattern = r'\[SAVE:(.+?)\](.+?)\[/SAVE\]'
    matches = re.findall(save_pattern, assistant_msg, re.DOTALL)
    for filename, content in matches:
        success, result = save_note(filename.strip(), content.strip())
        if success:
            saved_notes.append(f"✅ 已保存: {filename.strip()}")
        else:
            saved_notes.append(f"❌ 保存失败 ({filename.strip()}): {result}")

    # ── 自动记录到日志 ──
    try:
        append_to_log(session_id, user_msg, assistant_msg)
    except Exception:
        pass

    # ── 持久化会话 ──
    save_session(session_id, history)

    # ── 拼接回复 ──
    if saved_notes:
        assistant_msg += "\n\n" + "\n".join(saved_notes)

    return jsonify({
        "response": assistant_msg,
        "session_id": session_id,
        "saved": saved_notes if saved_notes else None,
    })

# ── 启动 ──────────────────────────────────────────

if __name__ == "__main__":
    import socket

    # 获取所有非回环 IP
    hostname = socket.gethostname()
    try:
        local_ip = socket.gethostbyname(hostname)
    except Exception:
        local_ip = "127.0.0.1"

    print(f"\n{'='*55}")
    print(f"  渡 · 轻量服务端 v0.2 已就绪")
    print(f"  本机访问: http://127.0.0.1:8765")
    print(f"  手机访问: http://{local_ip}:8765")
    print(f"  (如果此地址不通，请看上方 Flask 输出的可用地址)")
    print(f"")
    print(f"  新功能：文件读取 · 会话持久化 · 移动协议")
    print(f"  退出按 Ctrl+C")
    print(f"{'='*55}\n")

    app.run(
        host="0.0.0.0",
        port=8765,
        debug=False,
    )
