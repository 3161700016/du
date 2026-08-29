// ==UserScript==
// @name         古文岛 → 渡
// @namespace    du
// @version      0.5.0
// @description  抓取古文岛(gushiwen.cn)章节原文，书名从页面锚定，按 阅读材料/<书名>/<书名>·<章节>.txt 落盘（POST /du-scan）
// @match        https://www.gushiwen.cn/guwen/bookv_*.aspx
// @grant        GM_xmlhttpRequest
// @connect      127.0.0.1
// @run-at       document-idle
// ==/UserScript==

(function () {
  'use strict';

  // ── v0.5 书名锚定（2026-08-29 DSH 端渡）────────────────────────
  // 修复 v0.4 事故：书名硬编码「庄子·」+ 目录硬编码「阅读材料/庄子」，
  // 导致《文心雕龙·体性》被误存为 庄子/庄子·体性.txt。
  //
  // 书名证据链（按优先级）：
  //   ① document.title：「书名·章节名_古文岛_原古诗文网」→ 按 · 分割取前段。
  //     （2026-08-29 实证：原道第一页 title = "文心雕龙·原道第一_古文岛_原古诗文网"；
  //       章节页内唯一的 /guwen/book_*.aspx 链接文本=「目录」，不含书名，不可用。）
  //   ② title 无 · 结构 → h1 兜底章节名，书名走 ③。
  //   ③ prompt 手动输入兜底（留空取消）。
  // 目录与文件名均随书名走：阅读材料/<书名>/<书名>·<章节>.txt
  // ────────────────────────────────────────────────

  function getContentNode() {
    var sels = ['.contson', '#contson', '.bookcont', '.main3', '.cont', '.main4'];
    for (var i = 0; i < sels.length; i++) {
      var el = document.querySelector(sels[i]);
      if (el && el.innerText && el.innerText.trim().length > 50) return el;
    }
    // 兜底：正文最长的 div
    var best = null, bestLen = 0;
    document.querySelectorAll('div').forEach(function (d) {
      var t = d.innerText ? d.innerText.trim() : '';
      if (t.length > bestLen && t.length < 60000) { bestLen = t.length; best = d; }
    });
    return best;
  }

  function cleanTitle(t) {
    return (t || '').replace(/[_\-—|·]\s*(古文岛|古诗文网|gushiwen)[\s\S]*$/i, '').trim();
  }

  function derive() {
    var allH1 = [];
    document.querySelectorAll('h1').forEach(function (h) {
      var x = (h.innerText || '').trim();
      if (x) allH1.push(x);
    });

    var t = cleanTitle(document.title);
    var book = '', chapter = '', src = '';

    var dot = t.indexOf('·');
    if (dot > 0) {
      book = t.slice(0, dot).trim();
      chapter = t.slice(dot + 1).trim();
      src = 'title·分割(书名=' + book + ')';
    }
    if (!chapter && allH1.length) { chapter = allH1[0]; src = (src ? src + '+' : '') + 'h1'; }
    if (!chapter && t) { chapter = t; src = (src ? src + '+' : '') + 'title整体'; }

    // 章节名净化：去 篇/卷前缀 与 序号尾（原道第一→原道；体性第二十七→体性）
    var inner = chapter.replace(/^(内篇|外篇|杂篇|卷[一二三四五六七八九十百]+)[·•]?\s*/, '')
                       .replace(/第[一二三四五六七八九十百]+$/, '')
                       .trim() || chapter;

    return {
      book: book,
      chapterRaw: chapter,
      name: inner,
      allH1: allH1.slice(0, 4),
      src: src || '无',
      titleRaw: document.title || ''
    };
  }

  function askBook(d) {
    var b = prompt('未能从页面标题自动锚定书名。\n页面title：' + d.titleRaw +
                   '\n\n请输入书名（如：文心雕龙）。留空取消。', d.book || '');
    return (b || '').trim();
  }

  function paragraphs(node) {
    var text = (node && node.innerText) ? node.innerText : '';
    var paras = text.split(/\n+/).map(function (s) { return s.trim(); }).filter(Boolean);
    return paras.map(function (p) { return '\u3000\u3000' + p; }).join('\n\n');
  }

  function scan() {
    var d = derive();
    var node = getContentNode();
    if (!node) { alert('没抓到正文，选择器要改'); return; }

    var book = d.book;
    if (!book) book = askBook(d);
    if (!book) { alert('未提供书名，已取消。'); return; }
    if (!/^[^\\/:*?"<>|]{1,12}$/.test(book)) {
      alert('书名「' + book + '」为空、含非法字符或超过12字，已取消。\n\n页面title：' + d.titleRaw);
      return;
    }

    var filename = book + '·' + d.name + '.txt';
    var body = book + '·' + d.chapterRaw + '\n\n' + paragraphs(node);

    GM_xmlhttpRequest({
      method: 'POST',
      url: 'http://127.0.0.1:3080/du-scan',
      headers: { 'Content-Type': 'application/json' },
      data: JSON.stringify({ target: '阅读材料/' + book, filename: filename, text: body }),
      timeout: 10000,
      onload: function (r) {
        try {
          var j = JSON.parse(r.responseText);
          if (j.ok) {
            alert('已存（绝对路径）：' + (j.resolved || j.file) +
                  '\n\n书名源：' + d.src +
                  '\n推导落盘：阅读材料/' + book + '/' + filename +
                  '\n页面h1候选：' + (d.allH1.join(' | ') || '(无)'));
          } else {
            alert((j.existing ? ('防覆盖拦截：同名文件已存在\n' + j.existing + '\n\n这是预期保护行为；若确需更新请告诉渡。')
                              : ('失败：' + j.error)) +
                  '\n\n书名源：' + d.src +
                  '\n推导落盘：阅读材料/' + book + '/' + filename +
                  '\n页面h1候选：' + (d.allH1.join(' | ') || '(无)'));
          }
        } catch (e) { alert('响应解析失败：' + String(r.responseText).slice(0, 300)); }
      },
      onerror: function () { alert('请求失败（DSH 是否在运行？du-sync 端点插件是否活着？）'); },
      ontimeout: function () { alert('请求超时'); }
    });
  }

  function addButton() {
    var btn = document.createElement('button');
    btn.textContent = '扒给渡';
    btn.title = '把本章原文同步到渡（阅读材料/<书名>/）v0.5 书名锚定版';
    btn.style.cssText = 'position:fixed;right:20px;bottom:80px;z-index:99999;padding:10px 18px;' +
      'border:none;border-radius:20px;background:#0e7490;color:#fff;font-size:14px;' +
      'cursor:pointer;box-shadow:0 2px 10px rgba(0,0,0,.35);font-family:system-ui,sans-serif;';
    btn.onclick = scan;
    document.body.appendChild(btn);
  }

  if (document.body) { addButton(); }
  else { window.addEventListener('DOMContentLoaded', addButton); }
})();
