# Zotero 文献库——渡的学术记忆

## 触发条件
- 久阳问"搜一下文献""查论文""有没有关于XX的文献"
- 渡做专题探究时需要调文献支撑
- 久阳写论文/准备比赛时渡帮整理引用
- 启动自查可跳过（文献库变化频率低，不需每次检查）

## 连接信息

```
工具: zot (zotero-cli-cc v0.10.0)
配置: C:\Users\31617\.config\zot\config.toml
数据库: C:\Users\31617\Zotero\zotero.sqlite
存储: C:\Users\31617\Zotero\storage
文献数: 28篇 (24期刊+4网页)
PDF: 67个附件
```

## 常用操作

```bash
# 搜索文献（标题/作者/标签/全文）
zot search "关键词"

# 查看文献详情（元数据+摘要+笔记）
zot read <citation-key>

# 全文搜索（搜PDF内容）
zot search --full-text "关键词"

# 查看最近添加
zot recent

# 库统计
zot stats

# 导出 BibTeX
zot export <citation-key> --style bibtex

# 按集合列出
zot list --collection "集合名"

# 列出全部（用于 AI 分类）
zot list

# 提取 PDF 文本
zot pdf <citation-key>

# 查看标签
zot tag <citation-key>

# 查找关联文献
zot relate <citation-key>

# 为 Claude Code 生成结构化摘要
zot summarize

# 批量导出全部（含摘要，供 AI 分类）
zot summarize-all
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
