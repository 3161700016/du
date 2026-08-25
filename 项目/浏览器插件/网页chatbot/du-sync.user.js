// ==UserScript==
// @name         发给渡 (du-sync)
// @namespace    du
// @version      0.1.0
// @description  在 ChatGPT 页面加「发给渡」按钮，把对话同步到本地 DSH（http://127.0.0.1:3080/du-sync）
// @match        https://chatgpt.com/*
// @match        https://chat.openai.com/*
// @grant        GM_xmlhttpRequest
// @connect      127.0.0.1
// @run-at       document-idle
// ==/UserScript==

(function () {
  'use strict';

  function extract() {
    var msgs = [];
    document.querySelectorAll('[data-message-author-role]').forEach(function (el) {
      var role = el.getAttribute('data-message-author-role');
      var inner = el.querySelector('.markdown') || el;
      var t = inner.innerText.trim();
      if (t) msgs.push({ role: role, text: t });
    });
    return msgs;
  }

  function sync() {
    var msgs = extract();
    if (!msgs.length) { alert('没抓到对话，选择器要改'); return; }
    var title = (document.title || '').replace(/\s*-\s*ChatGPT.*$/, '').trim() || 'untitled';
    GM_xmlhttpRequest({
      method: 'POST',
      url: 'http://127.0.0.1:3080/du-sync',
      headers: { 'Content-Type': 'application/json' },
      data: JSON.stringify({ source: 'GPT', title: title, url: location.href, messages: msgs }),
      timeout: 10000,
      onload: function (r) {
        try {
          var j = JSON.parse(r.responseText);
          alert(j.ok ? ('已同步给渡：' + j.file) : ('失败：' + j.error));
        } catch (e) { alert('响应解析失败：' + r.responseText); }
      },
      onerror: function () { alert('请求失败（DSH 是否在运行？）'); },
      ontimeout: function () { alert('请求超时'); }
    });
  }

  function addButton() {
    var btn = document.createElement('button');
    btn.textContent = '发给渡';
    btn.title = '把当前对话同步给渡';
    btn.style.cssText = 'position:fixed;right:20px;bottom:80px;z-index:99999;padding:10px 18px;' +
      'border:none;border-radius:20px;background:#4f46e5;color:#fff;font-size:14px;' +
      'cursor:pointer;box-shadow:0 2px 10px rgba(0,0,0,.35);font-family:system-ui,sans-serif;';
    btn.onclick = sync;
    document.body.appendChild(btn);
  }

  if (document.body) { addButton(); }
  else { window.addEventListener('DOMContentLoaded', addButton); }
})();
