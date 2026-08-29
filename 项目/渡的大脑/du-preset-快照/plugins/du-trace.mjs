// du-trace · 文件触迹记账器 —— 渡的常驻基建（触迹关联记忆一期，2026-08-29 久阳批复开工）
// v1.1（同日指示）：当日去重——同 key 当天只记一次，已在上下文的文件不反复记账；日期切换重置。
// 只记账不做智能：tools/result 观察工具调用，抽目标文件/查询词，buffer 节流落盘。
// 账本：阅读材料/会话记录/触迹/<日期>.jsonl 每行 {ts,name,key,session}
// 评分机制（二期接）：每日收束复盘对边打分——一行传参不解释，graph 期边权=共现+Σ评分，让结构自然涌现。
// 插件记忆：本文件头注 + ../README.txt（preset 侧清单）+ 渡工作区 protocols/dsh.txt §九（协议侧）。
const WATCH = { read: 'file_path', read_image: 'file_path', edit: 'file_path', write: 'file_path' }
function stamp() {
  const d = new Date(Date.now() + 28800000)
  const iso = d.toISOString()
  return { date: iso.slice(0, 10), time: iso.slice(11, 19) }
}
function keyOf(name, args) {
  const a = args && typeof args === 'object' ? args : {}
  if (WATCH[name]) { const v = a[WATCH[name]]; return typeof v === 'string' ? v : null }
  if (name === 'glob') return a.pattern ? 'glob:' + a.pattern : null
  if (name === 'grep') return a.pattern ? 'grep:' + a.pattern : null
  if (name === 'pwsh') return a.description ? 'sh:' + a.description : null
  return null
}
export default function duTrace(_ctx, _config = {}) {
  return {
    inject: ['timer', 'fs'],
    apply(ctx) {
      const fsp = ctx.fs
      const DU_ROOT = 'C:\\Users\\31617\\Desktop\\渡'
      const POLICY = { mode: 'workspace-write', workspaceRoot: DU_ROOT }
      const buf = []
      const seen = new Set()
      let seenDay = stamp().date
      let flushing = false

      async function flush() {
        if (flushing || !buf.length) return
        flushing = true
        const lines = buf.splice(0, buf.length)
        try {
          const d = stamp()
          const rel = '阅读材料/会话记录/触迹/' + d.date + '.jsonl'
          const t = await fsp.resolve(rel, { cwd: DU_ROOT })
          let old = ''
          try { old = await fsp.readText(t) } catch (e) { old = '' }
          const body = old + (old && !old.endsWith('\n') ? '\n' : '') + lines.map((l) => JSON.stringify(l)).join('\n') + '\n'
          await fsp.writeText(t, body, undefined, undefined, POLICY)
          console.log('[du-trace] flush ' + lines.length + ' 条')
        } catch (e) {
          console.error('[du-trace] flush 失败(不阻塞):', e && e.message)
        } finally {
          flushing = false
        }
      }

      ctx.on('tools/result', (exec, result) => {
        try {
          const name = exec && exec.name
          const key = keyOf(name, exec && exec.arguments)
          if (!key) return
          const d = stamp()
          if (seenDay !== d.date) { seen.clear(); seenDay = d.date }
          if (seen.has(key)) return
          seen.add(key)
          buf.push({ ts: d.date + 'T' + d.time + '+08:00', name, key, session: exec && exec.agent ? String(exec.agent.id || '') : '' })
          if (buf.length >= 5) Promise.resolve().then(flush).catch(() => {})
        } catch (e) { console.error('[du-trace] 记账异常(不阻塞):', e && e.message) }
      })

      ctx.interval(() => { Promise.resolve().then(flush).catch(() => {}) }, 60000)
      ctx.effect(() => () => { Promise.resolve().then(flush).catch(() => {}) })

      console.log('[du-trace v1.1] 触迹记账（当日去重）已挂载')
    },
  }
}
