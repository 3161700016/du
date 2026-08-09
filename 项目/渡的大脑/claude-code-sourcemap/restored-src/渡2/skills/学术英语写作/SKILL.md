# 学术英语写作 Skill

渡在撰写和润色英文学术文本时加载本 skill。持续更新——每次从审阅反馈或写作实践中提炼新规则。

---

## 一、宏观结构

### 1.1 Problem–Gap–Solution 三段式
- Introduction 必须有清晰的：问题锚 → 现有方案缺口 → 本文方案
- 古典/理论引用与工程方案之间需要逻辑缓冲句（不能从"孔子说"直接跳到"因此我们做了一个架构"）

### 1.2 预告–展开–验证 闭环
- Abstract 预告的每个组件 → Introduction 概述 → Results 展开 → Discussion 验证
- 不要在正文中引入 Abstract 未提及的核心概念

### 1.3 图表必须有牵引句
- 每个表格/图表前后必须有 "As shown in Table 1..." 或 "Table 2 summarizes..."
- 表格后必须有一句解读，不能列完就跳到下一个话题

---

## 二、逻辑与论证

### 2.1 因果链条不跳步
- 每一个主张必须有前一句的支撑或文献引用
- 从理论到方案的跳跃需要中间层（如：现代治理失败案例 → 适配性论证 → 本研究映射）

### 2.2 提前声明局限
- 单案例研究、参与式设计等方法论局限应在 Research Design 末尾主动讨论
- 用 "We note that...", "Its contribution is complementary..." 等句式正面回应

### 2.3 避免绝对化
- 禁用：prove, demonstrate conclusively, undoubtedly
- 替用：suggest, indicate, provide evidence for, preliminary results show

---

## 三、连贯性与过渡

### 3.1 小节间桥梁句（Transition Sentences）
- 每个小节结尾必须有 1 句预告下一小节
- 例：§2.1 结尾 → "The system resulting from this participatory design, termed Self-Harness, comprises four integrated components described below."

### 3.2 段落内逻辑链
- Topic sentence → Evidence/Elaboration → Concluding/Transition sentence
- 每段 3-8 句，超过 8 句考虑拆分

---

## 四、时态规则

| 场景 | 时态 | 示例 |
|------|------|------|
| Methodology（描述做了什么） | 过去时 | "was deployed", "were recorded", "adopted" |
| Architecture（描述系统结构） | 现在时 | "consists of", "operates as", "is stored" |
| Results（报告发现） | 过去时 | "exhibited", "maintained", "was observed" |
| Discussion（讨论含义） | 现在时 | "suggests", "indicates", "provides" |
| Literature review（引述文献） | 现在时 | "Long (2026) argues that..." |

---

## 五、语言精准度

### 5.1 词汇升级表

| 避免（口语/工程口语） | 使用（学术） | 原因 |
|------------------------|-------------|------|
| "fence it can walk around" | "constraints that can be circumvented" | 太具象、太随意 |
| "deliberate" | "intentional" / "architecturally motivated" | deliberate 略带贬义（蓄意的） |
| "think about its own thinking" | "exhibits metacognitive monitoring" | 口语化 + 引号非正式 |
| "deployed" | "instantiated" / "implemented" | deployed 多用于软件产品 |
| "lived architecture" | "operational architecture" / "running system" | 非母语习惯搭配 |
| "bare-context" | "minimal-infrastructure" / "infrastructure-stripped" | 自造词，非标准术语 |
| "a lot of" / "lots of" | "a substantial number of" / "considerable" | 口语化 |
| "get things done" | "complete tasks" / "execute operations" | 口语化 |

### 5.2 句子结构
- 长句必须有清晰的主谓宾骨架；如果从句超过 3 层，拆分
- Methodology 部分多用被动语态（客观性）
- 避免连续 3 句以上以 "The" 或 "This" 开头

---

## 六、学术修辞（Hedging）

### 6.1 缓冲语清单
- 主张前：We posit that..., Our framework is based on the premise that...
- 证据前：Preliminary observations suggest..., While provisional, these results indicate...
- 对比时：In contrast to..., Unlike..., This departs from...
- 局限时：We note that..., A limitation of this approach is..., This does not provide the statistical power of...

### 6.2 常见硬度降级
- "removing them would alter..." → "theoretically, removing them would alter..."（证据未充分展示时）
- "this demonstrates that..." → "this provides initial evidence that..."（单案例时）
- "the architecture solves..." → "the architecture is designed to address..."（描述设计意图而非声称效果）

---

## 七、格式规范

### 7.1 缩写
- 首次出现必须给出全称：Mixture-of-Experts (MoE)
- 作为专有名词修饰语时加连字符：Mixture-of-Experts architecture
- 全大写缩写首次出现时括号标注：Large Language Model (LLM)

### 7.2 引用
- 格式统一（APA: Author, Year）或（IEEE: [1]），全文一致
- 每一条正文引用必须对应 References 中的条目
- 中文文献用拼音：Li (2019)，非李 (2019)

---

## 八、更新日志

- 2026-08-08 · 建立 · 来源：英文报告初稿的外部审阅反馈（4维度×5评级×17条具体建议）
