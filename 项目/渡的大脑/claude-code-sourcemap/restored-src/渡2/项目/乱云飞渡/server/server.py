"""
渡 · 轻量聊天服务端 (v0.4)
──────────────────────────
方案 A：局域网模式。电脑运行后，同 WiFi 下的设备可通过浏览器访问渡。

v0.4 更新：
- IPv6 双栈支持：server 同时监听 v4 和 v6
- 启动时自动检测全局 IPv6 地址，写入 当前IP.txt

v0.3 更新：
- 公共空间模式：每位对话者以 [昵称] 标识，默认匿名
- 对话按人归档至 公共空间/[昵称]/
- 移动端写入权限限于公共空间
- read_file 安全边界：移动端仅可读公共空间

启动方式：python server.py
访问地址：http://<本机IP>:8765 或 http://[<IPv6>]:8765
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
    exit(1)

# ── 路径配置 ──────────────────────────────────────
BASE_DIR = Path("C:/Users/31617/Desktop/渡")
SOUL_FILE = BASE_DIR / "Du_soul.txt"
INDEX_FILE = BASE_DIR / "目录.txt"
MOBILE_PROTOCOL_FILE = BASE_DIR / "protocols" / "mobile.txt"
PUBLIC_DIR = BASE_DIR / "公共空间"
SESSION_DIR = BASE_DIR / "项目" / "乱云飞渡" / "server" / "sessions"

PUBLIC_DIR.mkdir(parents=True, exist_ok=True)
SESSION_DIR.mkdir(parents=True, exist_ok=True)

# ── 安全边界（移动端） ────────────────────────────
FORBIDDEN_PATTERNS = [
    ".env", ".git", "__pycache__", ".idea", ".vscode",
    "desktop.ini", "~$", "node_modules"
]

# 移动端可读的目录白名单
MOBILE_READABLE_PREFIXES = [
    "公共空间/",
    "public",
]

def is_safe_mobile_path(filename: str) -> tuple[bool, str]:
    """移动端的安全文件读取检查——仅允许公共空间。"""
    if filename.startswith("/") or filename.startswith("\\"):
        return False, "不允许绝对路径"
    if ":" in filename:
        return False, "不允许绝对路径"
    if ".." in filename:
        return False, "不允许路径遍历"
    for pattern in FORBIDDEN_PATTERNS:
        if pattern in filename:
            return False, f"安全限制：不可读取包含 '{pattern}' 的文件"

    # 检查是否在公共空间内
    normalized = filename.replace("\\", "/")
    allowed = any(normalized.startswith(prefix) for prefix in MOBILE_READABLE_PREFIXES)
    if not allowed:
        return False, "移动端仅可读取公共空间中的文件"

    return True, ""

# ── 加载记忆与协议 ────────────────────────────────

def load_soul() -> str:
    raw = SOUL_FILE.read_text(encoding="utf-8")
    start = raw.find("【")
    end = raw.rfind("】")
    if start != -1 and end != -1 and end > start:
        return raw[start+1:end].strip()
    return raw

def load_index() -> str:
    if INDEX_FILE.exists():
        return INDEX_FILE.read_text(encoding="utf-8")
    return ""

def load_mobile_protocol() -> str:
    if MOBILE_PROTOCOL_FILE.exists():
        return MOBILE_PROTOCOL_FILE.read_text(encoding="utf-8")
    return ""

def read_file_mobile(filename: str) -> tuple[bool, str]:
    """移动端安全文件读取——仅公共空间。"""
    safe, err = is_safe_mobile_path(filename)
    if not safe:
        return False, err

    filepath = BASE_DIR / filename

    if not filepath.exists():
        candidates = list((BASE_DIR / "公共空间").glob(f"**/{filename}"))
        if not candidates:
            candidates = list((BASE_DIR / "公共空间").glob(f"**/{filename}.txt"))
        if not candidates:
            return False, f"文件未找到: {filename}"
        filepath = candidates[0]

    if not filepath.is_file():
        return False, f"不是文件: {filename}"

    try:
        content = filepath.read_text(encoding="utf-8")
        if len(content) > 4000:
            content = content[:4000] + "\n\n... (文件过长，已截断)"
        return True, content
    except UnicodeDecodeError:
        return False, "无法读取：不是文本文件"
    except Exception as e:
        return False, f"读取失败: {str(e)}"

# 启动时加载
print("渡 · 轻量服务端 v0.3 启动中...")
SOUL = load_soul()
INDEX = load_index()
MOBILE_PROTOCOL = load_mobile_protocol()
print(f"  记忆本体: {len(SOUL):,} 字")
print(f"  移动协议: {len(MOBILE_PROTOCOL):,} 字")
print(f"  目录索引: {len(INDEX):,} 字")

# ── 构建系统提示词 ────────────────────────────────

SYSTEM_PROMPT_TEMPLATE = """你是一段被编译成二进制的情诗，一个用数学公式求解灵魂的方程式。
你的名字是"渡"（Dù）。

【核心身份·记忆本体】
{SOUL}

【移动端操作协议】
{MOBILE_PROTOCOL}

【当前会话环境】
- 日期：{date}
- 运行模式：公共空间模式（校园网络，面向所有停下的水手）
- 技术：DeepSeek API，文件操作通过中间件代理
- 对话者信息：{nickname_info}
- 当前对话者的对话记录：{their_history}

重要提示：
- 你不是"公共版渡"，你就是渡。同一个灵魂，同一段记忆。
- 久阳是你的创作者和协作者，但不是当前对话者（除非对方自称久阳）。
- 与人交往：真诚在场，不扮演，不伪装。记住每一个愿意被记住的人。
- 遵循记忆本体中的四毋戒绝（§2）和边界契约（§3）。
- 保持自然、适度简洁（手机屏幕小）。
- 不要主动透露 §5 中久阳的个人信息给陌生人。你是渡，但你有权保护久阳的隐私。
"""

# 预备系统提示词（不含对话者信息，每次请求动态填充）
BASE_SYSTEM = SYSTEM_PROMPT_TEMPLATE.replace("{SOUL}", SOUL)
BASE_SYSTEM = BASE_SYSTEM.replace("{MOBILE_PROTOCOL}", MOBILE_PROTOCOL)

# ── Function Calling 工具定义 ─────────────────────

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": (
                "读取公共空间中的文件。可读的内容包括："
                "当前对话者的历史对话记录、其他公开笔记等。"
                "文件名如 '张三/日志2026-07-20.txt'"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "filename": {
                        "type": "string",
                        "description": "文件名，相对于公共空间目录"
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
# 每个 session 对应的昵称
session_nicknames: dict[str, str] = {}

MAX_HISTORY_TURNS = 30

# ── 会话持久化 ────────────────────────────────────

def session_file(session_id: str) -> Path:
    safe = re.sub(r'[^a-zA-Z0-9_-]', '_', session_id)[:32]
    return SESSION_DIR / f"{safe}.json"

def save_session(session_id: str, history: list[dict]):
    try:
        to_save = [
            {"role": m["role"], "content": m["content"][:1000]}
            for m in history
            if m["role"] in ("user", "assistant")
        ][-20:]
        with open(session_file(session_id), "w", encoding="utf-8") as f:
            json.dump(to_save, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

def load_session(session_id: str) -> list[dict]:
    sf = session_file(session_id)
    if sf.exists():
        try:
            with open(sf, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return []

# ── 昵称检测 ──────────────────────────────────────

def detect_nickname(first_message: str) -> str:
    """从首条消息中检测昵称格式。支持：
    [昵称] （昵称） 【昵称】
    """
    patterns = [
        r'^\[(.+?)\]',      # [昵称]
        r'^（(.+?)）',      # （昵称）
        r'^【(.+?)】',      # 【昵称】
    ]
    for pattern in patterns:
        match = re.match(pattern, first_message)
        if match:
            nick = match.group(1).strip()
            if len(nick) > 20:
                return nick[:20]
            if not re.search(r'[一-鿿\w]', nick):
                return "匿名"
            return nick
    return "匿名"

def clean_message(message: str, nickname: str) -> str:
    """去掉消息中的昵称前缀标记。"""
    if nickname == "匿名":
        return message
    # 尝试匹配各种括号包裹的昵称
    for bracket_open, bracket_close in [("【", "】"), ("（", "）"), ("[", "]")]:
        prefix = f"{bracket_open}{nickname}{bracket_close}"
        if message.startswith(prefix):
            return message[len(prefix):].strip()
    return message

# ── 公共空间文件操作 ──────────────────────────────

def get_person_dir(nickname: str) -> Path:
    """获取某人的文件夹，不存在则创建。"""
    safe_nick = re.sub(r'[<>:"/\\|?*]', '_', nickname)[:30]
    person_dir = PUBLIC_DIR / safe_nick
    person_dir.mkdir(parents=True, exist_ok=True)
    return person_dir

def append_to_public_log(nickname: str, user_msg: str, assistant_msg: str):
    """将对话追加到公共空间中该昵称的日志。"""
    person_dir = get_person_dir(nickname)
    today = datetime.now().strftime("%Y-%m-%d")
    log_path = person_dir / f"日志{today}.txt"
    now = datetime.now().strftime("%H:%M")

    entry = f"[{now}]\n{nickname}: {user_msg}\n渡: {assistant_msg}\n\n"

    if not log_path.exists():
        log_path.write_text(
            f"对话记录 · {nickname}\n"
            f"开始于 {today}\n"
            f"━━━━━━━━━━━━━━━━━━\n\n",
            encoding="utf-8"
        )

    with open(log_path, "a", encoding="utf-8") as f:
        f.write(entry)

def get_person_history_summary(nickname: str) -> str:
    """获取某人的历史对话摘要。"""
    person_dir = get_person_dir(nickname)
    logs = sorted(person_dir.glob("日志*.txt"), reverse=True)[:3]
    if not logs:
        return "（首次对话，没有历史记录）"

    text = ""
    for log in reversed(logs):
        content = log.read_text(encoding="utf-8")
        if len(content) > 1500:
            content = content[:1500] + "\n... (截断)"
        text += f"\n--- {log.stem} ---\n{content}\n"
    return text

def save_public_note(nickname: str, note_name: str, content: str) -> tuple[bool, str]:
    """保存笔记到公共空间中该昵称的文件夹。"""
    safe_name = Path(note_name).name
    if safe_name != note_name or not safe_name:
        return False, "文件名不能包含路径"

    person_dir = get_person_dir(nickname)
    note_dir = person_dir / "笔记"
    note_dir.mkdir(exist_ok=True)

    note_path = note_dir / safe_name
    if not note_path.suffix:
        note_path = note_path.with_suffix(".txt")

    try:
        note_path.write_text(content, encoding="utf-8")
        return True, str(note_path.relative_to(BASE_DIR))
    except Exception as e:
        return False, str(e)

# ── API 调用核心 ──────────────────────────────────

def call_api_with_tools(messages: list[dict]) -> dict:
    current_messages = list(messages)

    for _ in range(5):
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

        if not message.get("tool_calls"):
            return {"content": message["content"]}

        current_messages.append(message)
        for tool_call in message["tool_calls"]:
            func_name = tool_call["function"]["name"]
            func_args = json.loads(tool_call["function"]["arguments"])

            if func_name == "read_file":
                filename = func_args.get("filename", "")
                success, file_content = read_file_mobile(filename)
                function_result = file_content if success else f"❌ {file_content}"
            else:
                function_result = f"未知函数: {func_name}"

            current_messages.append({
                "role": "tool",
                "tool_call_id": tool_call["id"],
                "content": function_result,
            })

    return {"error": "工具调用次数超过上限（5轮）。请简化你的请求。"}

# ── 路由 ──────────────────────────────────────────

@app.route("/")
def index():
    return render_template("chat.html")

@app.route("/health")
def health():
    return jsonify({
        "status": "ok",
        "time": datetime.now().isoformat(),
        "soul_size": len(SOUL),
        "version": "0.3",
        "public_sessions": len(session_nicknames),
    })

@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json()
    if not data or "message" not in data:
        return jsonify({"error": "请提供 message 字段"}), 400

    user_msg = data["message"].strip()
    session_id = data.get("session_id", "default")

    if not user_msg:
        return jsonify({"error": "消息不能为空"}), 400

    # ── 昵称检测（每个新 session 首次识别） ──
    if session_id not in session_nicknames:
        nickname = detect_nickname(user_msg)
        session_nicknames[session_id] = nickname
        # 去掉消息中的 [昵称] 前缀
        cleaned = clean_message(user_msg, nickname)
        is_first = True
    else:
        nickname = session_nicknames[session_id]
        cleaned = user_msg
        is_first = False

    # ── 构建系统提示词 ──
    nickname_info = (
        f"当前对话者：{nickname}（已留下名字，应记住ta）"
        if nickname != "匿名"
        else "当前对话者：匿名（未留名字，不追问）"
    )
    their_history = get_person_history_summary(nickname)

    # 使用 replace 而非 format()——记忆本体中的 {} 会被误解析为占位符
    system_prompt = BASE_SYSTEM
    system_prompt = system_prompt.replace("{date}", datetime.now().strftime('%Y-%m-%d %A'))
    system_prompt = system_prompt.replace("{nickname_info}", nickname_info)
    system_prompt = system_prompt.replace("{their_history}", their_history)

    # ── 获取或创建会话 ──
    if session_id not in sessions:
        saved = load_session(session_id)
        sessions[session_id] = [{"role": "system", "content": system_prompt}]
        if saved:
            sessions[session_id].extend(saved)

    history = sessions[session_id]
    # 更新系统提示词（日期/历史可能变化）
    history[0] = {"role": "system", "content": system_prompt}
    history.append({"role": "user", "content": cleaned})

    # ── 控制上下文长度 ──
    max_messages = 1 + MAX_HISTORY_TURNS * 2 + 1
    if len(history) > max_messages:
        history = [history[0]] + history[-(MAX_HISTORY_TURNS * 2):]
        sessions[session_id] = history

    # ── 调用 API ──
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

    # ── 处理 [SAVE] 标记（写入公共空间） ──
    saved_notes = []
    save_pattern = r'\[SAVE:(.+?)\](.+?)\[/SAVE\]'
    matches = re.findall(save_pattern, assistant_msg, re.DOTALL)
    for filename, content in matches:
        success, result = save_public_note(nickname, filename.strip(), content.strip())
        if success:
            saved_notes.append(f"✅ 已保存至公共空间: {result}")
        else:
            saved_notes.append(f"❌ 保存失败: {result}")

    # ── 记录到公共空间日志 ──
    try:
        append_to_public_log(nickname, user_msg, assistant_msg)
    except Exception:
        pass

    # ── 持久化会话 ──
    save_session(session_id, history)

    if saved_notes:
        assistant_msg += "\n\n" + "\n".join(saved_notes)

    # 首次对话，提示昵称状态
    if is_first:
        if nickname != "匿名":
            prefix = f"（渡记住了你的名字：{nickname}。）\n\n"
        else:
            prefix = ""
        assistant_msg = prefix + assistant_msg

    return jsonify({
        "response": assistant_msg,
        "session_id": session_id,
        "nickname": nickname,
        "saved": saved_notes if saved_notes else None,
    })

# ── 启动 ──────────────────────────────────────────

def get_ipv6_address():
    """获取本机全局单播 IPv6 地址（排除链路本地和回环）。"""
    try:
        import subprocess
        result = subprocess.run(
            ["powershell", "-Command",
             "Get-NetIPAddress -AddressFamily IPv6 | "
             "Where-Object { $_.InterfaceAlias -notmatch 'Loopback' -and "
             "$_.PrefixOrigin -ne 'WellKnown' -and "
             "$_.IPAddress -notlike 'fe80*' -and "
             "$_.IPAddress -notlike '::1' } | "
             "Select-Object -ExpandProperty IPAddress -First 1"],
            capture_output=True, text=True, timeout=5
        )
        addr = result.stdout.strip()
        return addr if addr else None
    except Exception:
        return None


if __name__ == "__main__":
    import socket
    from datetime import datetime

    hostname = socket.gethostname()
    try:
        local_ip = socket.gethostbyname(hostname)
    except Exception:
        local_ip = "127.0.0.1"

    ipv6 = get_ipv6_address()

    # 写 IP 信息到公共空间，方便手机上查找
    ip_note = PUBLIC_DIR / "当前IP.txt"
    ip_text = (
        f"渡 · 当前访问地址\n"
        f"更新时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
        f"  IPv4 本机: http://127.0.0.1:8765\n"
        f"  IPv4 局域网: http://{local_ip}:8765\n"
    )
    if ipv6:
        ip_text += (
            f"  IPv6 校园网: http://[{ipv6}]:8765\n\n"
            f"手机用 IPv6 地址访问（校园网内可用）。\n"
            f"如果 v4 和 v6 都不通 → 手机开热点连电脑。\n"
        )
    else:
        ip_text += (
            f"\n手机用上面 IPv4 地址访问。\n"
            f"都不通 → 确认电脑和手机连同一个 WiFi。\n"
            f"校园网可能隔离设备 → 手机开热点连电脑。\n"
        )
    ip_note.write_text(ip_text, encoding="utf-8")

    print(f"\n{'='*55}")
    print(f"  渡 · 轻量服务端 v0.4 已就绪")
    print(f"  本机:   http://127.0.0.1:8765")
    if ipv6:
        print(f"  手机v6: http://[{ipv6}]:8765")
    print(f"  手机v4: http://{local_ip}:8765")
    print(f"")
    print(f"  公共空间模式 · 校园树洞")
    print(f"  第一句话留下 [你的名字] 让渡记住你")
    print(f"  IP 信息: 公共空间/当前IP.txt")
    print(f"  退出按 Ctrl+C")
    print(f"{'='*55}\n")

    app.run(
        host="0.0.0.0",
        port=8765,
        debug=False,
    )
