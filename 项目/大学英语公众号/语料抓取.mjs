// 语料抓取 · 渡 · 2026-09-14（可复用：系列每一期都用它取一手公版语料）
// 用法：node 语料抓取.mjs <期次目录名> <页面标题1> [标题2 ...]
// 例：  node 语料抓取.mjs 01-蒙娜丽莎 "1911 Encyclopædia Britannica/Leonardo da Vinci"
// 说明：走 Wikisource 的 action=parse&prop=text（渲染后纯文本），产出存 语料/<期次>/<标题>.txt
// 注意：Wikipedia 主站本机抓不到（fetch failed），Wikisource 正常；Gutenberg 亦可（公版全文）
import fs from 'node:fs'
import path from 'node:path'

const UA = { 'User-Agent': 'DuCorpusBot/0.1 (educational research)', Accept: '*/*' }
const [dir, ...titles] = process.argv.slice(2)
if (!dir || !titles.length) { console.log('用法：node 语料抓取.mjs <期次目录名> <页面标题...>'); process.exit(1) }

const strip = (h) => h
  .replace(/<style[\s\S]*?<\/style>/gi, ' ')
  .replace(/<script[\s\S]*?<\/script>/gi, ' ')
  .replace(/<[^>]+>/g, ' ')
  .replace(/&#160;|&nbsp;/g, ' ')
  .replace(/&amp;/g, '&')
  .replace(/\s+/g, ' ')
  .trim()

const out = path.join('语料', dir)
fs.mkdirSync(out, { recursive: true })
for (const title of titles) {
  const url = 'https://en.wikisource.org/w/api.php?action=parse&prop=text&redirects=1&format=json&page=' + encodeURIComponent(title)
  try {
    const r = await fetch(url, { headers: UA })
    const j = JSON.parse(await r.text())
    const text = strip((j.parse && j.parse.text && j.parse.text['*']) || '')
    const file = path.join(out, title.replace(/[\\/:*?"<>|]/g, '_').slice(0, 80) + '.txt')
    fs.writeFileSync(file, 'SOURCE: ' + title + '\nURL: ' + url + '\n授权: 公版（Wikisource）\n\n' + text, 'utf8')
    console.log('OK ' + title + ' -> ' + file + ' (' + text.length + ' chars)')
  } catch (e) {
    console.log('FAIL ' + title + ': ' + e.message)
  }
}
