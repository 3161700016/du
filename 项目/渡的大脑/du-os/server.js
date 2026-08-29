// du-os Todo 窗口服务（独立脚本版）· v4 多页面
// 与 preset 插件 du-todo.mjs 同构：同一 Todo/ 目录、同一端点协议。
// v4：多页面——每页一份 md（Todo/<页名>.md），书签切换/新建；数据目录 渡工作区/Todo/。
// 安全：页名净化（禁路径字符与 ..，强制 .md 后缀）；bind 127.0.0.1；全端点 no-store。
// 进程兜底：uncaught 只记日志不退出（2026-08-29 教训）。
import http from 'node:http'
import { readFile, writeFile, appendFile, mkdir, stat, readdir } from 'node:fs/promises'
import { readFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

const HERE = dirname(fileURLToPath(import.meta.url))
const HTML_PATH = join(HERE, 'du-todo.html')
const DU_ROOT = 'C:\\Users\\31617\\Desktop\\渡'
const TODO_DIR = join(DU_ROOT, 'Todo')
const CHANGES_PATH = join(DU_ROOT, '阅读材料', '会话记录', '触迹', 'Todo.changes.jsonl')
const SELECT_PATH = join(DU_ROOT, '阅读材料', '会话记录', '触迹', 'Todo.select.json')
const PORT = 3081
const TEMPLATE = '# <页名>\n\n## Q1 重要且紧急\n## Q2 重要不紧急\n## Q3 紧急不重要\n## Q4 不重要不紧急\n'

process.on('uncaughtException', (e) => console.error('[du-todo] uncaught:', e && e.stack || e))
process.on('unhandledRejection', (e) => console.error('[du-todo] unhandledRejection:', e && (e.stack || e.message) || e))

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
    await appendFile(CHANGES_PATH, JSON.stringify({ ts: new Date(Date.now() + 28800000).toISOString().slice(0, 19) + '+08:00', ...entry }) + '\n', 'utf8')
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
      await mkdir(dirname(SELECT_PATH), { recursive: true })
      await writeFile(SELECT_PATH, JSON.stringify({ ts: new Date().toISOString(), task: body && body.task ? body.task : null }), 'utf8')
      json(res, 200, { ok: true, selected: !!(body && body.task) }); return
    }
    if (req.method === 'POST' && url === '/api/notify') {
      let note = ''
      try { const b = JSON.parse(await readBody(req)); note = String(b.note || '').slice(0, 200) } catch (e) {}
      await logChange({ change: 'notify: ' + (note || '(无留言)') + '（独立服务模式：渡请在下轮读 changes）' })
      json(res, 200, { ok: true, note: '已记录；独立服务模式下请在 DSH 提一句即可' }); return
    }
    json(res, 404, { error: 'not found' })
  } catch (e) {
    json(res, 500, { error: String((e && e.message) || e) })
  }
})

server.listen(PORT, '127.0.0.1', () => console.log('[du-todo] 独立服务已开 http://127.0.0.1:' + PORT + '（多页面 v4，数据目录 ' + TODO_DIR + '）'))
