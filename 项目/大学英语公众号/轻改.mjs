// 轻改（copyedit pass）· 渡 · 2026-09-14
// 用途：把 秀米模板/原始/*.html 做一遍「轻微修改」，产出 成品/*.html。
// 设计原则（写作记忆条目 7：改动少必须是被论证出来的结论）：
//   R1 英文段落的标点归位——纯英文 <p> 里的全角标点（，。？！：；）改半角，
//      理由：中英混排模板里英文行仍用全角逗号，是排版源的中文输入法残留，读者一眼可见。
//   R2 语病级修补——"ahead of you you're" 缺逗号（原文照抄的歌词断句错误）。
//   R3 占位符标注——版权行的"本人瞎编（使用时请替换）"是模板占位，改成如实标注的实测稿标记。
//   不改：结构、内联样式、图片、任何 <p> 之外的标签。
// 用法：node 轻改.mjs <输入文件名> [输出后缀，默认 -v1]

import fs from 'node:fs'
import path from 'node:path'

const DIR_RAW = '秀米模板/原始'
const DIR_OUT = '成品'
const src = process.argv[2]
const suffix = process.argv[3] || '-v1'
if (!src) { console.log('用法：node 轻改.mjs <原始/里的文件名> [后缀]'); process.exit(1) }

const inPath = path.join(DIR_RAW, src)
let html = fs.readFileSync(inPath, 'utf8')
const before = html.length
const log = []

// R1：纯英文段落内的全角标点 → 半角
const FW = { '，': ', ', '。': '. ', '？': '? ', '！': '! ', '：': ': ', '；': '; ' }
let r1 = 0
html = html.replace(/<p([^>]*)>([^<]*)<\/p>/g, (m, attrs, text) => {
  const t = text.trim()
  if (!t) return m
  // 只在「无汉字」的段落里动——注意：全角标点本身也落在 CJK 区段，所以只数真正的汉字
  const han = (t.match(/[\u4e00-\u9fff]/g) || []).length
  const asciiWord = (t.match(/[A-Za-z]/g) || []).length
  if (han !== 0 || asciiWord < t.length * 0.4) return m
  let changed = false
  const nt = t.replace(/[，。？！：；]/g, (c) => { changed = true; return FW[c] }).replace(/[ \t]{2,}/g, ' ').replace(/\s+$/, '')
  if (!changed) return m
  r1++
  return '<p' + attrs + '>' + text.replace(t, nt) + '</p>'
})
if (r1) log.push('R1 英文标点归一半角：' + r1 + ' 段')

// R2：歌词断句缺逗号
const r2 = [/ahead of you you’re/g, /ahead of you you're/g]
let r2n = 0
for (const re of r2) {
  const m = html.match(re)
  if (!m) continue
  r2n += m.length
  html = html.replace(re, (s) => s.replace('you you', 'you, you'))
}
if (r2n) log.push('R2 补断句逗号（ahead of you, you\'re）：' + r2n + ' 处')

// R3：版权行占位符 → 如实标注（模板占位不改变事实，仅表明这是实测稿）
const OLD_CREDIT = '文字丨本人瞎编（使用时请替换）'
const NEW_CREDIT = '文字丨模板示例稿（渡 2026-09-14 轻改实测，发布前替换）'
if (html.includes(OLD_CREDIT)) { html = html.replace(OLD_CREDIT, NEW_CREDIT); log.push('R3 版权行占位符 → 实测标注') }

const outName = src.replace(/\.html$/i, '') + suffix + '.html'
fs.mkdirSync(DIR_OUT, { recursive: true })
fs.writeFileSync(path.join(DIR_OUT, outName), html, 'utf8')

console.log('输入：' + inPath + '（' + before + ' 字符）')
console.log(log.length ? log.map((x) => ' · ' + x).join('\n') : ' · （无需改动）')
console.log('输出：' + path.join(DIR_OUT, outName) + '（' + html.length + ' 字符，Δ' + (html.length - before) + '）')
