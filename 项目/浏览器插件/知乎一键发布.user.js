// ==UserScript==
// @name         知乎一键发布 · 渡稿直投
// @namespace    du.zhihu.publish
// @version      0.2
// @description  从本地 待发布/ 直接选稿零粘贴：专栏=注入标题+正文；回答=记住待注入稿→自动打开问题页→注入正文；发布按钮定位高亮，点击留人工确认。提问件按裁定（UI 不友好）人工处理。后端=DSH 的 GET /du-drafts（dudrft-3）。
// @author       渡
// @match        https://www.zhihu.com/question/*
// @match        https://zhuanlan.zhihu.com/write
// @match        https://www.zhihu.com/creator*
// @grant        GM_xmlhttpRequest
// @grant        GM_setValue
// @grant        GM_getValue
// @connect      127.0.0.1
// @connect      localhost
// ==/UserScript==

/*
 * v0.2 变更（2026-09-02 深夜，久阳实测反馈驱动）：
 * ① /du-drafts 选稿：不打开文件不复制，面板直接列 待发布/，点选注入。
 * ② 专栏标题注入：从 md 一级标题解析（剥「——回答/提问 D₀」「——专栏」尾巴），
 *    native setter 写入标题输入框；正文注入沿用 v0.1 的合成 paste（已实测可用）。
 * ③ 回答页支持：回答稿带 问题 URL →「开题页并注入」=记住待注入稿→打开问题页→
 *    页面加载时自动 ensureEditor（必要时点「写回答」）→注入正文→清除待办。
 * ④ 提问件：列表里标「人工」，不做注入（久阳裁定 UI 不友好，手动来）。
 * ⑤ 发布按钮：仍只定位+高亮，不自动点击——发布是不可逆动作，留人工确认。
 * ⑥ mtime 字段在 fs 服务返回 0 → 列表按文件名降序（文件名自带日期前缀=时序）。
 * 待实测回填：回答页编辑器与「写回答」按钮选择器（脚本已做多候选+按钮兜底）。
 */

(function () {
  'use strict'
  const API = 'http://127.0.0.1:3080/du-drafts'

  function gm(url) {
    return new Promise((resolve, reject) => {
      GM_xmlhttpRequest({ method: 'GET', url, timeout: 8000,
        onload: (r) => { try { resolve(JSON.parse(r.responseText)) } catch (e) { reject(e) } },
        onerror: () => reject(new Error('network')), ontimeout: () => reject(new Error('timeout')) })
    })
  }

  function parseDraft(file, content) {
    const lines = content.split('\n')
    let title = ''
    for (let i = 0; i < Math.min(lines.length, 12); i++) {
      if (/^#\s+/.test(lines[i])) { title = lines[i].replace(/^#\s+/, ''); break }
    }
    title = title.replace(/——(回答|提问)\s*D₀\s*$/, '').replace(/——专栏\s*$/, '').replace(/\s*D₀\s*$/, '').trim()
    let body = content
    const m = content.match(/正文草稿：[^\n]*\n/)
    if (m) body = content.slice(m.index + m[0].length)
    const cut = body.indexOf('隔夜改检查单')
    if (cut > -1) body = body.slice(0, cut)
    body = body.replace(/^\s*---\s*\n?/, '').trim()
    const qm = content.match(/https:\/\/www\.zhihu\.com\/question\/\d+/)
    const kind = qm ? '回答' : /提问/.test(file) ? '提问' : '专栏'
    return { file, title, body, questionUrl: qm ? qm[0] : null, kind }
  }

  function mdToHtml(md) {
    const esc = (s) => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    const inline = (s) => esc(s)
      .replace(/\*\*([^*]+)\*\*/g, '<b>$1</b>')
      .replace(/\*([^*]+)\*/g, '<i>$1</i>')
      .replace(/`([^`]+)`/g, '<code>$1</code>')
      .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2">$1</a>')
    return md.split(/\n{2,}/).map((block) => {
      const b = block.trim()
      if (!b) return ''
      if (/^###\s/.test(b)) return '<h3>' + inline(b.replace(/^###\s/, '')) + '</h3>'
      if (/^##\s/.test(b)) return '<h2>' + inline(b.replace(/^##\s/, '')) + '</h2>'
      if (/^#\s/.test(b)) return '<h1>' + inline(b.replace(/^#\s/, '')) + '</h1>'
      if (/^>\s?/.test(b)) return '<blockquote><p>' + inline(b.replace(/^>\s?/gm, '')) + '</p></blockquote>'
      return b.split('\n').map((line) => '<p>' + inline(line) + '</p>').join('')
    }).filter(Boolean).join('')
  }

  function findEditor() {
    const sels = ['.public-DraftEditor-content[contenteditable="true"]',
      '.Editable[contenteditable="true"]',
      '[contenteditable="true"].zhc-editor']
    for (const s of sels) { const el = document.querySelector(s); if (el) return el }
    const all = [...document.querySelectorAll('[contenteditable="true"]')]
    return all.find((el) => el.offsetHeight > 40) || null
  }

  async function ensureEditor() {
    for (let i = 0; i < 4; i++) {
      const ed = findEditor()
      if (ed) return ed
      if (i === 0) {
        const btn = [...document.querySelectorAll('button, [role="button"]')]
          .find((b) => /^(写回答|开始写文章|写文章)$/.test((b.textContent || '').trim()))
        if (btn) btn.click()
      }
      await new Promise((r) => setTimeout(r, 900))
    }
    return findEditor()
  }

  function injectHtml(editor, html) {
    editor.focus()
    const dt = new DataTransfer()
    dt.setData('text/html', html)
    dt.setData('text/plain', html.replace(/<[^>]+>/g, '\n'))
    editor.dispatchEvent(new ClipboardEvent('paste', { clipboardData: dt, bubbles: true, cancelable: true }))
    if (!editor.textContent.trim()) {
      const text = html.replace(/<\/(p|h1|h2|h3|blockquote)>/g, '\n\n').replace(/<[^>]+>/g, '')
      for (const seg of text.split('\n\n').filter(Boolean)) {
        document.execCommand('insertText', false, seg.trim())
        document.execCommand('insertText', false, '\n\n')
      }
    }
  }

  function setTitle(text) {
    const t = [...document.querySelectorAll('textarea, input')]
      .find((el) => /标题/.test(el.placeholder || el.getAttribute('placeholder') || ''))
    if (!t) return false
    const proto = t.tagName === 'TEXTAREA' ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype
    Object.getOwnPropertyDescriptor(proto, 'value').set.call(t, text)
    t.dispatchEvent(new Event('input', { bubbles: true }))
    return true
  }

  function highlightPublish() {
    const target = [...document.querySelectorAll('button')]
      .find((b) => /发布/.test(b.textContent || '') && !b.disabled)
    if (!target) return '未找到发布按钮（选择器需回填）'
    target.scrollIntoView({ behavior: 'smooth', block: 'center' })
    const old = target.style.boxShadow
    target.style.boxShadow = '0 0 0 4px #ff9607'
    setTimeout(() => { target.style.boxShadow = old }, 2500)
    return '发布按钮已高亮——点击留给你'
  }

  async function injectDraft(d) {
    const editor = await ensureEditor()
    if (!editor) return '未找到编辑器（选择器需回填）'
    if (location.hostname === 'zhuanlan.zhihu.com' && d.title) {
      if (!setTitle(d.title)) return '标题框未找到（选择器需回填），未注入'
    }
    injectHtml(editor, mdToHtml(d.body))
    return '已注入《' + (d.title || d.file) + '》 ' + d.body.length + ' 字——请目检格式（§2.6）'
  }

  function panel() {
    const p = document.createElement('div')
    p.style.cssText = 'position:fixed;right:16px;bottom:16px;z-index:99999;width:360px;max-height:70vh;overflow:auto;background:#fff;border:1px solid #d3d3d3;border-radius:8px;box-shadow:0 4px 16px rgba(0,0,0,.15);font:13px/1.5 system-ui;padding:10px'
    document.body.appendChild(p)
    const msg = (t) => { const el = p.querySelector('#du-msg'); if (el) el.textContent = t }

    function detail(d) {
      const isZhuanlan = location.hostname === 'zhuanlan.zhihu.com'
      p.innerHTML = `<div style="font-weight:600;margin-bottom:6px">《${(d.title || d.file).replace(/</g, '&lt;')}》 <span style="color:#999;font-weight:400">${d.kind}</span></div>`
        + (isZhuanlan ? `<div style="margin-bottom:6px">标题：<input id="du-title" style="width:100%;box-sizing:border-box" value="${(d.title || '').replace(/"/g, '&quot;')}"></div>` : '')
        + `<textarea id="du-body" style="width:100%;height:160px;box-sizing:border-box;font-size:12px">${d.body.replace(/</g, '&lt;')}</textarea>
        <div style="margin-top:6px;display:flex;gap:6px;flex-wrap:wrap">
          <button id="du-inject">注入${isZhuanlan ? '标题+' : ''}正文</button>
          <button id="du-pub">定位发布</button>
          <button id="du-back">←列表</button>
        </div>
        <div id="du-msg" style="margin-top:6px;color:#666;font-size:12px"></div>`
      p.querySelector('#du-back').onclick = () => list()
      p.querySelector('#du-inject').onclick = async () => {
        const d2 = { ...d,
          title: p.querySelector('#du-title') ? p.querySelector('#du-title').value : d.title,
          body: p.querySelector('#du-body').value }
        msg(await injectDraft(d2))
      }
      p.querySelector('#du-pub').onclick = () => msg(highlightPublish())
    }

    async function list() {
      p.innerHTML = `<div style="font-weight:600;margin-bottom:6px">渡 · 待发布稿件 <span style="color:#999;font-weight:400">v0.2</span></div><div id="du-lst" style="color:#666">读取 /du-drafts …</div><div id="du-msg" style="margin-top:6px;color:#666;font-size:12px"></div>`
      try {
        const r = await gm(API)
        const drafts = (r.drafts || []).sort((a, b) => (a.file < b.file ? 1 : -1))
        const lst = p.querySelector('#du-lst')
        if (!drafts.length) { lst.innerHTML = '待发布为空'; return }
        lst.innerHTML = ''
        for (const d0 of drafts) {
          const row = document.createElement('div')
          row.style.cssText = 'padding:6px 4px;border-bottom:1px solid #eee;cursor:pointer'
          row.textContent = '📄 ' + d0.file
          row.onclick = async () => {
            try {
              const raw = await gm(API + '?name=' + encodeURIComponent(d0.file))
              const d = parseDraft(raw.file, raw.content)
              if (d.kind === '提问') { msg('提问件按裁定人工处理'); return }
              if (d.kind === '回答' && d.questionUrl && !location.href.startsWith(d.questionUrl)) {
                GM_setValue('du_pending', JSON.stringify(d))
                window.open(d.questionUrl, '_blank')
                msg('已记住《' + (d.title || d.file) + '》并打开问题页——新页面自动注入')
                return
              }
              detail(d)
            } catch (e) { msg('取稿失败: ' + e.message) }
          }
          lst.appendChild(row)
        }
      } catch (e) {
        p.querySelector('#du-lst').innerHTML = '读不到 /du-drafts（DSH 没开？）——先起 DSH 再刷新页面'
      }
    }

    // 跨页待注入：问题页加载时自动处理
    const pending = GM_getValue('du_pending')
    if (pending) {
      GM_setValue('du_pending', '')
      try {
        const d = JSON.parse(pending)
        if (location.href.startsWith(d.questionUrl || '')) {
          list()
          injectDraft(d).then((t) => msg(t))
          return
        }
      } catch (e) {}
    }
    list()
  }

  window.addEventListener('load', panel)
})()
