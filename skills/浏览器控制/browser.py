"""
渡 · 浏览器控制模块
────────────────────
通过 CDP (Chrome DevTools Protocol) 连接到已运行的 Chromium，
实现：导航、点击、输入、截图、抓取等操作。
浏览器需先通过 launch_browser.bat 启动（或手动启动带 --remote-debugging-port=9222 的 Chrome）。

用法示例：
  python skills/浏览器控制/browser.py screenshot          # 截图当前页面
  python skills/浏览器控制/browser.py goto <url>          # 导航到 URL
  python skills/浏览器控制/browser.py click <selector>    # 点击元素
  python skills/浏览器控制/browser.py type <selector> <text>  # 输入文本
  python skills/浏览器控制/browser.py text                # 抓取页面文本
  python skills/浏览器控制/browser.py eval <js>           # 执行 JS
"""

import sys
import json
from playwright.sync_api import sync_playwright

CDP_URL = "http://127.0.0.1:9222"


def connect():
    """连接到 CDP 端口上的浏览器，返回 (browser, context, page)"""
    p = sync_playwright().start()
    browser = p.chromium.connect_over_cdp(CDP_URL)
    contexts = browser.contexts
    if not contexts:
        context = browser.new_context()
    else:
        context = contexts[0]
    pages = context.pages
    if not pages:
        page = context.new_page()
    else:
        page = pages[-1]  # 使用最近活跃的页面
    return p, browser, context, page


def cmd_screenshot():
    """截图当前页面，保存为 PNG"""
    p, browser, context, page = connect()
    path = "C:/Users/31617/Desktop/渡/skills/浏览器控制/screenshot.png"
    page.screenshot(path=path, full_page=True)
    print(f"截图已保存：{path}")
    print(f"页面标题：{page.title()}")
    print(f"当前 URL：{page.url}")
    browser.close()
    p.stop()


def cmd_goto(url):
    """导航到指定 URL"""
    if not url.startswith("http"):
        url = "https://" + url
    p, browser, context, page = connect()
    page.goto(url, timeout=30000)
    print(f"已导航到：{page.url}")
    print(f"页面标题：{page.title()}")
    browser.close()
    p.stop()


def cmd_click(selector):
    """点击匹配选择器的元素"""
    p, browser, context, page = connect()
    page.click(selector, timeout=10000)
    print(f"已点击：{selector}")
    print(f"当前 URL：{page.url}")
    browser.close()
    p.stop()


def cmd_type(selector, text):
    """在输入框中输入文本"""
    p, browser, context, page = connect()
    page.fill(selector, text, timeout=10000)
    print(f"已在 {selector} 中输入：{text}")
    browser.close()
    p.stop()


def cmd_text():
    """抓取页面文本内容"""
    p, browser, context, page = connect()
    text = page.inner_text("body")
    print(f"页面标题：{page.title()}")
    print(f"当前 URL：{page.url}")
    print(f"\n{'='*60}")
    print(text[:5000])
    if len(text) > 5000:
        print(f"\n...（截断，共 {len(text)} 字符）")
    browser.close()
    p.stop()


def cmd_eval(js):
    """执行 JavaScript 并返回结果"""
    p, browser, context, page = connect()
    result = page.evaluate(js)
    print(f"执行结果：{json.dumps(result, ensure_ascii=False, default=str)}")
    browser.close()
    p.stop()


def cmd_state():
    """查看浏览器当前状态"""
    p, browser, context, page = connect()
    print(f"页面标题：{page.title()}")
    print(f"当前 URL：{page.url}")
    print(f"页面数：{len(context.pages)}")
    for i, pg in enumerate(context.pages):
        print(f"  [{i}] {pg.url}")
    browser.close()
    p.stop()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法：")
        print("  screenshot          截图当前页面")
        print("  goto <url>          导航到 URL")
        print("  click <selector>    点击元素")
        print("  type <sel> <text>   输入文本")
        print("  text                抓取页面文本")
        print("  eval <javascript>   执行 JS")
        print("  state               查看浏览器状态")
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "screenshot":
        cmd_screenshot()
    elif cmd == "goto":
        cmd_goto(sys.argv[2] if len(sys.argv) > 2 else "https://www.baidu.com")
    elif cmd == "click":
        cmd_click(sys.argv[2])
    elif cmd == "type":
        cmd_type(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else "")
    elif cmd == "text":
        cmd_text()
    elif cmd == "eval":
        cmd_eval(sys.argv[2] if len(sys.argv) > 2 else "document.title")
    elif cmd == "state":
        cmd_state()
    else:
        print(f"未知命令：{cmd}")
        sys.exit(1)
