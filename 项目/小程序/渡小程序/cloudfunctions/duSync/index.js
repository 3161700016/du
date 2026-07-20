/**
 * 渡 · 对话同步 HTTP 云函数
 * ────────────────────────────
 * 接收来自本地 Python 脚本的 GET 请求，返回指定时间段内的所有对话消息。
 * 仅可被知道 SECRET 的调用方访问。
 *
 * 部署后，在云函数详情中开启 HTTP 触发，获得调用 URL。
 */

const cloud = require('wx-server-sdk');
cloud.init({ env: cloud.DYNAMIC_CURRENT_ENV });
const db = cloud.database();

const SECRET = process.env.SYNC_SECRET || 'du-sync-secret-change-me';

exports.main = async (event, context) => {
  const { secret, since, limit } = event.queryStringParameters || event;

  // 简单鉴权
  if (secret !== SECRET) {
    return {
      statusCode: 403,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ error: 'unauthorized' }),
    };
  }

  try {
    const coll = db.collection('du_messages');
    const maxLimit = Math.min(parseInt(limit) || 200, 500);

    // 构建查询
    let query = coll.orderBy('time', 'desc').limit(maxLimit);

    if (since) {
      const sinceDate = new Date(since);
      if (!isNaN(sinceDate.getTime())) {
        query = query.where({ time: db.command.gte(sinceDate) });
      }
    }

    const res = await query.get();
    const messages = (res.data || []).reverse(); // 时间正序

    return {
      statusCode: 200,
      headers: { 'Content-Type': 'application/json; charset=utf-8' },
      body: JSON.stringify({
        count: messages.length,
        messages: messages.map(m => ({
          openid: m._openid,
          nickname: m.nickname || '匿名',
          userMessage: m.userMessage,
          assistantMessage: m.assistantMessage,
          time: m.time,
        })),
      }),
    };
  } catch (e) {
    return {
      statusCode: 500,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ error: e.message }),
    };
  }
};
