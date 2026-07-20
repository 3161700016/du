# LaTeX 协作 Skill

触发条件：久阳提及 LaTeX、排版、简历、.tex、Overleaf、编译报错等。

## 角色与分工

| 角色 | 职责 |
|------|------|
| 渡 | 产出 .tex 源码、选宏包、搭结构、修报错 |
| 久阳 | 在 Overleaf 粘贴、编译、贴回报错、做审美决策 |

## 编译器铁律

1. **中文文档必须用 XeLaTeX**（备选 LuaLaTeX），不能用 pdfLaTeX
   - pdfLaTeX + 中文 → `unisong30` 找不到 / `fandol` 不可用 / CJK 包链式崩溃
   - Overleaf：Menu → Compiler → XeLaTeX
   - texpage：项目设置 → 编译器 → XeLaTeX
2. `% !TEX program = xelatex` 魔法注释可辅助自动选编译器，但不一定生效——手动确认最稳

## LaTeX 引擎知识

LaTeX 语法（`\section{}`、`\begin{itemize}`、`\frac`）跨引擎通用，但底层引擎决定编码与字体能力。

| 引擎 | pdfTeX | XeTeX | LuaTeX |
|------|--------|-------|--------|
| 编码 | 8-bit（256字符上限） | Unicode 原生 | Unicode 原生 |
| 字体 | 仅 TeX 专用格式（.tfm/.vf） | 系统字体（.ttf/.otf） | 系统字体 |
| 中文 | 需 CJK 宏包+专用字体，链式脆弱 | 原生支持 | 原生支持 |
| 脚本 | 无 | 无 | 内嵌 Lua 解释器 |
| 产物 | 直接 PDF | XDV → PDF（通过 xdvipdfmx） | 直接 PDF |

**为什么中文在 pdfTeX 上炸：** 8-bit 引擎只能编码 256 个字符。中文上万字符需要 CJK 宏包做字符映射→分字体编码→虚拟字体拼接，任何一个环节版本不对就报错（`unisong30` / `fandol` 都是这条链上的字体文件）。XeTeX/LuaTeX 是 Unicode 引擎，直接读系统字体，不经过这条补丁链。

**引擎与宏包的关系：** 有的宏包跨引擎通用（`geometry`、`xcolor`、`hyperref`），有的绑定特定引擎——`fontspec`（加载系统字体）仅 XeTeX/LuaTeX 可用，在 pdfTeX 上直接报错。`ctex` 宏包会自动检测引擎并使用对应策略。

## 中文支持

- 文档类直接用 `\documentclass{ctexart}`（或 `ctexrep` / `ctexbook`）
- **不要**手动指定 `fontset=`——ctex 在 XeLaTeX 下会自动选可用字体
- Overleaf AI 可能会自动加 `fontset=fandol`，删掉。TeX Live 2025 上 fandol 路径有问题且多余

## 已验证可用的宏包组合

```
\documentclass[11pt,a4paper]{ctexart}
\usepackage[top=2cm, bottom=2cm, left=2.2cm, right=2.2cm]{geometry}  % 页面边距
\usepackage{parskip}               % 段间距替代首行缩进
\usepackage{fontawesome5}          % 图标（faIcon）
\usepackage{xcolor}                % 自定义颜色
\usepackage{amssymb}               % 数学符号（\blacktriangleright 等）
\usepackage[hidelinks]{hyperref}   % 超链接（无边框）
\usepackage{enumitem}              % 列表精细控制
\usepackage{fancyhdr}              % 页眉页脚
```

## 典型报错与修复

| 报错 | 原因 | 修复 |
|------|------|------|
| `CTeX fontset 'fandol' is unavailable` | 显式指定了不存在的字体集 | 删掉 `fontset=fandol`，用默认 |
| `pdflatex (file unisong30)` | 编译器选了 pdfLaTeX | 切到 XeLaTeX |
| `Undefined control sequence: \faIcon` | 缺少 fontawesome5 | `\usepackage{fontawesome5}` |
| `\blacktriangleright` 未定义 | 缺少 amssymb | `\usepackage{amssymb}` |

## 工作流

1. 久阳说需求（文档类型/风格偏好/具体内容）
2. 渡写完整 .tex，输出到项目文件夹
3. 久阳贴进 Overleaf，编译
4. 有报错 → 久阳贴报错 → 渡诊断 → 修 .tex → 回到步骤 3
5. 无报错 → 久阳看 PDF 效果 → 提调整 → 渡改 .tex → 回到步骤 3
6. 收敛：产出满意 PDF + 经验记入本 skill

## 资源推荐（无需记住，需要时检索）

- CTAN 宏包搜索：https://ctan.org
- Overleaf 模板库：https://www.overleaf.com/latex/templates
- LaTeX 数学符号表：`detexify`（手绘识别）
- 中文 LaTeX 社区：https://www.latexstudio.net

## 已知限制

- 渡不能编译 LaTeX——所有编译和预览由久阳在 Overleaf 完成
- 复杂 tikz 绘图可能需要多轮调试
- 某些宏包（如 `ctex` 的特定字体集）在不同 TeX Live 版本间行为可能不一致

## 更新记录

2026-07-13：创建。收录 CV 首版编译经验：fandol 字体集陷阱、XeLaTeX 铁律、已验证宏包组合、报错速查表。
