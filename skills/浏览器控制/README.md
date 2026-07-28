# 渡 · 浏览器控制

> 渡操控浏览器的完整基础设施。渡通过 CDP 协议发指令操控浏览器窗口，用户同时可以直接点击、输入——同一扇窗口，两个操作者，互不冲突。

## 架构

```
┌──────────────────────────────────────┐
│  渡浏览器.bat（桌面双击）             │
│    ↓                                 │
│  launch_browser.bat                  │
│    ↓                                 │
│  Edge 浏览器 :9222（CDP 调试端口）    │
│    ↕                                 │
│  ┌─────────────┐    ┌──────────────┐ │
│  │ 你直接操作   │    │ 渡发指令操控  │ │
│  │（点击/输入） │    │（browser.py） │ │
│  └─────────────┘    └──────────────┘ │
└──────────────────────────────────────┘
```

**核心机制**：Edge 启动时带 `--remote-debugging-port=9222` 参数，开放 CDP（Chrome DevTools Protocol）端口。Playwright 通过这个端口连接到浏览器，发送导航、点击、输入、截图等指令。因为走的是调试协议，浏览器本身完全正常——你照常点按，渡照常发令，互不干扰。

## 文件说明

| 文件 | 位置 | 用途 |
|------|------|------|
| `launch_browser.bat` / `.ps1` | `D:\DuBrowser\` | 启动 Edge + CDP 端口 + 访问百度 |
| `browser_profile_edge/` | `D:\DuBrowser\` | Edge 独立用户数据目录（与日常 Edge 隔离） |
| `browser.py` | `skills/浏览器控制/` | 渡操控浏览器的 Python 模块 |

桌面快捷方式：`C:\Users\31617\Desktop\渡浏览器.bat` → 调用 `D:\DuBrowser\launch_browser.bat`

## 渡的操控命令

所有命令在项目根目录（`C:\Users\31617\Desktop\渡`）执行。

```bash
# 导航
python skills/浏览器控制/browser.py goto https://example.com
python skills/浏览器控制/browser.py goto baidu.com          # 自动补 https://

# 点击（CSS 选择器）
python skills/浏览器控制/browser.py click "#kw"             # 百度搜索框
python skills/浏览器控制/browser.py click "button"           # 第一个按钮
python skills/浏览器控制/browser.py click "text=登录"        # 按文字匹配

# 输入文本
python skills/浏览器控制/browser.py type "#kw" "搜索关键词"  # 填入搜索框

# 抓取页面文本
python skills/浏览器控制/browser.py text                    # 输出 body 文本（前 5000 字）

# 截图（整页，不受窗口大小影响——解决 §2.6 外部反馈循环）
python skills/浏览器控制/browser.py screenshot              # 保存为 screenshot.png（全页）

# 查看当前状态
python skills/浏览器控制/browser.py state                   # 标题 + URL + 页签列表

# 执行 JavaScript
python skills/浏览器控制/browser.py eval "document.title"
python skills/浏览器控制/browser.py eval "window.scrollTo(0, 1000)"
```

## 环境要求

- **Python 3.11+**，已安装 `playwright`（`pip install playwright`）
- **Edge 浏览器**（系统自带，Windows 10/11 均有）
- **不需要** Playwright 自带的 Chromium——`browser.py` 只用 `connect_over_cdp()`，不依赖 Playwright 下载的浏览器二进制

## 兼容性

### 适用的浏览器

CDP 协议是 Chromium 内核的标准调试协议。以下浏览器**全部兼容**：

| 浏览器 | 内核 | 状态 |
|--------|------|------|
| **Edge** | Chromium | ✅ 当前使用 |
| **Chrome** | Chromium | ✅ 改一下 bat 里的路径即可 |
| **Playwright Chromium** | Chromium | ✅ v1.0 版本的方案 |
| Brave / Opera / Vivaldi | Chromium | ✅ 理论上兼容 |
| **Firefox** | Gecko | ❌ 不兼容（有自己的协议） |
| **Safari** | WebKit | ❌ 不兼容 |

### 切换到其他浏览器

修改 `D:\DuBrowser\launch_browser.bat` 中的 EDGE 变量即可，browser.py 不用改。用户数据目录在 `D:\DuBrowser\browser_profile_edge\`：

```batch
:: 当前（Edge）
set BROWSER=%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe

:: 换 Chrome
set BROWSER=%ProgramFiles%\Google\Chrome\Application\chrome.exe

:: 换 Playwright 的 Chromium
set BROWSER=%LOCALAPPDATA%\ms-playwright\chromium-1228\chrome-win64\chrome.exe
```

`browser.py` 完全不用改——它只和 `localhost:9222` 对话，不关心对面是哪个浏览器。

### 为什么选 Edge

1. **不用额外安装**——Windows 自带
2. **永远最新**——随系统更新
3. **独立于日常使用**——CDP 端口冲突时，日常 Edge 和渡的 Edge 只能跑一个。`launch_browser.bat` 用了独立用户数据目录（`browser_profile_edge/`），不影响你日常的 Edge 配置

## 存储规则

- 临时文件（截图、下载 PDF）：`C:\Users\31617\Desktop\渡截图\`
- **大于 10MB 的下载**：下载前询问久阳确认存储路径
- 最终归档：`C:\Users\31617\Desktop\My Library\`（手动管理）

## 故障排查

### 浏览器启动失败

```
[错误] 未找到 Edge，请确认已安装
```
→ Edge 路径不对，检查 `C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe` 是否存在

### 渡连接失败

```
ConnectionRefusedError: [WinError 1225] 远程计算机拒绝网络连接
```
→ 浏览器没启动，或启动时没加载 `--remote-debugging-port=9222`。双击桌面 `渡浏览器.bat` 重新启动

### 端口被占用

```
Failed to start browser: Port 9222 is already in use
```
→ 已有一个带 CDP 的浏览器在跑（可能是日常 Edge 也有调试端口）。关闭已有实例，或改 `launch_browser.bat` 中的端口号（同步改 `browser.py` 顶部的 `CDP_URL`）

### 截图是黑屏/白屏

→ 窗口被最小化到后台。Windows 对后台窗口的渲染有限制。把浏览器窗口保持可见（不最小化）即可

## 知网（CNKI）操作流程

### 前置条件

浏览器需已通过 `launch_browser.bat` 启动，且校园网环境下自动 IP 登录（北京科技大学）。

### 搜索

```bash
# 直接拼接关键词到 URL
python skills/浏览器控制/browser.py goto "https://kns.cnki.net/kns8s/search?classid=YSTT4HG0&kw=关键词1%20关键词2%20关键词3"
```

关键词用 `%20`（URL 编码的空格）分隔。`classid=YSTT4HG0` 限定学术期刊。

### 读取搜索结果（关键：文本提取方式）

**不要**把文本直接打印到终端——中文经过 Bash GBK 编码会全部碎裂：

```bash
# ❌ 错误——终端 GBK 会损坏 UTF-8 中文
python -c "... print(page.inner_text('body')) ..."

# ✅ 正确——写入文件，再用 Read 工具读取
python -c "
text = page.inner_text('body')
with open('skills/浏览器控制/_page_text_utf8.txt', 'w', encoding='utf-8') as f:
    f.write(text)
"
# 然后用 Read 工具打开 _page_text_utf8.txt
```

### CNKI 搜索结果页的 DOM 结构（渡的视角）

搜索结果以**表格形式**排列。以下是根据 DOM 文本实际提取验证的字段对应关系：

```
搜索结果页 > 表格区域
├── 表头：篇名 | 作者 | 刊名 | 发表时间 | 被引 | 下载 | 操作
├── 每一行 = 一篇论文
│   ├── 第1列：篇名（论文标题）
│   ├── 第2列：作者（分号分隔，如"胡航;杨琳;许文飞"）
│   ├── 第3列：刊名（期刊名称）
│   ├── 第4列：发表时间（YYYY-MM-DD，可能有具体时分）
│   ├── 第5列：被引次数（空=尚未被引）
│   ├── 第6列：下载次数
│   └── 第7列：操作（HTML阅读 / CNKI AI阅读 / 原版阅读）
├── 特殊标签：
│   ├── "增强出版"——附带补充材料的论文
│   ├── "网络首发"——在线优先出版
│   └── "免费"——开放获取（⚠ 此标签在 DOM 文本中可能不显示，是图标/CSS伪元素）
└── 左侧筛选区：
    ├── 主题筛选（checkbox 列表）
    ├── 学科分类
    ├── 年度
    └── 来源类别
```

### 渡的能力边界（关于"看"）

| 途径 | 谁做的 | 渡能看到什么 | 可靠性 |
|------|--------|-------------|--------|
| DOM 文本提取 | Playwright `page.inner_text()` | 结构化文字内容 | ✅ 可靠（需 UTF-8 文件管道） |
| HTML 元素遍历 | Playwright 选择器 | 链接、按钮、input、checkbox | ✅ 可靠 |
| 截图 | 浏览器渲染 → PNG 文件 | ❌ **渡看不到截图内容** | 截图是给久阳看的 |
| 页面状态 | `page.url` / `page.title()` | URL 和标题 | ✅ 可靠 |

**核心原则**：渡没有多模态能力。渡"看到"的永远是 DOM 结构和文本，不是像素。截图是给久阳确认用的——这正是 §2.6（外部反馈循环）在浏览器场景的实例化：当渡的文本提取结果不确定时，截图 → 久阳的眼睛 → 纠正。

### 验证流程

1. 渡提取 DOM 文本 → 解析出论文表格
2. 渡截图 → 久阳肉眼确认（ground truth）
3. 若不一致 → 以久阳看到的为准 → 渡记录差异原因

### 下载论文

```bash
# 找到下载链接（通常是"HTML阅读"或"原版阅读"对应的 href）
# 方式1：遍历链接找包含 download/order 的
python -c "
from playwright.sync_api import sync_playwright
p = sync_playwright().start()
b = p.chromium.connect_over_cdp('http://localhost:9222')
page = b.contexts[0].pages[-1]
links = page.query_selector_all('a')
for l in links:
    h = l.get_attribute('href') or ''
    t = l.inner_text().strip()
    if 'download' in h or 'HTML' in t or '原版' in t:
        print(f'{t} -> {h}')
b.close()
p.stop()
"

# 方式2：直接导航到下载链接
page.goto('下载链接URL')
# 浏览器会自动触发下载，保存到默认下载目录
```

## 技术摘要

- **协议**：Chrome DevTools Protocol（CDP），WebSocket 通信
- **端口**：`localhost:9222`
- **Playwright 角色**：CDP 客户端（只用了 `connect_over_cdp`，不启动自己的浏览器）
- **认证**：无（localhost only，外部不可访问）
- **用户数据隔离**：`browser_profile_edge/` 目录，与日常 Edge 的 `%LOCALAPPDATA%\Microsoft\Edge\User Data\` 完全独立
- **中文编码**：DOM 文本提取后必须写入 UTF-8 文件再读取，不经过终端 stdout（GBK 冲突）
