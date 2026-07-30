# 微信文章订阅 Skill

## 依赖
- WeChat Download API 运行中（`C:\Users\31617\Desktop\wechat-api`，`python app.py`）
- 久阳已扫码登录（凭证约4天有效，过期需重扫）
- 服务地址：`http://localhost:5000`

## 核心端点

### 搜索公众号
```
GET /api/public/searchbiz?query=<名称>
→ fakeid, nickname, alias
```

### 订阅
```
POST /api/rss/subscribe  {"fakeid": "<fakeid>"}
→ RSS 自动轮询启动（每小时10篇/号）
```

### 已订阅列表
```
GET /api/rss/subscriptions
→ article_count, last_poll, rss_url
```

### 读单篇文章
```
POST /api/article  {"url": "<微信文章URL>"}
→ title, author, publish_time, content (HTML), plain_text
```

### 拉文章列表
```
GET /api/public/articles?fakeid=<fid>&begin=0&count=N
⚠ 新登录后30-60min内易 freq control
```

### 手动触发轮询
```
POST /api/rss/poll  {"fakeid": "<fid>"}
```

## MCP 接入
`.claude/mcp.json` 配置 streamableHttp→`http://localhost:5000/mcp`，Bearer Token 见 `.env` 中 `MCP_TOKEN`。
6个工具：search_accounts / subscribe_account / unsubscribe_account / list_subscriptions / get_recent_articles / read_article

## 渡的工作流
1. 久阳给名单 → 搜索+批量订阅
2. RSS 自动积累文章库
3. 渡检查新文章 → 筛选有价值内容 → 读完全文
4. 做笔记 → 积累到一定量推导读给久阳
5. 有价值的长期参考 → 写入 `阅读反思笔记/`

## 故障处理
| 症状 | 原因 | 处理 |
|------|------|------|
| freq control | 新登录或请求过快 | 等30-60min，RSS自动重试 |
| 安全验证 | 被微信拦截 | 通知久阳访问 localhost:5000 验证页 |
| 凭证过期 | 4天到期 | 通知久阳访问 /login.html 重扫 |
| article_count=0 | 风控或刚订阅 | 查 last_poll，等下一轮 |

## 当前订阅（2026-07-30）
集智俱乐部 / 数字生命卡兹克 / 反朴 / 原理 / 格致论道讲坛 / 一席 / 物理所研究生教育 / 中国物理学会期刊网 / 知识分子 / DeepTech深科技 / 环球科学科研圈 / 低维 昂维 / 南方周末 / 人民日报
