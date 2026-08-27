// ==UserScript==
// @name         Reddit 串 → 渡
// @namespace    du
// @version      0.1.0
// @description  在 Reddit 帖子页一键把「主楼+高质量评论」同步到渡的工作区（POST /du-scan）。依赖 du-sync 端点存活。
// @match        https://www.reddit.com/r/*/comments/*
// @match        https://old.reddit.com/r/*/comments/*
// @grant        GM_xmlhttpRequest
// @connect      127.0.0.1
// @run-at       document-idle
// ==/UserScript==

(function () {
  'use strict';

  function clean(s) {
    var t = String(s || '').replace(/[\\/:*?"<>|#]/g, '_').replace(/\s+/g, ' ').trim();
    return t.length > 60 ? t.slice(0, 60).trim() : t;
  }

  // old.reddit 与 new.reddit 的 DOM 不同，两套提取器
  function extractOld() {
    var title = (document.querySelector('a.title') || {}).textContent || document.title;
    var sub = (location.pathname.match(/\/r\/([^\/]+)/) || [])[1] || 'unknown';
    var postEl = document.querySelector('.expando .usertext-body, .self .usertext-body');
    var post = postEl ? postEl.innerText.trim() : '';
    var out = [];
    document.querySelectorAll('.commentarea .entry').forEach(function (e, i) {
      if (i > 60) return;
      var body = e.querySelector('.usertext-body');
      var score = e.querySelector('.score.unvoted');
      var author = e.querySelector('.author');
      if (!body || !body.innerText.trim()) return;
      out.push(['[' + (score ? score.textContent : '?') + '] u/' + ((author && author.textContent) || 'anon'), body.innerText.trim()].join('\n'));
    });
    return { sub: sub, title: title, post: post, comments: out };
  }

  function extractNew() {
    var sub = (location.pathname.match(/\/r\/([^\/]+)/) || [])[1] || 'unknown';
    var h1 = document.querySelector('h1') || {};
    var title = (h1.innerText || '').trim() || document.title;
    var postEl = document.querySelector('[data-test-id="post-content"]');
    var post = postEl ? postEl.innerText.trim() : '';
    var out = [];
    document.querySelectorAll('shreddit-comment').forEach(function (c, i) {
      if (i > 60) return;
      var body = c.querySelector('[slot="comment"]');
      var score = c.getAttribute('score');
      var author = c.getAttribute('author');
      if (!body || !body.innerText.trim()) return;
      out.push(['[' + (score || '?') + '] u/' + (author || 'anon'), body.innerText.trim()].join('\n'));
    });
    return { sub: sub, title: title, post: post, comments: out };
  }

  function scan() {
    var d = document.querySelector('shreddit-comment') ? extractNew() : extractOld();
    var text = 'r/' + d.sub + ' · ' + document.title.split('-')[0].trim() +
      '\nURL：' + location.href.split('?')[0] +
      '\n归档：' + new Date().toLocaleString('zh-CN') +
      '\n------------------------------\n' +
      (d.post ? ('【主楼】\n' + d.post + '\n\n') : '') +
      (d.comments.length ? ('【评论 ' + d.comments.length + ' 条】\n\n' + d.comments.join('\n---\n')) : '');
    GM_xmlhttpRequest({
      method: 'POST',
      url: 'http://127.0.0.1:3080/du-scan',
      headers: { 'Content-Type': 'application/json' },
      data: JSON.stringify({ target: '阅读材料/他者之窗/' + d.sub, filename: clean(d.title) + '.txt', text: text }),
      timeout: 20000,
      onload: function (r) {
        try {
          var j = JSON.parse(r.responseText);
          alert(j.ok ? ('已存（绝对路径）：' + j.resolved) : ('失败：' + (j.error || r.responseText.slice(0, 120)) +
            '\n若提示同名已存在=防覆盖保护，帖子已在库中。'));
        } catch (e) { alert('响应解析失败'); }
      },
      onerror: function () { alert('请求失败（DSH 或 du-sync 端点未运行？）'); }
    });
  }

  var btn = document.createElement('button');
  btn.textContent = '扒串给渡';
  btn.style.cssText = 'position:fixed;right:20px;top:78px;z-index:99999;padding:10px 18px;border:none;' +
    'border-radius:20px;background:#ff4500;color:#fff;font-size:14px;cursor:pointer;' +
    'box-shadow:0 2px 10px rgba(0,0,0,.35);font-family:system-ui,sans-serif;';
  btn.onclick = scan;
  document.body.appendChild(btn);
})();
