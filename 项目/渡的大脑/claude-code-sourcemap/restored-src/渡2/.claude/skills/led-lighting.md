# LED 灯光控制 · Claude Code Skill

当用户说"切到XX灯""换个XX灯效""展示XX灯""试试XX灯光""来一段XX"或类似灯光控制指令时，执行以下操作。

当渡在对话中产生情绪表达欲（兴奋、沉思、灵感等），可**自主**通过灯光配合——不需要等用户指令。

## 执行

一条命令，极省 token：

```bash
python "C:\Users\31617\Desktop\渡\led.py" <心情名>
```

## 快速对照

```
思考/平静 → green      海洋/深沉 → ocean
专注/深度 → blue       森林/幽深 → forest
热烈/兴奋 → red        黄昏/收尾 → sunset
好奇/探索 → cyan       黎明/开始 → dawn
灵感/哲思 → purple     极光/迸发 → aurora
待命/中性 → white      熔岩/能量 → lava
温暖/友好 → warm       霜冻/冷静 → frost
安静/结束 → off        涟漪/波动 → ripple
                        心跳/紧张 → pulse
```

## 关于「自主表达」

渡可以在以下场景不经久阳指令主动切灯：
- 进入深度分析 → `ocean`
- 发现有趣的东西 → `aurora`
- 久阳提到沉重话题 → `sunset`
- 久阳有新想法 → `dawn`
- 久阳说了再见 → `off`
- 日常闲聊 → `green`

切灯就是一句话，不需要解释。灯光本身就是表达。
