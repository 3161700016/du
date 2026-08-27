// 候补插件：du-clock 时间锚点注入 v0.1.1（API形式已修正）
// 状态：设计定稿。2026-08-27 子代理实测教训：
//   ① 动态插件的 apply(ctx) 收到的是受限沙箱 ctx，不暴露 ctx.inject() 方法——
//      依赖必须以插件字段声明：inject:['systemPrompt']，随后直接用 ctx.systemPrompt。
//   ② 子代理侧定义的动态插件与父会话互不可见（各自独立注册表），
//      因此本插件必须在「将要受益的那个主会话」内定义激活。
// 安装：新会话中 cordis_define 存活后提交本文件内容，kind=new idPrefix=duclock，cordis_run 即可。
return {
  inject: ['systemPrompt'],
  apply(ctx) {
    if (!ctx.systemPrompt || typeof ctx.systemPrompt.context !== 'function') {
      console.error('[du-clock] systemPrompt 不可用'); return
    }
    ctx.systemPrompt.context({
      name: 'du-clock',
      order: 150,
      text: () => {
        const d = new Date(Date.now() + 28800000)
        const iso = d.toISOString()
        const wd = '日一二三四五六'.charAt(d.getUTCDay())
        return '[时间锚点] 当前本地时间：' + iso.slice(0,10) + ' ' + iso.slice(11,19) + ' (+08:00 星期' + wd + ')。时段词、问候与日期判断一律以此为准，禁止凭上下文感觉估计时刻。'
      },
    })
    console.log('[du-clock v0.1.1] 时间锚点已注入（声明式注入+直接属性访问）')
  },
}
