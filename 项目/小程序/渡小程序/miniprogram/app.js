/**
 * 渡 · 微信小程序
 * 入口文件 — 云环境初始化
 */
App({
  onLaunch() {
    if (!wx.cloud) {
      console.error('请使用 2.2.3 或以上的基础库以使用云能力');
      return;
    }
    wx.cloud.init({
      env: 'prod-xxxxxxxx',  // ← 替换为你的云环境 ID
      traceUser: true,
    });
  },

  globalData: {
    nickname: null,
    sessionId: null,
  },
});
