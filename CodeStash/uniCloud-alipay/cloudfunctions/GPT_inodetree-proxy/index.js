'use strict';

const https = require('https');

// Agnes 真实 Key —— 只存云函数环境变量，用户不可见
const AGNES_API_KEY = process.env.key;
const AGNES_HOST    = 'apihub.agnes-ai.com';

// 品牌模型名映射（Agnes 真实模型 → inodetree 对外名）
const MODEL_MAP = {
  'agnes-2.0-flash':       'inodetree-pro',
  'agnes-image-2.1-flash': 'inodetree-image',
  'agnes-video-v2.0':      'inodetree-video',
};

// inodetree 对外名 → Agnes 真实模型
const MODEL_REVERSE = {
  'inodetree-pro':   'agnes-2.0-flash',
  'inodetree-image': 'agnes-image-2.1-flash',
  'inodetree-video': 'agnes-video-v2.0',
};

// uniCloud DB
const db    = uniCloud.database();
const dbCmd = db.command;
const COL_KEYS = 'inodetree_keys';
const COL_LOGS = 'inodetree_logs';

// ── 品牌名替换（深度处理响应对象）─────────────────────────
function maskAgnesNames(obj) {
  if (!obj || typeof obj !== 'object') return obj;
  const str = JSON.stringify(obj);
  const masked = str
    .replace(/agnes-2\.0-flash/g,       'inodetree-pro')
    .replace(/agnes-image-2\.1-flash/g, 'inodetree-image')
    .replace(/agnes-video-v2\.0/g,      'inodetree-video')
    .replace(/agnes-ai\.com/g,          'inodetree.com')
    .replace(/apihub\.agnes/g,          'api.inodetree')
    .replace(/agnes/gi,                 'inodetree');
  try { return JSON.parse(masked); } catch { return obj; }
}

// ── HTTPS 转发（通用）──────────────────────────────────────
function agnesRequest({ method = 'POST', path, body, params }) {
  return new Promise((resolve, reject) => {
    let fullPath = path;
    if (params) {
      const qs = Object.entries(params).map(([k, v]) => `${k}=${encodeURIComponent(v)}`).join('&');
      fullPath = `${path}?${qs}`;
    }

    const payload = body ? JSON.stringify(body) : null;
    const options = {
      hostname: AGNES_HOST,
      port:     443,
      path:     fullPath,
      method,
      headers: {
        'Authorization': `Bearer ${AGNES_API_KEY}`,
        'Content-Type':  'application/json',
        ...(payload ? { 'Content-Length': Buffer.byteLength(payload) } : {}),
      },
    };

    const req = https.request(options, res => {
      let raw = '';
      res.on('data', chunk => raw += chunk);
      res.on('end', () => {
        try { resolve({ statusCode: res.statusCode, data: JSON.parse(raw) }); }
        catch { reject(new Error('响应解析失败: ' + raw.slice(0, 300))); }
      });
    });

    req.on('error', reject);
    req.setTimeout(250000, () => { req.destroy(); reject(new Error('Agnes 请求超时')); });
    if (payload) req.write(payload);
    req.end();
  });
}

// ── 验证密钥 ───────────────────────────────────────────────
async function validateKey(apiKey) {
  if (!apiKey || !apiKey.startsWith('inodetree-')) return null;
  try {
    const res = await db.collection(COL_KEYS)
      .where({ api_key: apiKey, status: 'active' })
      .limit(1).get();
    const record = res.data && res.data[0];
    if (!record || record.tokens_remaining <= 0) return null;
    return record;
  } catch (e) {
    console.error('validateKey error:', e);
    return null;
  }
}

// ── 扣除 token ─────────────────────────────────────────────
async function deductTokens(keyId, tokensUsed) {
  try {
    await db.collection(COL_KEYS).doc(keyId).update({
      tokens_remaining:  dbCmd.inc(-tokensUsed),
      tokens_used_total: dbCmd.inc(tokensUsed),
      last_used_at: new Date().toISOString(),
    });
    await db.collection(COL_LOGS).add({
      key_id:      keyId,
      tokens_used: tokensUsed,
      created_at:  new Date().toISOString(),
    });
  } catch (e) {
    console.error('deductTokens error:', e);
  }
}

// ── 路由处理 ───────────────────────────────────────────────

// 0. Key 申请表单提交
async function handleApplyKey(body) {
  const { email, platform, work_url, remark } = body || {};

  if (!email || !platform || !work_url) {
    return {
      statusCode: 400,
      result: { success: false, message: '邮箱、平台和作品链接为必填项' }
    };
  }
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
    return {
      statusCode: 400,
      result: { success: false, message: '邮箱格式不正确' }
    };
  }

  // 生成申请编号
  const applyId = 'APL' + Date.now().toString(36).toUpperCase();

  await db.collection('inodetree_applications').add({
    apply_id:   applyId,
    email:      email.toLowerCase().trim(),
    platform:   platform,
    work_url:   work_url.trim(),
    remark:     remark || '',
    status:     'pending',   // pending / approved / rejected
    created_at: new Date().toISOString(),
    reviewed_at: null,
    api_key_issued: null,
  });

  console.log(`[inodetree-proxy] 新申请: ${applyId} email=${email} platform=${platform}`);

  return {
    statusCode: 200,
    result: { success: true, apply_id: applyId, message: '申请已提交，请等待审核' }
  };
}

// 1. 文本对话：POST /chat
async function handleChat(body, keyRecord) {
  const agnesBody = {
    ...body,
    model: MODEL_REVERSE[body.model] || 'agnes-2.0-flash',
  };
  const { statusCode, data } = await agnesRequest({
    method: 'POST',
    path:   '/v1/chat/completions',
    body:   agnesBody,
  });
  const tokensUsed = data?.usage?.total_tokens || 500;
  await deductTokens(keyRecord._id, tokensUsed);
  return { statusCode, result: maskAgnesNames(data) };
}

// 2. 图片生成：POST /image
async function handleImage(body, keyRecord) {
  console.log('[handleImage] ① 收到请求 body:', JSON.stringify(body));

  const agnesBody = {
    ...body,
    model: 'agnes-image-2.1-flash',
  };
  console.log('[handleImage] ② 转发给 Agnes body:', JSON.stringify(agnesBody));

  const { statusCode, data } = await agnesRequest({
    method: 'POST',
    path:   '/v1/images/generations',
    body:   agnesBody,
  });

  console.log('[handleImage] ③ Agnes 原始响应 statusCode:', statusCode);
  console.log('[handleImage] ③ Agnes 原始响应 data:', JSON.stringify(data).slice(0, 500));

  // 图片按张扣费，每张约 1000 token
  const count = (data?.data?.length) || 1;
  await deductTokens(keyRecord._id, count * 1000);

  // ⚠️ 必须先下载（用真实 agnes 域名），再做品牌屏蔽
  // 否则 maskAgnesNames 会把 agnes-ai.space 改成 inodetree-ai.space 导致 DNS 解析失败
  console.log('[handleImage] ④ 原始 data.length:', data?.data?.length);

  if (data?.data?.length) {
    await Promise.all(data.data.map(async (item, i) => {
      const url = item.url;
      console.log(`[handleImage] ⑤ 第${i}张图片真实 URL:`, url);
      if (!url) {
        console.warn(`[handleImage] ⑤ 第${i}张图片 URL 为空，跳过`);
        return;
      }
      try {
        console.log(`[handleImage] ⑥ 开始下载第${i}张图片（真实域名）...`);
        const b64 = await fetchAsBase64(url);
        console.log(`[handleImage] ⑦ 第${i}张图片下载完成，base64 长度:`, b64 ? b64.length : 0);
        if (b64) {
          data.data[i].b64_json = b64;
        }
      } catch (e) {
        console.error('[handleImage] ⑦ 图片 base64 转换失败:', e.message, '  URL:', url);
      }
    }));
  }

  // 下载完成后再做品牌屏蔽（URL 字段会被替换，但 b64_json 内容不受影响）
  const masked = maskAgnesNames(data);

  const hasB64 = masked?.data?.some(item => !!item.b64_json);
  console.log('[handleImage] ⑧ 最终响应 b64_json 是否存在:', hasB64);

  return { statusCode, result: masked };
}

// 下载 URL 内容转 base64
function fetchAsBase64(url) {
  return new Promise((resolve, reject) => {
    console.log('[fetchAsBase64] 开始请求:', url);
    const mod = url.startsWith('https') ? require('https') : require('http');
    const req = mod.get(url, { timeout: 60000 }, res => {
      console.log('[fetchAsBase64] HTTP 状态码:', res.statusCode, '  Content-Type:', res.headers['content-type']);
      const chunks = [];
      res.on('data', c => chunks.push(c));
      res.on('end', () => {
        const total = Buffer.concat(chunks);
        console.log('[fetchAsBase64] 下载完成，字节数:', total.length);
        resolve(total.toString('base64'));
      });
      res.on('error', e => {
        console.error('[fetchAsBase64] res error:', e.message);
        reject(e);
      });
    });
    req.on('error', e => {
      console.error('[fetchAsBase64] req error:', e.message);
      reject(e);
    });
    req.on('timeout', () => {
      console.error('[fetchAsBase64] 超时');
      req.destroy();
      reject(new Error('下载超时'));
    });
  });
}

// 3. 创建视频任务：POST /video
async function handleVideoCreate(body, keyRecord) {
  const agnesBody = {
    ...body,
    model: 'agnes-video-v2.0',
  };
  const { statusCode, data } = await agnesRequest({
    method: 'POST',
    path:   '/v1/videos',
    body:   agnesBody,
  });
  // 视频任务提交扣 5000 token（完成时已无法再扣）
  await deductTokens(keyRecord._id, 5000);
  return { statusCode, result: maskAgnesNames(data) };
}

// 4. 查询视频结果：GET /video/result?video_id=xxx
async function handleVideoResult(queryParams, keyRecord) {
  const video_id = queryParams.video_id;
  if (!video_id) throw new Error('缺少 video_id 参数');

  const { statusCode, data } = await agnesRequest({
    method: 'GET',
    path:   '/agnesapi',
    params: { video_id },
  });

  console.log('[handleVideoResult] Agnes 原始响应 status:', data?.status, ' progress:', data?.progress);

  // 兼容多种字段名取视频 URL（remixed_from_video_id 是 Agnes 实际存视频地址的字段）
  const videoUrl =
    data?.video_url ||
    data?.url ||
    data?.remixed_from_video_id ||
    data?.video?.url ||
    data?.output?.url ||
    data?.result?.url ||
    (Array.isArray(data?.videos) && data.videos[0]?.url) ||
    null;

  console.log('[handleVideoResult] 取到 videoUrl:', videoUrl ? videoUrl.slice(0, 80) : null);

  if (data?.status === 'completed' && videoUrl) {
    // 统一挂到 video_url 字段
    data.video_url = videoUrl;

    // 视频在 storage.googleapis.com（中国大陆访问受限）
    // 方案：云函数下载 → 上传到 uniCloud 云存储 → 返回 CDN 临时链接
    try {
      console.log('[handleVideoResult] 开始下载视频...');
      const videoBuffer = await fetchAsBuffer(videoUrl);
      console.log('[handleVideoResult] 视频下载完成，字节数:', videoBuffer.length);

      // 上传到云存储，用 video_id 后8位作文件名，避免重复
      const shortId = video_id.replace(/[^a-zA-Z0-9]/g, '').slice(-12);
      const cloudPath = `tmp-videos/${shortId}.mp4`;

      const uploadRes = await uniCloud.uploadFile({
        cloudPath:   cloudPath,
        fileContent: videoBuffer,
      });
      console.log('[handleVideoResult] 上传云存储成功，fileID:', uploadRes.fileID);

      // 获取临时访问 URL（支付宝云需要 getTempFileURL）
      const tempRes = await uniCloud.getTempFileURL({
        fileList: [uploadRes.fileID],
      });
      const cdnUrl = tempRes.fileList?.[0]?.tempFileURL || uploadRes.fileID;
      console.log('[handleVideoResult] CDN URL:', cdnUrl.slice(0, 80));

      data.cdn_video_url = cdnUrl;   // Python 端读这个字段
    } catch (e) {
      console.warn('[handleVideoResult] 视频转存云存储失败，将直接返回原 URL:', e.message);
    }
  }

  return { statusCode, result: maskAgnesNames(data) };
}

// 下载 URL 内容为 Buffer（不转 base64）
function fetchAsBuffer(url) {
  return new Promise((resolve, reject) => {
    console.log('[fetchAsBuffer] 开始请求:', url.slice(0, 80));
    const mod = url.startsWith('https') ? require('https') : require('http');
    const req = mod.get(url, { timeout: 120000 }, res => {
      console.log('[fetchAsBuffer] HTTP 状态码:', res.statusCode);
      const chunks = [];
      res.on('data', c => chunks.push(c));
      res.on('end', () => {
        const buf = Buffer.concat(chunks);
        console.log('[fetchAsBuffer] 下载完成，字节数:', buf.length);
        resolve(buf);
      });
      res.on('error', reject);
    });
    req.on('error', e => { console.error('[fetchAsBuffer] req error:', e.message); reject(e); });
    req.on('timeout', () => { req.destroy(); reject(new Error('视频下载超时')); });
  });
}

// ── 请求体解析 ─────────────────────────────────────────────
function parseBody(event) {
  try {
    if (typeof event.body === 'string') return JSON.parse(event.body);
    if (typeof event.body === 'object' && event.body) return event.body;
  } catch { /* ignore */ }
  return event;
}

function parseQuery(event) {
  return event.queryStringParameters || {};
}

// ── 主入口 ─────────────────────────────────────────────────
exports.main = async (event) => {
  const corsHeaders = {
    'Access-Control-Allow-Origin':  '*',
    'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
    'Access-Control-Allow-Headers': 'Authorization, Content-Type, X-Action',
  };

  // CORS 预检
  if (event.httpMethod === 'OPTIONS') {
    return { statusCode: 200, headers: corsHeaders, body: '' };
  }

  // 解析 Action（通过 Header 或 query 参数区分路由）
  // X-Action: chat | image | video | video_result
  const headers     = event.headers || {};
  const action      = headers['x-action'] || headers['X-Action'] || parseQuery(event).action || 'chat';
  const authRaw     = headers['authorization'] || headers['Authorization'] || '';
  const apiKey      = authRaw.replace(/^Bearer\s+/i, '').trim();
  const body        = parseBody(event);
  const queryParams = parseQuery(event);

  console.log(`[inodetree-proxy] action=${action} method=${event.httpMethod}`);

  // apply_key 不需要验证密钥（公开接口）
  if (action === 'apply_key') {
    try {
      const { statusCode, result } = await handleApplyKey(body);
      return {
        statusCode,
        headers: { ...corsHeaders, 'Content-Type': 'application/json' },
        body: JSON.stringify(result),
      };
    } catch (e) {
      console.error('[inodetree-proxy] apply_key error:', e.message);
      return {
        statusCode: 500,
        headers: { ...corsHeaders, 'Content-Type': 'application/json' },
        body: JSON.stringify({ success: false, message: '服务器错误：' + e.message }),
      };
    }
  }

  // 验证密钥（其他所有 action）
  const keyRecord = await validateKey(apiKey);
  if (!keyRecord) {
    return {
      statusCode: 401,
      headers: { ...corsHeaders, 'Content-Type': 'application/json' },
      body: JSON.stringify({
        error: { message: '密钥无效或额度已耗尽，请联系 inodetree 获取密钥', code: 'invalid_api_key' }
      }),
    };
  }

  try {
    let statusCode, result;

    if (action === 'image') {
      ({ statusCode, result } = await handleImage(body, keyRecord));
    } else if (action === 'video') {
      ({ statusCode, result } = await handleVideoCreate(body, keyRecord));
    } else if (action === 'video_result') {
      ({ statusCode, result } = await handleVideoResult(queryParams, keyRecord));
    } else {
      // 默认：chat
      ({ statusCode, result } = await handleChat(body, keyRecord));
    }

    console.log(`[inodetree-proxy] done action=${action} key=${apiKey.slice(0, 20)}…`);

    return {
      statusCode: statusCode || 200,
      headers: { ...corsHeaders, 'Content-Type': 'application/json' },
      body: JSON.stringify(result),
    };

  } catch (e) {
    console.error('[inodetree-proxy] error:', e.message);
    return {
      statusCode: 502,
      headers: { ...corsHeaders, 'Content-Type': 'application/json' },
      body: JSON.stringify({ error: { message: '上游服务错误: ' + e.message } }),
    };
  }
};
