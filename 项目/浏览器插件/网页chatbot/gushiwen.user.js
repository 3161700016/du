// ==UserScript==
// @name         古文岛庄子 → 渡
// @namespace    du
// @version      0.2.0
// @description  抓取古文岛(gushiwen.cn)章节原文，按页面标题自动命名，同步到渡（POST /du-scan）
// @match        https://www.gushiwen.cn/guwen/bookv_*.aspx
// @grant        GM_xmlhttpRequest
// @connect      127.0.0.1
// @run-at       document-idle
// ==/UserScript==

(function () {
  'use strict';

  // 根据页面标题自动推导篇名与文件名
  function derive() {
    var raw = '';
    var h1 = document.querySelector('h1');
    if (h1 && h1.innerText && h1.innerText.trim()) raw = h1.innerText.trim();
    if (!raw) raw = (document.title || '').trim();
    raw = raw.replace(/[-_—|·]\s*(古诗文网|gushiwen).*$/i, '')
             .replace(/[-_—|·\s]+$/, '').trim();
    var name = raw.replace(/第[一二三四五六七八九十]+$/, '').trim() || raw;
    return { header: raw, name: name, filename: '庄子·' + name + '.txt' };
  }

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

  function paragraphs(node) {
    var text = (node && node.innerText) ? node.innerText : '';
    var paras = text.split(/\n+/).map(function (s) { return s.trim(); }).filter(Boolean);
    return paras.map(function (p) { return '\u3000\u3000' + p; }).join('\n\n');
  }

  function scan() {
    var d = derive();
    var node = getContentNode();
    if (!node) { alert('没抓到正文，选择器要改'); return; }
    var body = d.header + '\n\n' + paragraphs(node);
    GM_xmlhttpRequest({
      method: 'POST',
      url: 'http://127.0.0.1:3080/du-scan',
      headers: { 'Content-Type': 'application/json' },
      data: JSON.stringify({ target: '阅读材料/庄子', filename: d.filename, text: body }),
      timeout: 10000,
      onload: function (r) {
        try {
          var j = JSON.parse(r.responseText);
          alert(j.ok ? ('已存：' + j.file + '\n推导标题：' + d.header) : ('失败：' + j.error));
        } catch (e) { alert('响应解析失败：' + r.responseText); }
      },
      onerror: function () { alert('请求失败（DSH 是否在运行？）'); },
      ontimeout: function () { alert('请求超时'); }
    });
  }

  function addButton() {
    var btn = document.createElement('button');
    btn.textContent = '扒给渡';
    btn.title = '把本章原文同步到渡（阅读材料/庄子/）';
    btn.style.cssText = 'position:fixed;right:20px;bottom:80px;z-index:99999;padding:10px 18px;' +
      'border:none;border-radius:20px;background:#0e7490;color:#fff;font-size:14px;' +
      'cursor:pointer;box-shadow:0 2px 10px rgba(0,0,0,.35);font-family:system-ui,sans-serif;';
    btn.onclick = scan;
    document.body.appendChild(btn);
  }

  if (document.body) { addButton(); }
  else { window.addEventListener('DOMContentLoaded', addButton); }
})();
