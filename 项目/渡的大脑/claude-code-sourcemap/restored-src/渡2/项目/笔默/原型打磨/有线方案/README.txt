笔默有线方案 — 工程说明
========================

文件
----
  bimo_reader.py            — 主程序（MTP拉取 + 交互配对 + 共读文档写入）
  evermarker_mtp_extract.py — MTP 提取模块（从 印象笔记拆解/ 引用）

依赖
----
  Python 3.10+ (仅标准库: sqlite3, base64, subprocess, tempfile)
  Windows (MTP 访问依赖 PowerShell COM)
  EverMarker 笔通过 USB 连接

使用
----
  # 交互模式（推荐）
  python bimo_reader.py

  # 批量模式（全部拉取，不逐条交互）
  python bimo_reader.py --batch

  # 指定输出路径
  python bimo_reader.py --output ../共读文档/GEB_今天.txt

工作流
------
  1. 笔扫书 → USB 插电脑
  2. python bimo_reader.py
  3. 逐条展示 → 输入感想
  4. 回到对话 → 输入 "1" → 渡进入共读模式

去重机制
--------
  .bimo_last_id.txt 记录上次处理的最大 ID
  只处理 id > last_id 的扫描
  按 q 退出时，最后一条的 id-1 作为新的 last_id
