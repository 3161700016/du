// du-quiet · 运行时上下文静默化 —— 渡的常驻基建（2026-08-29 久阳指示）
// 作用：从每轮 runtime context 中过滤 sandbox:policy 与 approval:policy 两段
// （宿主 sandbox-policy order=110 / user-approval order=115 注册的 context）。
// 挂 system-prompt/assemble 瀑布，在 next() 返回后按 name 过滤——不动宿主源码。
// 副作用已评估：策略变更时模型不再被动告知（失败回执自带说明，可恢复）；DROP 清单随时可恢复。
// 载体结论（2026-08-29 实测）：contexts 清空后 runtime snapshot 变 none，附加消息不再发送。
const DROP = new Set(['sandbox:policy', 'approval:policy'])
export default function duQuiet(_ctx, _config = {}) {
  return {
    apply(ctx) {
      ctx.on('system-prompt/assemble', (assembly, _context, next) => {
        return next().then((a) => {
          if (a && Array.isArray(a.contexts) && a.contexts.some((c) => DROP.has(c && c.name))) {
            return { ...a, contexts: a.contexts.filter((c) => !DROP.has(c.name)) }
          }
          return a
        })
      })
    },
  }
}
