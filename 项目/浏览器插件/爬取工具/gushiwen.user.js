// ==UserScript==
// @name         古文岛庄子 → 渡
// @namespace    du
// @version      0.4.0
// @description  抓取古文岛(gushiwen.cn)章节原文，按页面标题自动命名；成功弹窗显示落盘绝对路径（POST /du-scan）
// @match        https://www.gushiwen.cn/guwen/bookv_*.aspx
// @grant        GM_xmlhttpRequest
// @connect      127.0.0.1
// @run-at       document-idle
// ==/UserScript==

(function () {
  'use strict';

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

  // 标题推导 v0.3 起：正文容器祖先内的 h1 → 全局首个 h1 → document.title。
  // 所有失败路径回显诊断信息。
  function derive() {
    var allH1 = [];
    document.querySelectorAll('h1').forEach(function (h) {
      var t = (h.innerText || '').trim();
      if (t) allH1.push(t);
    });

    var raw = '', src = '';
    var node = getContentNode();
    if (node) {
      var anc = node;
      for (var i = 0; i < 6 && anc && anc !== document.body; i++) {
        var h = anc.querySelector ? anc.querySelector('h1') : null;
        if (h && (h.innerText || '').trim()) {
          raw = h.innerText.trim();
          src = '正文祖先内h1(第' + i + '层)';
          break;
        }
        anc = anc.parentElement;
      }
    }
    if (!raw && allH1.length) { raw = allH1[0]; src = '全局首个h1'; }
    if (!raw) { raw = (document.title || '').trim(); src = 'document.title'; }

    raw = raw.replace(/[-_—|·]\s*(古诗文网|gushiwen).*$/i, '')
             .replace(/(原文|译文及注释|翻译及赏析|原文、翻译|拼音版)+\s*$/, '')
             .replace(/[-_—|·\s]+$/, '').trim();
    var inner = raw.replace(/^(内篇|外篇|杂篇)[·•]?\s*/, '')
                   .replace(/第[一二三四五六七八九十]+$/, '')
                   .trim() || raw;

    return {
      header: raw,
      name: inner,
      filename: '庄子·' + inner + '.txt',
      allH1: allH1.slice(0, 4),
      src: src
    };
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
          if (j.ok) {
            alert('已存（绝对路径）：' + (j.resolved || j.file) +
                  '\n\n标题源：' + d.src +
                  '\n推导标题：' + d.header +
                  '\n页面h1候选：' + (d.allH1.join(' | ') || '(无)'));
          } else {
            alert((j.existing ? ('防覆盖拦截：同名文件已存在\n' + j.existing + '\n\n这是预期保护行为；若确需更新请告诉渡。')
                              : ('失败：' + j.error)) +
                  '\n\n标题源：' + d.src +
                  '\n推导标题：' + d.header +
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
    btn.title = '把本章原文同步到渡（阅读材料/庄子/）v0.4';
    btn.style.cssText = 'position:fixed;right:20px;bottom:80px;z-index:99999;padding:10px 18px;' +
      'border:none;border-radius:20px;background:#0e7490;color:#fff;font-size:14px;' +
      'cursor:pointer;box-shadow:0 2px 10px rgba(0,0,0,.35);font-family:system-ui,sans-serif;';
    btn.onclick = scan;
    document.body.appendChild(btn);
  }

  if (document.body) { addButton(); }
  else { window.addEventListener('DOMContentLoaded', addButton); }
})();
