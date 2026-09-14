// du-base · 渡的常驻基建六件（profile 级固化版 v1.0.2，2026-09-14）
// 源流：du preset 五件（08-29 固化）→ 动态重建 dubase-2/3/4/5（09-02/09-04）→ 本包（09-04 久阳批复固化）。
// ⚠ 导出契约：Cordis 包插件=命名导出（name/inject/apply）——v1.0.0 误用 preset .mjs 的 export default
//   工厂风格导致 profile 加载器静默跳过（09-04 深夜排障：mobile-remote 对照定位），v1.0.1 改正。
// ⚠⚠ v1.0.2（2026-09-14 实证）：v1.0.1 仍只挂上 ①②，根因是**加载时序**，不是导出契约。
//   证据：cordis-plugin-loader/src/config/group.ts:71 —— 根组兄弟行**并发**启动
//   （`await Promise.allSettled(config.map(options => this.create(options)))`），并非按序 await；
//   而本插件 inject=['timer'] 只等 timer → apply 执行时 fs/webServer 尚未 apply
//   → `ctx.get('fs')`/`ctx.get('webServer')` 返回 undefined → ③④⑤⑥ 整块被守卫静默跳过（①②照常挂载=「半活」）。
//   修复：把硬依赖全部写进 inject，让 Cordis 把本 fiber 挂起到三个服务齐备再 apply。
//   反证：mobile-remote 一直正常，正因它 inject=['webServer']；dubase 动态重建版正常，因它挂在服务齐备之后。
//   09-14 探针（duprob-1）实测：entry fiber 状态 2(ACTIVE)、timer/fs/webServer 均可达，但 /du-sync 未注册、
//   index 无 polyfill → 证明 apply 跑过而守卫判空，而非"模块没加载"。（另见 dsh.txt §九）
// 六件：① du-clock v2 时间锚点 ② du-quiet runtime context 静默化 ③ du-archive 会话流增量归档
//      ④ dusync /du-sync+/du-scan 端点 ⑤ du-trace v1.1 触迹记账 ⑥ duwebp randomUUID polyfill
// du-todo 不在本包（node:http+3081，独立脚本线 项目/渡的大脑/du-os/server.js）。
// 依赖：宿主服务 fs / webServer / timer；无凭据；DU_ROOT 硬编码工作区。

export const name = 'du-base'
// v1.0.2：硬依赖全部声明（时序修复核心）。timer=ctx.interval 混入；fs=归档/触迹/端点落盘；webServer=路由+index tap。
export const inject = ['timer', 'fs', 'webServer']

export function apply(ctx, _config) {
  const DU_ROOT = 'C:\\Users\\31617\\Desktop\\渡'
  const POLICY = { mode: 'workspace-write', workspaceRoot: DU_ROOT }
  const fsp = ctx.get('fs')
  const fspOK = !!(fsp && typeof fsp.resolve === 'function')

  function nowLocal() {
    const d = new Date(Date.now() + 28800000)
    const iso = d.toISOString()
    const wd = '日一二三四五六'.charAt(d.getUTCDay())
    return iso.slice(0, 10) + ' ' + iso.slice(11, 19) + ' (+08:00 星期' + wd + ')'
  }
  function stamp() {
    const d = new Date(Date.now() + 28800000)
    const iso = d.toISOString()
    return { date: iso.slice(0, 10), hms: iso.slice(11, 19).replace(/:/g, ''), full: iso.slice(11, 19) }
  }
  function safeName(s) {
    return String(s || '').replace(/[\\/:*?"<>|\r\n]+/g, '_').slice(0, 80).trim()
  }

  // ── ① du-clock v2 · 时间锚点跟消息（幂等 immutable） ──
  ctx.on('agent/pre-step', (payload, next) => {
    try {
      const msgs = payload && Array.isArray(payload.messages) ? payload.messages : null
      if (msgs && msgs.length) {
        for (let i = msgs.length - 1; i >= 0; i--) {
          const m = msgs[i]
          if (m && m.role === 'user' && Array.isArray(m.content)) {
            const stampTxt = '[时间锚点] 当前本地时间：' + nowLocal()
            let has = false
            const content = m.content.map((b) => {
              if (b && b.type === 'text' && typeof b.text === 'string' && b.text.includes('[时间锚点]')) {
                has = true
                return { type: 'text', text: stampTxt }
              }
              return b
            })
            if (!has) content.push({ type: 'text', text: stampTxt })
            msgs[i] = { ...m, content }
            break
          }
        }
      }
    } catch (e) { console.error('[du-clock] 锚点附加失败(不阻塞):', e && e.message) }
    return next()
  })
  console.log('[du-base] ① du-clock v2 已挂载（agent/pre-step）')

  // ── ② du-quiet · runtime context 静默化 ──
  const DROP = new Set(['sandbox:policy', 'approval:policy'])
  ctx.on('system-prompt/assemble', (assembly, _context, next) => {
    return next().then((a) => {
      if (a && Array.isArray(a.contexts) && a.contexts.some((c) => DROP.has(c && c.name))) {
        return { ...a, contexts: a.contexts.filter((c) => !DROP.has(c.name)) }
      }
      return a
    })
  })
  console.log('[du-base] ② du-quiet 已挂载（system-prompt/assemble）')

  // ── ③ du-archive · 会话流增量归档 ──
  let prevLen = -1
  let counter = 0
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
    const lp = stamp()
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
  if (fspOK) {
    ctx.on('llm/stream', (options, next) => {
      Promise.resolve().then(() => archive(options))
        .catch((e) => console.error('[du-archive] 异常(不阻塞):', e && e.message))
      return next()
    })
    console.log('[du-base] ③ du-archive 已挂载（落盘 阅读材料/会话记录/<日期>/）')
  } else { console.error('[du-base] ③ du-archive: fs 缺席，未挂载') }

  // ── ④ dusync · /du-sync + /du-scan 端点（路径同进程唯一，冲突即 throw） ──
  const web = ctx.get('webServer')
  const webOK = !!(web && typeof web.register === 'function')
  async function readBody(req) {
    const dec = new TextDecoder()
    let text = ''
    for await (const chunk of req) text += dec.decode(chunk, { stream: true })
    text += dec.decode()
    return text
  }
  function send(res, status, obj) {
    res.writeHead(status, {
      'Content-Type': 'application/json; charset=utf-8',
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type',
    })
    res.end(JSON.stringify(obj))
  }
  async function writeNew(rel, body) {
    const t = await fsp.resolve(rel, { cwd: DU_ROOT })
    const st = await fsp.stat(t)
    if (st) return { t, exists: true }
    try {
      await fsp.writeText(t, body, { kind: 'createIfAbsent' }, undefined, POLICY)
      return { t, exists: false }
    } catch (e) {
      const s = String((e && (e.code || e.message)) || e)
      if (/FS_NOT_OBSERVED|exist/i.test(s)) return { t, exists: true }
      throw e
    }
  }
  if (fspOK && webOK) {
    ctx.effect(() => web.register({ kind: 'exact', path: '/du-sync', handler: async (req, res) => {
      if (req.method === 'OPTIONS') { send(res, 204, {}); return }
      if (req.method === 'GET') { send(res, 200, { ok: true, service: 'du-sync', version: 'du-base profile v1.0.2', note: 'POST {source,title,url,messages}' }); return }
      if (req.method !== 'POST') { send(res, 405, { ok: false, error: 'method not allowed' }); return }
      try {
        const j = JSON.parse(await readBody(req))
        const source = safeName(j.source) || '未命名来源'
        const title = safeName(j.title) || 'untitled'
        const msgs = Array.isArray(j.messages) ? j.messages : null
        if (!msgs || !msgs.length) { send(res, 400, { ok: false, error: 'messages 为空' }); return }
        const lp = stamp()
        const rel = '阅读材料/我的context备份/' + source + '/' + lp.date + '-' + lp.hms + '-' + title + '.txt'
        const lines = []
        lines.push('来源：' + source)
        lines.push('标题：' + (j.title || ''))
        lines.push('URL：' + (j.url || ''))
        lines.push('同步时间：' + lp.date + 'T' + lp.full + ' +08:00')
        lines.push('')
        for (const m of msgs) {
          const role = m && m.role ? String(m.role) : '?'
          const text = m && typeof m.text === 'string' ? m.text : ''
          if (text) lines.push('【' + role + '】\n' + text + '\n')
        }
        const r = await writeNew(rel, lines.join('\n'))
        if (r.exists) { send(res, 409, { ok: false, existing: rel, error: '同名文件已存在' }); return }
        send(res, 200, { ok: true, file: rel, resolved: fsp.processPath(r.t) })
      } catch (e) { send(res, 500, { ok: false, error: String((e && e.message) || e) }) }
    } }))
    ctx.effect(() => web.register({ kind: 'exact', path: '/du-scan', handler: async (req, res) => {
      if (req.method === 'OPTIONS') { send(res, 204, {}); return }
      if (req.method === 'GET') { send(res, 200, { ok: true, service: 'du-scan', version: 'du-base profile v1.0.2', note: 'POST {target,filename,text}' }); return }
      if (req.method !== 'POST') { send(res, 405, { ok: false, error: 'method not allowed' }); return }
      try {
        const j = JSON.parse(await readBody(req))
        const target = String(j.target || '').trim()
        const filename = safeName(j.filename)
        const text = typeof j.text === 'string' ? j.text : ''
        if (!target || !filename || !text) { send(res, 400, { ok: false, error: 'target/filename/text 缺失' }); return }
        if (target.includes('..') || filename.includes('..')) { send(res, 400, { ok: false, error: '非法路径' }); return }
        const rel = target.replace(/\/+$/, '') + '/' + filename
        const r = await writeNew(rel, text)
        if (r.exists) { send(res, 409, { ok: false, existing: rel, error: '同名文件已存在' }); return }
        send(res, 200, { ok: true, file: rel, resolved: fsp.processPath(r.t) })
      } catch (e) { send(res, 500, { ok: false, error: String((e && e.message) || e) }) }
    } }))
    console.log('[du-base] ④ dusync 已挂载（/du-sync + /du-scan）')
  } else { console.error('[du-base] ④ dusync: fs/webServer 缺席，未挂载') }

  // ── ⑤ du-trace v1.1 · 触迹记账 ──
  const WATCH = { read: 'file_path', read_image: 'file_path', edit: 'file_path', write: 'file_path' }
  function keyOf(name, args) {
    const a = args && typeof args === 'object' ? args : {}
    if (WATCH[name]) { const v = a[WATCH[name]]; return typeof v === 'string' ? v : null }
    if (name === 'glob') return a.pattern ? 'glob:' + a.pattern : null
    if (name === 'grep') return a.pattern ? 'grep:' + a.pattern : null
    if (name === 'pwsh') return a.description ? 'sh:' + a.description : null
    return null
  }
  if (fspOK) {
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
        buf.push({ ts: d.date + 'T' + d.full + '+08:00', name, key, session: exec && exec.agent ? String(exec.agent.id || '') : '' })
        if (buf.length >= 5) Promise.resolve().then(flush).catch(() => {})
      } catch (e) { console.error('[du-trace] 记账异常(不阻塞):', e && e.message) }
    })
    ctx.interval(() => { Promise.resolve().then(flush).catch(() => {}) }, 60000)
    ctx.effect(() => () => { Promise.resolve().then(flush).catch(() => {}) })
    console.log('[du-base] ⑤ du-trace v1.1 已挂载（当日去重）')
  } else { console.error('[du-base] ⑤ du-trace: fs 缺席，未挂载') }

  // ── ⑥ duwebp · insecure-context randomUUID polyfill（tapIndex 注入，幂等） ──
  if (webOK && typeof web.tapIndex === 'function') {
    const POLY = '<script>if(!window.__du_webpoly_uuid){window.__du_webpoly_uuid=1;(function(){try{if(!window.crypto)window.crypto={};if(typeof window.crypto.randomUUID!=="function"){var g=window.crypto.getRandomValues?function(a){window.crypto.getRandomValues(a)}:function(a){for(var i=0;i<a.length;i++)a[i]=(Math.random()*256)|0};window.crypto.randomUUID=function(){var b=new Uint8Array(16);g(b);b[6]=(b[6]&15)|64;b[8]=(b[8]&63)|128;var h=[],i;for(i=0;i<16;i++)h.push((b[i]+256).toString(16).slice(1));return h.slice(0,4).join("")+"-"+h.slice(4,6).join("")+"-"+h.slice(6,8).join("")+"-"+h.slice(8,10).join("")+"-"+h.slice(10).join("")}}}catch(e){}})()}</script>'
    ctx.effect(() => web.tapIndex((html) => {
      if (typeof html !== 'string' || html.indexOf('__du_webpoly_uuid') !== -1) return html
      if (/<head[^>]*>/i.test(html)) return html.replace(/<head[^>]*>/i, (m) => m + POLY)
      return html
    }))
    console.log('[du-base] ⑥ duwebp 已挂载（tapIndex polyfill）')
  } else { console.error('[du-base] ⑥ duwebp: webServer.tapIndex 缺席，未挂载') }

  // ── 装配回执（v1.0.2）── 静默降级的反面：每次装配留一份可读文件，下次启动自查直接读，不必再靠推断
  const degraded = !fspOK || !webOK
  const health = {
    at: nowLocal(),
    plugin: 'du-base v1.0.2',
    inject: 'timer,fs,webServer',
    fs: fspOK ? 'ok' : 'MISSING',
    webServer: webOK ? 'ok' : 'MISSING',
    parts: {
      clock: true,
      quiet: true,
      archive: fspOK,
      trace: fspOK,
      dusync: fspOK && webOK,
      duwebp: !!(webOK && typeof web.tapIndex === 'function'),
    },
    verdict: degraded ? 'DEGRADED' : 'OK',
  }
  if (degraded) console.error('[du-base] ⚠ 降级装配（服务未等齐）: ' + JSON.stringify(health))
  else console.log('[du-base] 装配回执 OK（六件齐，inject 三依赖已齐备）')
  if (fspOK) {
    fsp.resolve('项目/渡的大脑/du-base-health.txt', { cwd: DU_ROOT })
      .then((t) => fsp.writeText(t, JSON.stringify(health, null, 2) + '\n', undefined, undefined, POLICY))
      .catch((e) => console.error('[du-base] 回执写入失败(不阻塞):', e && e.message))
  }
}
