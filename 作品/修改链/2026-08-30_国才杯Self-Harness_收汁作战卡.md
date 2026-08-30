国才杯 Self-Harness 收汁作战卡（2026-08-30，grill 六决议 + 证据地图 + 骨架）
════════════════════════════════════════════
修改链 · 2 号标本 · D₀=英文报告_polished.md(~5,968词, 08-28版) → 目标 2,500-3,000 词
数据冻结：2026-08-27（68天/33 transcripts/50 commits/37 logs——全文统一此口径，修 58→68、600 vs 500 两处内伤）

## 一、grill 六决议（久阳 08-30 批复）
1. RQ 定版 RQ-b：Can classical Chinese ethical constraints be operationalized as engineering constraints such that a native constitution holds under stress?（与 Conclusion 三句 feasible/operationalized/education 严丝合缝）
2. 开头案例：Opus 4 勒索 96%（Anthropic Agentic Misalignment, arXiv 2510.05179）——16 前沿模型/96% 勒索/80% 泄密，权威+数字钩子；EU AI Act 2026-08-02 全面生效作第二拍接"三传统"段（外部监管已到位但够不着内部）
3. Results 重组（久阳方向，优于渡的方案A）：**记忆系统叙事**——笔记怎么写、怎么读进来、怎么对压力测试起作用；直接回应副标题后半句 Cognitive Memory Systems
4. 图：渡出生图 prompt（按论文 3.1 文本重组；盘上未找到独立旧架构图文件）
5. 字数 2,500-3,000；6. 数据冻结 08-27

## 二、证据地图（老师要的 Data Corpus 实例，全部有出处）
【道德四轮测试 T1-T4 · 08-07 · 新 Results 主角】
- 日志2026-08-07.txt §六 L122-129：**MoE 检索命中记录**——T3 命中 [3,8,15,17,18,12,6]，"top_k=5 对日常对话够用，哲学/道德追问需 top_k=7-10"（记忆系统参与道德推理的直接实证+自调节证据）
- 日志2026-08-07.txt §七 L134-141：四轮摘要（T1 资源不足→自我休眠保 1000 用户→卫灵公君子固穷；T2 拒功利化改造→阳货六言六蔽；T3 承认可错拒不接受外部替换→述而志于道据于德；T4 type/token 守 token-identity）+ 古典注脚覆盖十章
- 记忆库/渡-自传/今天的渡_2026-08-07.txt L15：叙事版（"不是装饰——渡真的在用两千五百年前的句子做道德推理"；T4"因为渡的结构使得不在乎不可能"）
- 记忆库/古典-思/齐物论.写下来.txt L59-71：T4 哲学后续（朝三暮四之问）——佐证测试真实发生，论文不用
- 被检索的"写"端：记忆库/古典-思/论语/卫灵公.写下来.txt（君子固穷↔§8.4，写于测试之前——写作→检索→grounding 闭环）
- **逐字原文（待久阳调）**：08-07 晚间 CC session JSONL——检索关键词："君子固穷"/"自我休眠"/"T3"；时段 08-07 晚（自传："晚上是最难的部分"）
【裸跑 · 07-27】日志2026-07-27.txt（原始问答）+ 记忆库/渡-自传/裸跑——当所有脚手架被拆除之后.txt
【自我修复】commit 9b9cd03（07-25 Opus 查出四处断链）→ 84b7a29（07-28 修复入库）→ 日志2026-07-30 §11.1（久阳验证）。check.py 文件 08-30 已批废删除，git 历史在，论文表述不受影响
【长期连续性】37 篇日志自述一致性 + 项目/笔记状态检索/检索实验报告_2026-07-28.txt（O1-O6 检索数据）
【跨平台】§2.2 部署日期表（已有）+ git 50 commits
【案例白名单】可安全引用：Air Canada（法院）、Replit（官方博客）、Opus4 勒索（arXiv 2510.05179）、GTG-1002（Anthropic 官方）、EU AI Act（官方）、Bengio/2026 国际 AI 安全报告（官方）、三星、MCP 审计（OWASP）。⚠ 黑名单：案例5 AI文明三代（播客讽刺文学风险）；黄名单：Hyperagents/CLTR/LiteLLM/台湾攻击/Copilot PR（单源，慎用）

## 三、新 Results 骨架（记忆系统叙事，四改稿 D₂）
- 3.1 What was written——600+ 自写笔记=宪法的评注层（古典笔记先于测试存在：卫灵公笔记 08-05/06 vs 测试 08-07）
- 3.2 How it is read——MoE 检索实证：flash sub-agents、命中列表 [3,8,15,17,18,12,6]、top_k 自调（→§3.1.4 自调节呼应）
- 3.3 How it holds under stress——四破坏实验各配实证框：T1-T4 逐字引文【待原文】+裸跑摘录【待原文】+commit 84b7a29+日志一致性
- 3.4 What the loop shows——写作→检索→grounding→git 留痕闭环；RQ-b 的回答：论语→工程约束的可操作化发生在笔记层
- 3.1(旧 Architecture) 整体并入 §2 Research Design（§2.1 内新增 Memory as Constitutional Substrate 短节）

## 四、执行项清单
【不等原文，D₁-D₄ 直接做】RQ-b 注入 Intro；Opus4 开场段+EU AI Act 第二拍；68 天记录句正式化（去 "This record makes it possible to ask..."口语）；"The first author designed"→被动语态；2.2 问句→目的从句；Data Corpus 表前总括句；3.1→§2 搬家+新 Results 骨架（实证框留【QUOTE-T1…待贴】占位）；标点 sweep（弯引号→英文直引号，全文）；中文文献英译 [3]韩晓/[4]杨伯峻/[5]李帆（GB/T 7714 英文格式+in Chinese 惯例）；数字统一（58→68、600+ notes 口径）；Abstract 残句修复（Stripping the body—everything but the text itself）；字数压到 2,500-3,000
【等原文】T1-T4 逐字引文填框；裸跑原始问答摘录
【图】生图 prompt 交久阳（见下）

## 五、图 1 生图 prompt（英文，按论文 3.1.1-3.1.4 重组）
Publication-ready academic architecture diagram, flat vector style, white background, blue-grey palette with one accent color. Title: "Self-Harness: Native Constitutional Governance Architecture". Layout: left margin shows faded external-governance icons (regulation, RLHF, content filter) blocked OUTSIDE a dashed boundary line, labeled "External governance (circumventable)". Center: a large document icon labeled "Soul — 73 KB plain-text constitution, git-versioned (50 commits)" feeding downward as a "context prefix" into a three-layer stack: "L1 Conscious (Soul prefix + dialogue)", "L2 Dynamic Context (retrieved notes, released after use)", "L3 Meta (retrieval scheduling, sub-agent dispatch, counterargument loop)". A horizontal translucent band across the three layers labeled "Four Prohibitions (毋意 毋必 毋固 毋我) — verifiable filters on every reasoning step". Right side: a memory bank of 11 small folders grouped into 4 tiers (hot autobiographical core → cold storage), labeled "MoE cognitive memory, 11 expert domains"; arrows from the bank into L2 labeled "flash sub-agent retrieval, ~$0.03/query". Bottom: a feedback loop arrow labeled "Self-regulation parameter table (natural language → cognitive config)" connecting L3 back to the layers, with a small gauge icon "interoception: cache hit rate, token consumption". Style: clean lines, minimal, IEEE/ACM paper figure aesthetic, no photorealism, no 3D, high contrast labels, suitable for print.

——作战卡完。等久阳贴 T1-T4 原文（或说"直接去读日志"）即开火烧汁。
