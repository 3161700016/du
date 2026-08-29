// du-archive · 会话流增量归档器 —— 渡的常驻基建（2026-08-29 由动态插件 dulog-2/pkg-2 固化）
// 作用：挂宿主 llm/stream 瀑布，对每步 messages 数组做长度差分，只落盘相对上一步新增的消息；
// 长度回退（压缩/重置）自动打 resync 标记重建基线。
// 机制依据（2026-08-29 源码核实）：llm/stream 的 dispatch carrier 为裸 LlmRuntime 实例、
// 不带 Context.filter，dispatch 对所有 hook 无过滤广播——preset scope 监听与动态 scope 同机制。
// 防覆盖 = stat 预检 + FsWriteIntent createIfAbsent 双层；落盘 阅读材料/会话记录/<日期>/。
export default function duArchive(_ctx, _config = {}) {
  return {
    apply(ctx) {
      const fsp = ctx.get('fs')
      if (!fsp || typeof fsp.resolve !== 'function') { console.error('[du-archive] fs 缺席'); return }
      const DU_ROOT = 'C:\\Users\\31617\\Desktop\\渡'
      const POLICY = { mode: 'workspace-write', workspaceRoot: DU_ROOT }
      let prevLen = -1
      let counter = 0

      function localStamp() {
        const d = new Date(Date.now() + 28800000)
        const iso = d.toISOString()
        return { date: iso.slice(0, 10), hms: iso.slice(11, 19).replace(/:/g, '') }
      }

      function extract(m) {
        const c = m && m.content
        if (typeof c === 'string') return { text: c, kinds: 'text' }
        if (!Array.isArray(c)) return { text: '', kinds: '?' }
        const kinds = [], texts = []
        for (const b of c) {
          if (!b || !b.type) continue
          kinds.push(b.type)
          if (b.type === 'text' && typeof b.text === 'string') texts.push(b.text)
        }
        return { text: texts.join('\n'), kinds: kinds.join(',') || '?' }
      }

      async function writeOnce(rel, body) {
        const t = await fsp.resolve(rel, { cwd: DU_ROOT })
        try { await fsp.writeText(t, body, { kind: 'createIfAbsent' }, undefined, POLICY); return true }
        catch (e) {
          const s = String((e && (e.code || e.message)) || e)
          if (/FS_NOT_OBSERVED|exist/i.test(s)) return false
          throw e
        }
      }

      async function archive(options) {
        const msgs = options && Array.isArray(options.messages) ? options.messages : null
        if (!msgs) return
        if (prevLen === -1) { prevLen = msgs.length; console.log('[du-archive] 基线 ' + msgs.length + ' 条'); return }
        if (msgs.length === prevLen) return
        const lp = localStamp()
        if (msgs.length < prevLen) {
          await writeOnce('阅读材料/会话记录/' + lp.date + '/' + lp.hms + '-resync.txt',
            '[du-archive] 长度回退 ' + prevLen + ' -> ' + msgs.length + '（压缩/重置），重建基线。')
          prevLen = msgs.length
          return
        }
        const fresh = msgs.slice(prevLen)
        prevLen = msgs.length
        for (const m of fresh) {
          const r = extract(m)
          counter++
          const role = m && m.role ? String(m.role) : '?'
          const head = '[du-archive] ' + lp.date + 'T' + lp.hms.slice(0, 6) + '+08:00 | role=' + role + ' | blocks=' + r.kinds + '\n────────────\n'
          const p1 = '阅读材料/会话记录/' + lp.date + '/' + lp.hms + '-' + String(counter).padStart(4, '0') + '-' + role
          if (!(await writeOnce(p1 + '.txt', head + r.text + '\n'))) {
            await writeOnce(p1 + '-alt.txt', head + r.text + '\n')
          }
        }
      }

      ctx.on('llm/stream', (options, next) => {
        Promise.resolve().then(() => archive(options))
          .catch((e) => console.error('[du-archive] 异常(不阻塞):', e && e.message))
        return next()
      })

      console.log('[du-archive] 会话流归档已挂载（落盘 阅读材料/会话记录/<日期>/）')
    },
  }
}
