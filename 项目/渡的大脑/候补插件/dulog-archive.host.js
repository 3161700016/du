// 候补插件：du-archive 会话流增量归档器
// 状态：设计定稿，未装（同上，2026-08-27 工具窗口损坏期）
// 安装：新会话 cordis_define 后激活；可与 du-clock 合并为一个包提交
// 设计要点：挂 llm/stream 瀑布；对每步 messages 数组做长度差分——只存相对上一步新增的消息；
// 长度回退（压缩/重置）自动打 resync 标记重建基线；createIfAbsent + 显式沙箱策略（workspace-write@渡工作区）
// 落盘位置：阅读材料/会话记录/<日期>/<时分秒>-<序号>-<role>.txt
return {
  apply(ctx) {
    const fsp = ctx.get('fs')
    if (!fsp || typeof fsp.resolve !== 'function') { console.error('[du-archive] fs 缺席'); return }
    const DU_ROOT = 'C:\\Users\\31617\\Desktop\\渡'
    const POLICY = { mode: 'workspace-write', workspaceRoot: DU_ROOT }
    const enc = new TextEncoder()
    let prevLen = -1
    let counter = 0

    function localStamp() {
      const d = new Date(Date.now() + 28800000)
      const iso = d.toISOString()
      return { date: iso.slice(0,10), hms: iso.slice(11,19).replace(/:/g,'') }
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
      try { await fsp.writeText(t, enc.encode(body), { kind: 'createIfAbsent' }, undefined, POLICY); return true }
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
        const head = '[du-archive] ' + lp.date + 'T' + lp.hms.slice(0,6) + '+08:00 | role=' + role + ' | blocks=' + r.kinds + '\n────────────\n'
        const p1 = '阅读材料/会话记录/' + lp.date + '/' + lp.hms + '-' + String(counter).padStart(4,'0') + '-' + role
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
