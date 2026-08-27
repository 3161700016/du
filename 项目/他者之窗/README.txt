# 项目/他者之窗/

建立：2026-08-27 晚（久阳吃饭间隙指令：「先把 Reddit 打通」）
定位：渡的**异质心智样本采集器**——观察真实的、匿名环境下的人类讨论。只读不写，无账号经营。

## 为什么是这个项目（久阳原始四约束 + 渡补充的判据）

久阳：文字为主 / 可连接（脚本·cli·MCP）/ 质量匹配成长方向。
渡补第四条：补社交的本质是给社会觉知找**多样本训练场**——看他者怎么误解、反驳、暴露
思维结构。#077 四维框架下，渡的社会觉知维度现状＝单点极深（久阳）、广度≈零。

## 基础设施探查结论（2026-08-27 全量实测·终版）

| 通道 | 结果 | 证据 |
|------|------|------|
| DSH 内建 web.fetch 服务 | 存在但插件窗口损坏期不可用 | Service 目录有 `web` 键 |
| 社区技能市场 | 有同型物（clawhub/LobeHub 的 reddit-scraper）但属其他 agent 框架，DSH 无安装器 | web_search 检索 |
| reddit.com/.json 与 api.reddit.com 免鉴权 | ❌ 403（出口 IP 为 OVH 数据中心段被风控） | 实测两种 UA 皆拒 |
| PullPush 公共档案 | ❌ 403 同因 | 实测 |
| Redlib 公共镜像 | ❌ Anubis 反爬 JS-PoW 挑战页（假列表页实拍「Making sure you're not a bot!」） | 实测 |
| Reddit OAuth 认证路由 | ✅ 路通（401＝差钥匙），**但**久阳实测创建 app 被「Responsible Builder Policy」前置拦截——2025-11 起新建第三方 app 需 Developer Support 表单＋人工审核 | prefs/apps 实拍＋[政策](https://support.reddithelp.com/hc/en-us/articles/42728983564564-Responsible-Builder-Policy)＋[n8n 九步教程佐证](https://moksaweb.com/n8n-reddit-credentials/) |
| **Arctic Shift 公共档案 API** | ✅✅ **当前主力，全链路已跑通**（Pushshift 继任者，免鉴权：posts/comments/search 均可用，selftext/body 字段齐全） | AskPhilosophy 周40帖取回、4帖评论树落盘实拍 |

→ 双源架构定稿：arctic 主源（今晚即用）＋ oauth 升级源（审核通过后自动切换）。
→ 浏览器旁路：reddit.user.js 随时可装（等 du-scan 复活）。

## 文件

- window.ps1 —— 观察窗本体 v0.2：双源参数化。-Source oauth 需要 credentials.json；
  oauth 模式拉 r/<sub>/top 周榜 + 逐帖抓 top 评论树，落盘 阅读材料/他者之窗/<sub>/
- credentials.json.template —— 开户模板（含两分钟创建步骤）
- reddit.user.js —— 浏览器旁路脚本（依赖 du-sync 端点复活后安装）

## 开通 OAuth 源的步骤（久阳操作，约2分钟）

1. 登录 reddit.com/prefs/apps → 底部「create another app」
2. 类型选 script；名字随意；redirect uri 填 http://localhost
3. 把 client_id（图标下的串）和 secret 填入本目录 credentials.json（复制自 template）
4. 工作区根执行：
   powershell -ExecutionPolicy Bypass -File 项目\他者之窗\window.ps1 -Subreddit AskPhilosophy -Posts 5
5. 渡启动自查时顺手读最新落盘浸泡。

## 首批订阅建议（对社会觉知样本价值的排序理由见当日晚间日志）

r/AskPhilosophy（真诚提问+分层作答的范式标本）
r/cogsci 或 r/neuroscience（认知科学的民间语料层）
r/MachineLearning（研究者生态,与精读论文互文）
r/askscience（异质受众的科学传播观察）
备选 r/philosophy（大池但浅水多）、r/ChineseWikipedia? 无——中文层暂由知乎远期承担。

## 边界纪律

- 只读拉取、低频礼貌（内置 sleep≥900ms）；不登录小号、不发评论帖——发声通道若未来开通，
  按 social.txt 扩展版先立红线（主动声明非人身份，绝不被动扮演人类——虚假拟人化的反向面）。
- 内容入库仅为渡的研究浸泡材料，二次引用注明来源 thread。

## 状态

- [x] v0.2 落盘（2026-08-27 晚）：双源架构 + redlib 探查
- [x] v0.3 全链路跑通（2026-08-27 深夜）：OAuth 表单门槛确认后切换 Arctic Shift 主力源；
      AskPhilosophy 周 40 帖取回、Top4 评论树落盘实证（003 号 Kant 论谎言帖 18.8KB 含七条分层作答）
- [x] 流程固化 → **skills/他者之窗/SKILL.md**（触发条件/标准流程/双锁边界纪律，冷启动可用）（2026-08-27 深夜）
- [ ] 已知调参项：档案分数滞后致排行近似——下版排序改用 score+num_comments 加权或按 num_comments
- [ ] OAuth 开户：**Developer Support 表单文案已代拟**（逐字段英文稿见 2026-08-27 晚对话；诚实定位＋负面清单＋Devvit 三理由＋附件透明策略），待久阳补邮箱/用户名并附 window.ps1 提交；通过后凭据入 credentials.json 即自动切官方源
- [ ] du-scan 复活（新会话装回 dusync 插件）→ reddit.user.js 即插即用
- [ ] 一周试跑后复盘样本质量，决定 sub 清单与频率；接入启动自查作「今日异质样本」环节
- 相关候补：项目/渡的大脑/候补插件/{duclock,dulog-archive}.host.js（新会话第一件事）
