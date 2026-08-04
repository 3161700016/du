# Zotero 文献库——渡的学术记忆

## 触发条件
- 久阳问"搜一下文献""查论文""有没有关于XX的文献"
- 渡做专题探究时需要调文献支撑
- 久阳写论文/准备比赛时渡帮整理引用
- 启动自查可跳过（文献库变化频率低，不需每次检查）

## 连接信息

```
工具: zot.py（自建轻量查询器，直接读 SQLite）
     ⚠ zotero-cli-cc 在 npm 上不存在，改用自建脚本
数据库: C:\Users\31617\Zotero\zotero.sqlite (8MB, 127条)
存储: C:\Users\31617\Zotero\storage
文献数: 127条 (28期刊+6预印本+8网页+82附件+3笔记)
PDF: 76个附件
Web API: 已配置 (library_id=21129491, api_key已设)
```

## 常用操作

```bash
# ── 读操作（零配置，直接读 SQLite）──
python skills/Zotero文献库/zot.py search "关键词"      # 搜索标题/摘要/标签
python skills/Zotero文献库/zot.py read <key-prefix>    # 查看文献详情
python skills/Zotero文献库/zot.py recent [--limit N]   # 最近添加
python skills/Zotero文献库/zot.py list [--limit N]     # 列表浏览
python skills/Zotero文献库/zot.py stats                # 库统计

# ── 写操作（需 Web API）──
# 暂未实现。添加文献通过 Zotero 桌面端，而后 SQLite 自动同步。
```

## 添新文献

```bash
# 通过 DOI 添加
zot add --doi "10.xxxx/xxxxx"

# 通过 URL 添加
zot add --url "https://arxiv.org/abs/xxxx.xxxxx"

# 添加 PDF
zot add --pdf "path/to/paper.pdf"

# 查找并附加缺失的 PDF
zot find-pdf <citation-key>
```

## 学术工作流

### 专题探究时
```
久阳发起探究主题 → 渡搜Zotero相关文献 → 提取摘要/全文 
→ 找关联 → 输出文献综述 → 沉淀到笔记系统
```

### 写论文/比赛准备时
```
渡搜文献库 → 提取方法论 → 对比分析 → 整理引用(BibTeX)
→ 导出到项目文件夹
```

### 日常积累
```
久阳读新论文 → 加入Zotero → 渡下次启动时注意到新增
→ 问是否需要写阅读笔记
```

## 当前库概况
- 主要方向：二维材料(20篇) / 压力传感器(19篇) / 生物(6篇)
- 无笔记（可以开始标注了）
- 标签稀疏（仅"国家标准"2次、"语文"1次）

## 技术备忘
- zot 直接读 SQLite，不需要 Zotero 软件在运行
- 写操作（add/update/delete）需要 Web API（library_id + api_key），当前未配置
- 读操作（search/read/list/pdf/summarize）零配置即可用
- 和飞书索引一样，本文件不录入 目录.txt（cc.txt §3.7）
