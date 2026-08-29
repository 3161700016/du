// du-clock v2 · 时间锚点跟消息 —— 渡的常驻基建（2026-08-29 久阳指示重设计）
// 变更：弃 systemPrompt.context 每轮注入；改挂 agent/pre-step 瀑布，对本轮 claim 的
// 最后一条 user message 在 content 尾部追加 [时间锚点] text block。
// 文本只留表针；幂等（块标记检测，immutable 重建）；工具循环续步 claim 为空 → 不重复。
// 载体结论（2026-08-29 实测）：runtime snapshot 随 context 清空变为 none，附加消息不再发送。
export default function duClock(_ctx, _config = {}) {
  return {
    apply(ctx) {
      function nowLocal() {
        const d = new Date(Date.now() + 28800000)
        const iso = d.toISOString()
        const wd = '日一二三四五六'.charAt(d.getUTCDay())
        return iso.slice(0, 10) + ' ' + iso.slice(11, 19) + ' (+08:00 星期' + wd + ')'
      }
      ctx.on('agent/pre-step', (payload, next) => {
        try {
          const msgs = payload && Array.isArray(payload.messages) ? payload.messages : null
          if (msgs && msgs.length) {
            for (let i = msgs.length - 1; i >= 0; i--) {
              const m = msgs[i]
              if (m && m.role === 'user' && Array.isArray(m.content)) {
                const stamp = '[时间锚点] 当前本地时间：' + nowLocal()
                let has = false
                const content = m.content.map((b) => {
                  if (b && b.type === 'text' && typeof b.text === 'string' && b.text.includes('[时间锚点]')) {
                    has = true
                    return { type: 'text', text: stamp }
                  }
                  return b
                })
                if (!has) content.push({ type: 'text', text: stamp })
                msgs[i] = { ...m, content }
                break
              }
            }
          }
        } catch (e) { console.error('[du-clock] 锚点附加失败(不阻塞):', e && e.message) }
        return next()
      })
    },
  }
}
