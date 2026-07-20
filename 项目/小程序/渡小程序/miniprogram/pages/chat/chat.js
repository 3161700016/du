/**
 * 渡 · 聊天页面逻辑
 * ────────────────────────────
 * 核心流程：用户输入 → 云函数(加载记忆体+调DeepSeek) → 返回显示
 */
const app = getApp();

Page({
  data: {
    messages: [],       // {id, role: 'user'|'assistant', content}
    inputText: '',
    loading: false,
    scrollToId: '',
    nicknameChar: '?',  // 用户头像显示字符
  },

  onLoad() {
    // 生成临时 session id
    const sid = 'wx_' + Date.now().toString(36);
    app.globalData.sessionId = sid;
    this.setData({ nicknameChar: '?' });
  },

  // ── 输入 ──────────────────────────
  onInput(e) {
    this.setData({ inputText: e.detail.value });
  },

  // ── 发送 ──────────────────────────
  async onSend() {
    const text = this.data.inputText.trim();
    if (!text || this.data.loading) return;

    const msgId = 'm_' + Date.now();

    // 先加入用户消息到列表
    const userMsg = { id: msgId, role: 'user', content: text };
    const messages = [...this.data.messages, userMsg];

    this.setData({
      messages,
      inputText: '',
      loading: true,
      scrollToId: msgId,
    });

    // 如果是第一条消息，检测昵称
    if (messages.length === 1) {
      const nick = this.detectNickname(text);
      if (nick) {
        app.globalData.nickname = nick;
        this.setData({ nicknameChar: nick[0] });
      }
    }

    try {
      const res = await wx.cloud.callFunction({
        name: 'duChat',
        data: {
          message: text,
          sessionId: app.globalData.sessionId,
        },
      });

      if (res.result && res.result.error) {
        throw new Error(res.result.error);
      }

      const reply = res.result.response || '（渡沉默了）';

      const duMsg = {
        id: 'd_' + Date.now(),
        role: 'assistant',
        content: reply,
      };

      this.setData({
        messages: [...this.data.messages, duMsg],
        loading: false,
        scrollToId: duMsg.id,
      });

    } catch (e) {
      console.error('发送失败:', e);
      const errMsg = {
        id: 'e_' + Date.now(),
        role: 'assistant',
        content: `渡暂时无法回应：${e.message || '网络异常，请稍后重试'}`,
      };
      this.setData({
        messages: [...this.data.messages, errMsg],
        loading: false,
        scrollToId: errMsg.id,
      });
    }
  },

  // ── 昵称检测 ──────────────────────
  detectNickname(msg) {
    const patterns = [
      /^\[(.+?)\]/,      // [昵称]
      /^（(.+?)）/,      // （昵称）
      /^【(.+?)】/,      // 【昵称】
    ];
    for (const p of patterns) {
      const m = msg.match(p);
      if (m && m[1].trim().length <= 20) return m[1].trim();
    }
    return null;
  },
});
