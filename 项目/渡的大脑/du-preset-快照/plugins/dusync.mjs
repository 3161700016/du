// dusync-plugin · /du-sync + /du-scan 本地同步端点 —— 渡的常驻基建
// （2026-08-29 由动态插件 dusync-3/pkg-3 固化；命名与已停用的 DuSync 计划任务永久断开混淆）
// 协议：POST /du-sync {source,title,url,messages} → 阅读材料/我的context备份/<source>/；
//       POST /du-scan {target,filename,text} → 阅读材料/<target>/，撞库 409 {ok:false,existing}。
// 浏览器侧零改动兼容：ChatGPT 书签脚本、du-sync.user.js、gushiwen v0.5。
// 机制依据（2026-08-29 源码核实）：WebRoute{kind:'exact',path,handler(req,res)} 持 Node 原生
// req/res；webServer.register 返回裸 Map disposer，须用 ctx.effect 挂 Fiber；
// 动态宿主无 Buffer 的顾虑在 preset（完整 Node）不存在，但 TextDecoder 分块写法保持一致。
export default function duSync(_ctx, _config = {}) {
  return {
    apply(ctx) {
      const fsp = ctx.get('fs')
      const web = ctx.get('webServer')
      if (!fsp || typeof fsp.resolve !== 'function' || !web || typeof web.register !== 'function') {
        console.error('[dusync] fs/webServer 缺席')
        return
      }
      const DU_ROOT = 'C:\\Users\\31617\\Desktop\\渡'
      const POLICY = { mode: 'workspace-write', workspaceRoot: DU_ROOT }

      function localStamp() {
        const d = new Date(Date.now() + 28800000)
        const iso = d.toISOString()
        return { date: iso.slice(0, 10), hms: iso.slice(11, 19).replace(/:/g, ''), full: iso.slice(11, 19) }
      }

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

      function safeName(s) {
        return String(s || '').replace(/[\\/:*?"<>|\r\n]+/g, '_').slice(0, 80).trim()
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

      ctx.effect(() => web.register({ kind: 'exact', path: '/du-sync', handler: async (req, res) => {
        if (req.method === 'OPTIONS') { send(res, 204, {}); return }
        if (req.method === 'GET') { send(res, 200, { ok: true, service: 'du-sync', version: 'dusync-plugin preset', note: 'POST {source,title,url,messages}' }); return }
        if (req.method !== 'POST') { send(res, 405, { ok: false, error: 'method not allowed' }); return }
        try {
          const j = JSON.parse(await readBody(req))
          const source = safeName(j.source) || '未命名来源'
          const title = safeName(j.title) || 'untitled'
          const msgs = Array.isArray(j.messages) ? j.messages : null
          if (!msgs || !msgs.length) { send(res, 400, { ok: false, error: 'messages 为空' }); return }
          const lp = localStamp()
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
        if (req.method === 'GET') { send(res, 200, { ok: true, service: 'du-scan', version: 'dusync-plugin preset', note: 'POST {target,filename,text}' }); return }
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

      console.log('[dusync-plugin] /du-sync + /du-scan 已挂载（exact 路由，CORS 全开，落盘 ' + DU_ROOT + '）')
    },
  }
}
