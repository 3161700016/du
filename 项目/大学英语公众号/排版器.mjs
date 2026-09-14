// 排版生成器 v0 · 渡 · 2026-09-14
// 输入：本文件底部 ARTICLES 的内容规格；输出：成品/<名>.html（微信安全子集）+ 排版说明.txt
// 设计约束（来自 09-14 实测）：
//  · 微信只保留 section/p/span/img/strong/em/br + 内联样式；class/id/<style>/position/transform 全丢
//  · 不用 background-clip:text 的"渐变字/透明字"（秀米模板里 color:transparent 的写法在微信里有整段消失的风险）
//  · 配色取自久阳三张空模板：主色橙 rgb(255,129,0)、米白底 rgb(255,246,237)、
//    深棕辅助 rgb(149,117,89)、正文灰 rgb(62,62,62)、白卡 rgb(255,255,255)
//  · 装饰位只用纯样式（线/圆点/色块）实现，不盲放贴纸；可选贴纸位以 <!-- du-deco:... --> 标记
// 用法：node 排版器.mjs [文章键]

import fs from 'node:fs'

const C = {
  main: 'rgb(255,129,0)', soft: 'rgb(254,195,135)', cream: 'rgb(255,246,237)', cream2: 'rgb(255,251,247)',
  brown: 'rgb(149,117,89)', ink: 'rgb(62,62,62)', white: 'rgb(255,255,255)', gray: 'rgb(138,133,120)',
}

const p = (t, s) => '<p style="margin: 0px 0px 12px; font-size: 15px; line-height: 2; letter-spacing: 0.5px; color: ' + C.ink + '; text-align: justify;' + (s || '') + '">' + t + '</p>'
const small = (t, s) => '<p style="margin: 0px 0px 8px; font-size: 13px; line-height: 1.9; letter-spacing: 0.5px; color: ' + C.brown + '; text-align: justify;' + (s || '') + '">' + t + '</p>'
const rule = (w, color) => '<section style="width: ' + w + '; height: 1px; background-color: ' + color + '; margin: 14px auto; box-sizing: border-box;"></section>'
const dot = (c) => '<section style="display: inline-block; width: 6px; height: 6px; border-radius: 6px; background-color: ' + c + '; margin: 0px 4px;"></section>'
const dots = () => '<section style="text-align: center; margin: 18px 0px;">' + dot(C.soft) + dot(C.main) + dot(C.soft) + '</section>'
const card = (inner) => '<section style="background-color: ' + C.white + '; border-radius: 12px; padding: 16px 18px; margin: 12px 0px; box-sizing: border-box;">' + inner + '</section>'
const deco = (note) => '<!-- du-deco: ' + note + ' -->'
const part = (no, title, sub) => '<section style="margin: 26px 0px 12px; text-align: center;">'
  + '<section style="display: inline-block; border-bottom: 2px solid ' + C.main + '; padding: 0px 10px 4px;">'
  + '<p style="margin: 0px; font-size: 12px; letter-spacing: 3px; color: ' + C.main + ';">' + no + '</p></section>'
  + '<p style="margin: 10px 0px 0px; font-size: 20px; font-weight: bold; letter-spacing: 1px; color: ' + C.ink + ';">' + title + '</p>'
  + (sub ? '<p style="margin: 6px 0px 0px; font-size: 12px; letter-spacing: 2px; color: ' + C.gray + ';">' + sub + '</p>' : '')
  + '</section>'

// 内容图位：占位块（他按关键词搜图后替换整块）
const slot = (id, ratio, predict, keys) => '<!-- du-slot: ' + id + ' | ' + ratio + ' -->'
  + '<section style="margin: 14px 0px; padding: 22px 16px; border: 1px dashed ' + C.soft + '; border-radius: 10px; background-color: ' + C.cream2 + '; text-align: center; box-sizing: border-box;">'
  + '<p style="margin: 0px 0px 8px; font-size: 13px; letter-spacing: 1px; color: ' + C.main + ';">【内容图位 ' + id + '｜' + ratio + '｜把图放在这里】</p>'
  + '<p style="margin: 0px 0px 6px; font-size: 13px; line-height: 1.9; color: ' + C.gray + ';">预判画面：' + predict + '</p>'
  + '<p style="margin: 0px; font-size: 13px; line-height: 1.9; color: ' + C.brown + ';">搜图关键词：' + keys + '</p>'
  + '</section>'

const pair = (en, zh) => '<section style="margin: 0px 0px 10px;">'
  + '<p style="margin: 0px; font-size: 15px; line-height: 1.8; letter-spacing: 0.3px; color: ' + C.ink + ';">' + en + '</p>'
  + '<p style="margin: 0px; font-size: 14px; line-height: 1.8; letter-spacing: 0.3px; color: ' + C.brown + ';">' + zh + '</p>'
  + '</section>'
const lyr = (arr) => '<section style="border-left: 3px solid ' + C.soft + '; padding-left: 14px; margin: 12px 0px;">' + arr.map((x) => pair(x[0], x[1])).join('') + '</section>'
const big = (en, zh) => '<section style="margin: 18px 0px; text-align: center;">'
  + '<p style="margin: 0px; font-size: 30px; font-weight: bold; letter-spacing: 8px; color: ' + C.main + ';">' + en + '</p>'
  + '<p style="margin: 8px 0px 0px; font-size: 12px; letter-spacing: 2px; color: ' + C.gray + ';">' + zh + '</p>'
  + '</section>'

const A = {
  yellow: {
    file: '2026-09-14-yellow-v0',
    kicker: 'USTB ENGLISH · 你点我播',
    title: 'YELLOW',
    subtitle: '酷玩乐队 Coldplay',
    lede: '2000 年的威尔士，一个静谧的录音室夜晚。刚录完《Shiver》的四个人走到室外，抬头看见了整片星空。',
    parts: [
      {
        no: 'PART 01', title: 'Look at the stars', sub: '一首十分钟写成的歌',
        body: [
          deco('标题区右侧可选贴纸位（模板自带，如星/音符）'),
          p('制作人 Ken Nelson 指着夜空说：“Look at the stars.” 主唱克里斯·马丁抱着吉他抬头凝望，旋律就从指尖流了出来。'),
          p('十分钟不到，这首歌完成了。他本是在模仿尼尔·扬（Neil Young）的嗓音逗大家笑，却意外哼出了世纪金曲。'),
          p('“Yellow”这个词，是他看见录音室里那本电话黄页，顺口唱出来的。后来他说，这个 yellow 本身没有固定意义——是听众给它注满了温暖与爱。'),
          slot('①', '16:9（1080×608）', '夜晚的录音室或郊外夜空：深蓝到黑的渐变天幕、稀疏星点、地平线或树影剪影；整体暗、安静、留白多', 'starry night sky long exposure / Wales countryside night / 星空 夜景 剪影 / dark minimal night sky'),
          slot('②', '4:3（1080×810）', '乐队感（不要求人脸清晰）：吉他手抱琴的局部、录音台与推子、暖光下的乐器剪影——避开有明显水印的新闻图', 'Coldplay 2000 studio session / acoustic guitar warm light / recording studio mixing desk / 录音室 吉他 暖光'),
        ],
      },
      {
        no: 'PART 02', title: '为你而亮的光', sub: 'YELLOW 是什么颜色',
        body: [
          p('歌里讲的是一种默默的、愿意付出的爱：星星为你而亮，我为你写歌，为你穿越海洋，为你画下轮廓，甚至“为你流尽最后一滴血”。'),
          p('Yellow 不是明艳的橙色，也不是冷静的蓝色，它是温和、包容、带着一点点害羞的颜色——像初秋的阳光，不灼人，却刚好暖到心里。'),
          slot('③', '3:2（1080×720）', '暖黄的抽象光感：阳光穿过树叶的光斑、金色逆光剪影、暖色墙面光痕；不看人脸也要“暖”', 'golden hour light through leaves / warm yellow light texture / 初秋 暖阳 光斑 / soft golden bokeh'),
          big('YELLOW', 'A LOVE THAT ASKS FOR NOTHING'),
        ],
      },
      {
        no: 'PART 03', title: '中英文歌词', sub: 'LYRICS',
        body: [
          deco('歌词区左上角可选贴纸位（模板自带，如小星/引号）'),
          lyr([
            ['Look at the stars,', '抬头仰望繁星点点'],
            ['Look how they shine for you,', '看它们为你绽放光芒'],
            ['And everything you do,', '而你所做的每一件事'],
            ['Yeah, they were all Yellow.', '都温暖如金。'],
            ['I came along,', '我一路追随'],
            ['I wrote a song for you,', '为你写下这首歌'],
            ['And all the things you do,', '还有你所有的举止'],
            ['And it was called Yellow.', '名字就叫 Yellow。'],
            ['So then I took my turn,', '我也鼓起勇气'],
            ['Oh what a thing to have done,', '虽然有些冒昧'],
            ['And it was all Yellow.', '却充满暖意。'],
          ]),
          dots(),
          lyr([
            ['Your skin', '你的肌肤'],
            ['Oh yeah, your skin and bones,', '你的筋骨皮囊'],
            ['Turn into something beautiful,', '都化作美好'],
            ['You know, you know I love you so,', '你知道，你知道我深爱你'],
            ['You know I love you so.', '你知道我有多爱你。'],
            ['I swam across,', '我游越沧海'],
            ['I jumped across for you,', '为你纵身一跃'],
            ['Oh what a thing to do.', '哪怕只是傻事'],
            ['’Cause you were all yellow,', '因为你全身闪耀'],
            ['I drew a line,', '我画下一笔'],
            ['I drew a line for you,', '为你描绘轮廓'],
            ['Oh what a thing to do,', '哪怕徒劳'],
            ['And it was all yellow.', '也染成金黄。'],
          ]),
          slot('④', '3:4 竖（810×1080）', '竖构图暖调收束：逆光的麦穗/芦苇、暖黄灯串、夜空下的剪影；纵向延伸感强，压得住长歌词区', 'backlit wheat golden field / warm string lights night / 逆光 麦穗 暖黄 / vertical golden silhouette'),
          dots(),
          lyr([
            ['Your skin', '你的肌肤'],
            ['Oh yeah, your skin and bones,', '你的筋骨皮囊'],
            ['Turn into something beautiful,', '都化作美好'],
            ['And you know,', '你知道'],
            ['For you I’d bleed myself dry,', '我愿为你流尽最后一滴血'],
            ['For you I’d bleed myself dry.', '我愿为你倾尽所有。'],
            ['It’s true,', '都是真的'],
            ['Look how they shine for you,', '看星星为你闪耀'],
            ['Look how they shine for you,', '看它们多为你闪耀'],
            ['Look how they shine for,', '看那光芒'],
            ['Look how they shine for you,', '为你而绽放'],
            ['Look how they shine for you,', '为你而璀璨'],
            ['Look how they shine.', '如此耀眼。'],
            ['Look at the stars,', '抬头仰望繁星点点'],
            ['Look how they shine for you,', '看它们为你绽放光芒'],
            ['And all the things that you do.', '还有你所有的美好。'],
          ]),
        ],
      },
    ],
    outro: [
      p('Yellow 不是一首轰轰烈烈的爱之歌，它更像一次温柔的告白：你不必完美，我愿为你做那些看似“傻气”的小事——写歌、渡海、画线，甚至付出自己全部。'),
      p('如果你也有想推荐的英文歌，欢迎来稿分享你的故事与感受。我们下期「你点我播」见。', ' color: ' + C.main + ';'),
    ],
    credits: [
      '排版丨渡（秀米空模板改制，2026-09-14）',
      '文字丨【发布前填写】',
      '图片丨【按四个内容图位的关键词替换】',
      '封面丨由秀米生成长图的截图改制',
      '贴纸丨【发布前填写，或删除装饰位】',
    ],
  },
}

function build(key) {
  const a = A[key]
  const o = []
  o.push('<section style="background-color: ' + C.cream + '; padding: 20px 16px 26px; box-sizing: border-box;">')
  o.push('<section style="text-align: center; padding: 4px 0px 0px;">')
  o.push('<p style="margin: 0px 0px 10px; font-size: 12px; letter-spacing: 3px; color: ' + C.brown + ';">' + a.kicker + '</p>')
  o.push('<p style="margin: 0px; font-size: 40px; font-weight: bold; letter-spacing: 8px; color: ' + C.main + ';">' + a.title + '</p>')
  o.push('<p style="margin: 10px 0px 0px; font-size: 15px; letter-spacing: 3px; color: ' + C.ink + ';">' + a.subtitle + '</p>')
  o.push(rule('38%', C.soft))
  o.push(small(a.lede, ' text-align: center;'))
  o.push('</section>')
  for (const pt of a.parts) {
    o.push(part(pt.no, pt.title, pt.sub))
    o.push(card(pt.body.join('')))
  }
  o.push(part('END', '写在最后', 'AFTERWORD'))
  o.push(card(a.outro.join('')))
  o.push(dots())
  o.push(rule('30%', C.soft))
  o.push(deco('文末可选贴纸位（模板自带）'))
  o.push('<section style="text-align: center;">')
  for (const c of a.credits) o.push('<p style="margin: 0px 0px 4px; font-size: 12px; line-height: 1.9; color: ' + C.gray + ';">' + c + '</p>')
  o.push('</section>')
  o.push('</section>')
  return o.join('\n')
}

const key = process.argv[2] || 'yellow'
const a = A[key]
if (!a) { console.log('未知文章键：' + key); process.exit(1) }
fs.mkdirSync('成品', { recursive: true })
const out = '成品/' + a.file + '.html'
const html = build(key)
fs.writeFileSync(out, html, 'utf8')
const slots = (html.match(/du-slot:/g) || []).length
const decos = (html.match(/du-deco:/g) || []).length
console.log('生成：' + out + '（' + html.length + ' 字符；内容图位 ' + slots + ' 个；装饰位标记 ' + decos + ' 处）')
