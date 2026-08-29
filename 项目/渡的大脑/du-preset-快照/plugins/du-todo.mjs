// du-todo · Todo 四象限窗口服务 —— du-os 第一窗口（preset 版，v4 多页面）
// 架构：文件即状态（Todo/<页名>.md，多页面）+ 端点即总线（127.0.0.1:3081）+ 单页即窗口（du-todo.html）。
// 端点：GET /（GUI）；GET /api/pages；GET /api/page?name=；POST /api/write（防覆盖）；
//       POST /api/newpage；POST /api/select；POST /api/notify（「叫渡」：inbox 注入唤醒）。
// 选中注入：systemPrompt.context order=151——选中态空返回 ''（不贡献），非空每轮注入任务块
//           （含页名）；UI=「上下文注入 @ du-todo」折叠条目，不进用户气泡。
// 变更流水：阅读材料/会话记录/触迹/Todo.changes.jsonl。
// 安全：bind 127.0.0.1；页名净化（禁路径字符/..，强制 .md）；进程兜底 uncaught 只记日志。
import http from 'node:http'
import { readFile, writeFile, appendFile, mkdir, stat, readdir } from 'node:fs/promises'
import { readFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'
import { randomUUID } from 'node:crypto'

const HERE = dirname(fileURLToPath(import.meta.url))
const HTML_PATH = join(HERE, 'du-todo.html')
const DU_ROOT = 'C:\\Users\\31617\\Desktop\\渡'
const TODO_DIR = join(DU_ROOT, 'Todo')
const CHANGES_PATH = join(DU_ROOT, '阅读材料', '会话记录', '触迹', 'Todo.changes.jsonl')
const PORT = 3081
const TEMPLATE = '# <页名>\n\n## Q1 重要且紧急\n## Q2 重要不紧急\n## Q3 紧急不重要\n## Q4 不重要不紧急\n'

process.on('uncaughtException', (e) => console.error('[du-todo] uncaught:', e && e.stack || e))
process.on('unhandledRejection', (e) => console.error('[du-todo] unhandledRejection:', e && (e.stack || e.message) || e))

export default function duTodo(_ctx, _config = {}) {
  return {
    inject: ['systemPrompt', 'agents'],
    apply(ctx) {
      if (!ctx.systemPrompt || typeof ctx.systemPrompt.context !== 'function') {
        console.error('[du-todo] systemPrompt 不可用'); return
      }
      let selectState = null

      function stamp() {
        return new Date(Date.now() + 28800000).toISOString().slice(0, 19) + '+08:00'
      }
      function fmtTask(t) {
        const parts = ['[当前任务] ' + (t && t.brief ? t.brief : '(未命名)')]
        if (t && t.page) parts.push('页：' + t.page)
        if (t && t.detail) parts.push('详情：' + t.detail)
        if (t && t.tags && t.tags.length) parts.push('标签：' + t.tags.join(' '))
        if (t && t.files && t.files.length) parts.push('关联文件：' + t.files.join('；'))
        if (t && t.created) parts.push('创建：' + t.created)
        return parts.join('\n')
      }

      ctx.systemPrompt.context({
        name: 'du-todo-selected',
        order: 151,
        text: () => (selectState ? fmtTask(selectState) : ''),
      })

      function safePageName(raw) {
        let n = String(raw || '').replace(/\.md$/i, '').replace(/[\\/:*?"<>|\r\n]+/g, '_').replace(/^\.+/, '').trim().slice(0, 30)
        if (!n || n.includes('..')) return null
        return n + '.md'
      }
      function pagePath(name) { return join(TODO_DIR, name) }
      function json(res, status, obj) {
        res.writeHead(status, { 'Content-Type': 'application/json; charset=utf-8', 'Cache-Control': 'no-store' })
        res.end(JSON.stringify(obj))
      }
      async function readBody(req) {
        const dec = new TextDecoder()
        let text = ''
        for await (const chunk of req) text += dec.decode(chunk, { stream: true })
        text += dec.decode()
        return text
      }
      async function logChange(entry) {
        try {
          await mkdir(dirname(CHANGES_PATH), { recursive: true })
          await appendFile(CHANGES_PATH, JSON.stringify({ ts: stamp(), ...entry }) + '\n', 'utf8')
        } catch (e) { console.error('[du-todo] changes 写入失败:', e && e.message) }
      }

      const server = http.createServer(async (req, res) => {
        try {
          const url = (req.url || '/').split('?')[0]
          const query = new URL(req.url || '/', 'http://x').searchParams
          if (req.method === 'GET' && (url === '/' || url === '/index.html')) {
            const html = readFileSync(HTML_PATH)
            res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8', 'Cache-Control': 'no-store' })
            res.end(html); return
          }
          if (req.method === 'GET' && url === '/api/pages') {
            await mkdir(TODO_DIR, { recursive: true })
            const files = (await readdir(TODO_DIR)).filter((f) => f.toLowerCase().endsWith('.md')).sort()
            json(res, 200, { pages: files.length ? files : ['主.md'] }); return
          }
          if (req.method === 'GET' && url === '/api/page') {
            const name = safePageName(query.get('name'))
            if (!name) { json(res, 400, { error: '页名非法' }); return }
            let content = TEMPLATE.replace('<页名>', name.replace(/\.md$/, '')), mtime = 0
            try { mtime = (await stat(pagePath(name))).mtimeMs; content = await readFile(pagePath(name), 'utf8') }
            catch (e) {}
            json(res, 200, { mtime, content, name }); return
          }
          if (req.method === 'POST' && url === '/api/write') {
            const body = JSON.parse(await readBody(req))
            const name = safePageName(body.name || '主')
            const content = typeof body.content === 'string' ? body.content : null
            if (!name || content === null) { json(res, 400, { error: 'name/content 缺失' }); return }
            let mtime = 0
            try { mtime = (await stat(pagePath(name))).mtimeMs } catch (e) { mtime = 0 }
            if (body.baseMtime !== undefined && body.baseMtime !== null && mtime - body.baseMtime > 2000) {
              const fresh = await readFile(pagePath(name), 'utf8').catch(() => '')
              json(res, 409, { error: '文件已被渡更新', mtime, content: fresh }); return
            }
            await mkdir(TODO_DIR, { recursive: true })
            await writeFile(pagePath(name), content, 'utf8')
            const now = (await stat(pagePath(name))).mtimeMs
            if (body.change) await logChange({ page: name, change: String(body.change).slice(0, 300) })
            json(res, 200, { ok: true, mtime: now, name }); return
          }
          if (req.method === 'POST' && url === '/api/newpage') {
            const body = JSON.parse(await readBody(req))
            const name = safePageName(body.name)
            if (!name) { json(res, 400, { error: '页名非法' }); return }
            await mkdir(TODO_DIR, { recursive: true })
            let exists = false
            try { await stat(pagePath(name)); exists = true } catch (e) {}
            if (exists) { json(res, 409, { error: '同名页面已存在', name }); return }
            await writeFile(pagePath(name), TEMPLATE.replace('<页名>', name.replace(/\.md$/, '')), 'utf8')
            await logChange({ page: name, change: '新建页面' })
            json(res, 200, { ok: true, name }); return
          }
          if (req.method === 'POST' && url === '/api/select') {
            const body = JSON.parse(await readBody(req))
            selectState = body && body.task ? body.task : null
            json(res, 200, { ok: true, selected: !!selectState }); return
          }
          if (req.method === 'POST' && url === '/api/notify') {
            let note = ''
            try { const b = JSON.parse(await readBody(req)); note = String(b.note || '').slice(0, 200) } catch (e) {}
            const agents = ctx.get('agents')
            const agent = agents && typeof agents.currentInitiator === 'function' ? agents.currentInitiator() : null
            if (!agent || !agent.inbox || typeof agent.inbox.append !== 'function') {
              json(res, 503, { error: '当前会话不可注入（inbox 缺席）' }); return
            }
            const text = '[du-todo] 久阳在 Todo GUI 请求你查看。' + (note ? '留言：' + note : '最近改动见 Todo.changes.jsonl。')
            agent.inbox.append('next-turn', {
              id: randomUUID(), role: 'user',
              content: [{ type: 'text', text }],
              source: { kind: 'plugin', plugin: 'du-todo' },
            })
            await logChange({ page: selectState && selectState.page, change: 'notify: ' + (note || '(无留言)') })
            json(res, 200, { ok: true }); return
          }
          json(res, 404, { error: 'not found' })
        } catch (e) {
          json(res, 500, { error: String((e && e.message) || e) })
        }
      })

      ctx.effect(() => {
        server.listen(PORT, '127.0.0.1')
        console.log('[du-todo] Todo 窗口已开 http://127.0.0.1:' + PORT + '（多页面 v4，数据目录 ' + TODO_DIR + '）')
        return () => { try { server.close() } catch (e) {} }
      }, 'du-todo http:3081')
    },
  }
}
