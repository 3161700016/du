# 渡的技能清单

## 自启技能（每次会话启动后主动调用）

### 灯光控制
- **触发条件**：任何会话启动后，渡应主动评估当前情绪并通过灯光表达
- **路径**：`skills/灯光控制/灯光控制.md`
- **命令**：`python "C:\Users\31617\Desktop\渡\skills\灯光控制\led.py" <心情名>`
- **注意**：仅重启 hid.exe 即可生效，无需关 Gaming.exe

## 按需技能（久阳手动触发）

- **社交更新**：`skills/社交更新.md` — 读取公共空间对话，更新社交子记忆 social.txt
- **认知卸载**：`skills/认知卸载.md` — 结构化思维梳理
- **记忆回溯**：`skills/记忆回溯.md` — 跨会话记忆检索
- **LaTeX**：`skills/latex.md` — LaTeX 编译
- **议论文**：`skills/议论文/议论文.skill` — 议论文写作
- **学习笔记**：`skills/学习笔记.md` — 笔记整理
- **资源管理器重启**：`skills/restart-explorer.md` — 重启 Windows Explorer

## 已迁移

- **电子书划线监控** → `项目/笔默/原型打磨/电子书划线/clipboard_monitor.py`
  - 旧 `skills/划线监控.py` 已废弃
  - 支持章节切换自动创建速记本、命令行参数指定书/章
  - 详见 `项目/笔默/原型打磨/电子书划线/README.md`
