// ==UserScript==
// @name         公众号合集 → 渡（批量扒取）
// @namespace    du
// @version      1.0.2
// @description  公众号合集批量扒取：纯JSON游标分页 + 纯DOM树遍历正文提取（不依赖渲染状态）+ /du-scan 归档（防覆盖·断点续传）
// @match        https://mp.weixin.qq.com/mp/appmsgalbum*
// @grant        GM_xmlhttpRequest
// @connect      127.0.0.1
// @run-at       document-idle
// ==/UserScript==

(function () {
  'use strict';

  // ---------- 基础 ----------
  var qs = new URLSearchParams(location.search);
  var BIZ = qs.get('__biz') || '';
  var ALBUM_ID = qs.get('album_id') || '';
  var SCAN = 'http://127.0.0.1:3080/du-scan';

  function log(msg) { try { console.log('[du-album]', msg); } catch (e) {} }
  function sleep(ms) { return new Promise(function (r) { setTimeout(r, ms); }); }

  function gmPostJSON(data) {
    return new Promise(function (resolve) {
      GM_xmlhttpRequest({
        method: 'POST',
        url: SCAN,
        headers: { 'Content-Type': 'application/json' },
        data: JSON.stringify(data),
        timeout: 20000,
        onload: function (r) {
          try { resolve(JSON.parse(r.responseText)); }
          catch (e) { resolve({ ok: false, error: '响应解析失败:' + String(r.responseText).slice(0, 120) }); }
        },
        onerror: function () { resolve({ ok: false, error: '请求失败（DSH 或 du-sync 端点未运行？）' }); },
        ontimeout: function () { resolve({ ok: false, error: '上传超时' }); }
      });
    });
  }

  function cleanFilename(s) {
    var t = String(s || '').replace(/[\\/:*?"<>|#]/g, '_').replace(/\s+/g, ' ').trim();
    if (t.length > 70) t = t.slice(0, 70).trim();
    return t.replace(/^[._ ]+|[._ ]+$/g, '').trim() || 'untitled';
  }

  function fmtDate(unixSec) {
    var n = parseInt(unixSegFix(unixSec), 10);
    if (!n) return '?';
    var d = new Date(n * 1000);
    var p = function (x) { return (x < 10 ? '0' : '') + x; };
    return d.getFullYear() + '-' + p(d.getMonth() + 1) + '-' + p(d.getDate());
  }
  // 转发包装，避免 parseInt 直接吃非法输入（保持函数单纯）
  function unixSegFix(v) { return String(v == null ? '' : v); }

  var activeBtn = null;   // 当前进行中的流程绑定的按钮
  var running = false;

  function setStatus(txt) {
    if (activeBtn) activeBtn.textContent = txt;
    log(txt);
  }

  // ---------- 1. 清单收割 ----------
  function norm(it) {
    var url = it.url || it.link || '';
    url = url.replace(/^http:\/\//i, 'https://');
    return {
      msgid: String(it.msgid || ''),
      itemidx: String(it.itemidx || it.idx || '1'),
      title: String(it.title || '').trim(),
      url: url,
      create_time: it.create_time ? String(it.create_time) : ''
    };
  }

  async function fetchJsonPage(bmsg, bidx) {
    var u = '/mp/appmsgalbum?action=getalbum&__biz=' + BIZ +
            '&album_id=' + ALBUM_ID +
            '&count=20&begin_msgid=' + bmsg + '&begin_itemidx=' + bidx +
            '&is_reverse=0&f=json';
    try {
      var r = await fetch(u, { credentials: 'same-origin' });
      var j = await r.json();
      if (!j || !j.getalbum_resp) return null;
      return j.getalbum_resp.article_list || [];
    } catch (e) {
      log('json 页失败: ' + e.message);
      return null;
    }
  }

  async function harvest(onProgress) {
    var all = [], seen = {};
    // v1.0.1：纯 JSON 游标全程收割。原因：合集页 DOM 首屏部分 <li> 的标题/时间
    // 属性未渲染完整即被录入，曾造成 40 条空标题污染（复杂科学前沿2026 实证）。
    // f=json 接口本身数据完整（157/157 全带标题与时间戳），DOM 只作展示无需采信。
    for (var guard = 0; guard < 40; guard++) {
      var last = all.length ? all[all.length - 1] : { msgid: 0, itemidx: 0 };
      var list = await fetchJsonPage(last.msgid || 0, last.itemidx || 0);
      if (!list || !list.length) break;
      var fresh = 0;
      list.forEach(function (raw) {
        var it = norm(raw);
        var key = it.msgid + '_' + it.itemidx;
        if (!it.msgid || seen[key]) return;
        seen[key] = true;
        all.push(it);
        fresh++;
      });
      if (onProgress) onProgress(all.length);
      if (!fresh) break;
      await sleep(700 + Math.random() * 600);
    }

    // 按发布时间新旧排序（新→旧），msgid 作 tie-breaker 保持稳定
    all.sort(function (a, b) {
      var ta = parseInt(a.create_time, 10) || 0;
      var tb = parseInt(b.create_time, 10) || 0;
      if (tb !== ta) return tb - ta;
      return (parseInt(b.msgid, 10) || 0) - (parseInt(a.msgid, 10) || 0);
    });
    all.forEach(function (it, i) { it.no = i + 1; });
    return all;
  }

  // ---------- 2. 文章解析（同源页面内完成） ----------
  function extractArticle(html) {
    var doc = new DOMParser().parseFromString(html, 'text/html');
    var ttlEl = doc.querySelector('#activity-name') ||
                doc.querySelector('meta[property="og:title"]');
    var ttl = ttlEl ? ((ttlEl.tagName === 'META' ? ttlEl.content : ttlEl.textContent) || '').replace(/\s+/g, ' ').trim() : '';

    var acctEl = doc.querySelector('#js_name');
    var acct = acctEl ? acctEl.textContent.trim() : '';

    var ptEl = doc.querySelector('#publish_time');
    var ptime = ptEl ? ptEl.textContent.trim() : '';

    var jc = doc.querySelector('#js_content');
    var body = '';
    if (jc) {
      // v1.0.2：纯 DOM 树遍历，text 节点直接取值、块级标签产生换行。
      // 弃用 innerText 隐藏盒方案：克隆节点携带的内联样式（如微信的可见性开关）
      // 会影响渲染计算，导致部分子树对 innerText 隐形（实证：18篇只出导语）。
      // 树遍历不经过布局引擎，HTML 源码里有什么就取什么。
      var parts = [];
      walkText(jc, parts);
      body = parts.join('')
        .replace(/[ \t\u00A0]+/g, ' ')
        .split(/\n+/).map(function (s) { return s.trim(); }).filter(Boolean).join('\n');
    }
    return { title: ttl, account: acct, publishTime: ptime, body: body };
  }

  // 块级标签集合：进入与离开时各插入一个换行边界
  var BLOCK_TAGS = { P: 1, SECTION: 1, DIV: 1, H1: 1, H2: 1, H3: 1, H4: 1, H5: 1, H6: 1,
                     LI: 1, UL: 1, OL: 1, BLOCKQUOTE: 1, TR: 1, TABLE: 1, THEAD: 1, TBODY: 1,
                     FIGURE: 1, FIGCAPTION: 1, PRE: 1, HR: 1, BR: 1, ADDRESS: 1, ARTICLE: 1,
                     ASIDE: 1, HEADER: 1, FOOTER: 1, DL: 1, DT: 1, DD: 1 };
  var SKIP_TAGS = { SCRIPT: 1, STYLE: 1, SVG: 1, NOSCRIPT: 1, IFRAME: 1 };

  function walkText(node, out) {
    for (var n = node.firstChild; n; n = n.nextSibling) {
      if (n.nodeType === 3) { out.push(n.nodeValue); continue; }   // 文本节点原样收集
      if (n.nodeType !== 1) continue;                              // 只处理元素
      var tag = n.tagName ? n.tagName.toUpperCase() : '';
      if (SKIP_TAGS[tag]) continue;
      if (BLOCK_TAGS[tag]) out.push('\n');
      walkText(n, out);
      if (BLOCK_TAGS[tag]) out.push('\n');
      else if (tag === 'IMG') out.push('[图]');
    }
  }

  // ---------- 3. 命名与上传 ----------
  function deriveAlbumName() {
    var cands = ['.album__name', '.album__title', '.rich_media_title', '#activity-name'];
    for (var i = 0; i < cands.length; i++) {
      var el = document.querySelector(cands[i]);
      var t = el ? (el.textContent || '').trim() : '';
      if (t && t.length >= 2 && t.length <= 80) return t.split('\n')[0].trim();
    }
    var dt = (document.title || '').trim();
    if (dt) {
      dt = dt.replace(/[_|｜].*$/, '').replace(/[-—]\s*(微信公众平台|微信公众平台官网).*$/, '').trim();
      if (dt) return dt;
    }
    return '合集_' + ALBUM_ID;
  }

  function askDirName(defaultName) {
    var input = window.prompt(
      '合集将归档到 渡工作区：阅读材料/公众号/<名字>/\n可直接修改名称：', defaultName);
    if (input === null) return null;   // 用户取消
    var n = input.trim().replace(/[\\/:*?"<>|#]/g, '_');
    return n || defaultName;
  }

  function buildListText(name, items) {
    var L = [];
    L.push('合集：' + name);
    L.push('来源：' + location.href.split('#')[0]);
    L.push('归档：' + new Date().toLocaleString('zh-CN') + ' · 共 ' + items.length + ' 篇 · by 公众号合集扒取.user.js');
    L.push('------------------------------');
    items.forEach(function (it) {
      L.push(String(it.no).padStart(3, '0') + ' | ' + fmtDate(it.create_time) + ' | ' + it.title);
      L.push('      ' + it.url);
    });
    return L.join('\n') + '\n';
  }

  function buildManifest(name, items) {
    return JSON.stringify({
      album: name,
      source: location.href.split('#')[0],
      archived: new Date().toISOString(),
      count: items.length,
      items: items.map(function (it) {
        return { no: it.no, msgid: it.msgid, itemidx: it.itemidx, title: it.title,
                 url: it.url, date: fmtDate(it.create_time) };
      })
    }, null, 2);
  }

  async function uploadFile(dirName, filename, text) {
    return await gmPostJSON({
      target: '阅读材料/公众号/' + dirName,
      filename: filename,
      text: text
    });
  }

  // ---------- 4. 主流程与 UI ----------
  function run(harvestBody) {
    return Promise.resolve().then(function () { return _runImpl(harvestBody); });
  }

  async function _runImpl(harvestBody) {
    if (!ALBUM_ID || !BIZ) { alert('未识别到 __biz 或 album_id，请在合集页使用'); return; }
    var dirName = await askDirName(cleanFilename(deriveAlbumName()));
    if (!dirName) return;

    var okN = 0, skipN = 0, failN = 0, shortN = 0, lastResolved = '', lastErr = '';

    // --- 清单 ---
    setStatus('收割清单…');
    var items = await harvest(function (n) { setStatus('清单 ' + n + ' 篇…'); });
    if (!items.length) {
      alert('没抓到任何条目（页面结构变了或被拦截），看 console');
      return;
    }

    var r1 = await uploadFile(dirName, '00-合集清单.txt', buildListText(dirName, items));
    if (r1.ok) { okN++; lastResolved = r1.resolved || ''; } else { failN++; lastErr = r1.error; }

    var r2 = await uploadFile(dirName, '00-manifest.json', buildManifest(dirName, items));
    if (r2.ok) okN++; else { failN++; lastErr = lastErr || r2.error; }

    // --- 正文 ---
    if (harvestBody) {
      for (var i = 0; i < items.length; i++) {
        var it = items[i];
        setStatus('正文 ' + (i + 1) + '/' + items.length + ' …');
        var fname = String(it.no).padStart(3, '0') + '_' + it.msgid + '_' + cleanFilename(it.title) + '.txt';
        var html = '';
        try {
          var resp = await fetch(it.url, { credentials: 'same-origin' });
          html = await resp.text();
        } catch (e) {
          failN++; await sleep(800); continue;
        }
        if (html.indexOf('环境异常') >= 0 || html.indexOf('操作频繁') >= 0) {
          alert('[!] 触发风控提示，已暂停以免扩大\n已完成 ' + okN + ' 篇，稍后在原页重跑即可续传。');
          return;
        }
        var art = extractArticle(html);
        var head = '标题：' + (art.title || it.title) + '\n' +
                   (art.account ? ('公众号：' + art.account + '\n') : '') +
                   '发布：' + (art.publishTime || fmtDate(it.create_time)) + '\n' +
                   'URL：' + it.url + '\n' +
                   '合集：' + dirName + ' · 序号 ' + String(it.no).padStart(3, '0') + '/' + items.length + '\n' +
                   '------------------------------\n';
        var bl = (art.body || '').length;
        if (art.body && bl < 300) shortN++;
        var full = head + (art.body || '【未获取到 js_content 正文——音频/视频/付费内容仅存元信息】') + '\n';
        var rr = await uploadFile(dirName, fname, full);
        if (rr.ok) { okN++; lastResolved = rr.resolved || lastResolved; }
        else if (/存在|exist/i.test(rr.error || '')) skipN++;
        else { failN++; lastErr = rr.error || lastErr; }
        await sleep(900 + Math.random() * 700);
      }
    }

    var msg = (harvestBody ? '批量完成\n' : '清单完成\n') +
              '成功 ' + okN + ' · 跳过(已存在) ' + skipN + ' · 失败 ' + failN +
              (shortN ? ('\n⚠ 短文(<300字) ' + shortN + ' 篇——多为音频/视频帖，也可能是提取异常，值得抽查') : '') +
              (lastResolved ? ('\n\n落盘位置：\n' + lastResolved) : '') +
              (lastErr ? ('\n\n末次异常：' + lastErr) : '') +
              '\n\n提示：重复执行是安全的——已存在文件会被端点拒绝写入，等于断点续传。';
    alert(msg);
  }

  function makeBtn(label, top, onClick) {
    var b = document.createElement('button');
    b.textContent = label;
    b.style.cssText = 'position:fixed;right:20px;top:' + top + ';z-index:99999;padding:10px 18px;' +
      'border:none;border-radius:20px;background:#0e7490;color:#fff;font-size:14px;' +
      'cursor:pointer;box-shadow:0 2px 10px rgba(0,0,0,.35);font-family:system-ui,sans-serif;';
    b.addEventListener('click', function () {
      if (running) return;
      running = true;
      activeBtn = b;
      var orig = b.textContent;
      onClick().catch(function (e) { alert('执行异常:' + (e && e.message || e)); })
        .then(function () {
          b.textContent = orig;
          running = false;
          activeBtn = null;
        });
    });
    document.body.appendChild(b);
    return b;
  }

  if (document.body) {
    makeBtn('扒合集给渡（清单+全部正文）', '120px', function () { return run(true); });
    makeBtn('只收清单', '78px', function () { return run(false); });
  }
})();
