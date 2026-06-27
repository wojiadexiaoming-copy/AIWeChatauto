/**
 * tab_config.js — 系统配置管理 Tab
 * 负责：加载配置、保存配置、各服务测试连接、模型列表刷新
 */

const ConfigTab = (() => {

  // ── 工具 ──────────────────────────────────────────────────
  function setStatus(id, ok, msg) {
    const el = document.getElementById(id);
    if (!el) return;
    el.textContent = msg || (ok ? '已连接' : '连接失败');
    el.className = ok
      ? 'text-caption px-sm py-xs rounded-full bg-wechat-green/10 text-wechat-green font-semibold'
      : 'text-caption px-sm py-xs rounded-full bg-red-100 text-red-600 font-semibold';
  }

  function btnLoading(btn, text = '测试中…') {
    btn._orig = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = `<span class="material-symbols-outlined animate-spin align-middle" style="font-size:14px;">sync</span> ${text}`;
  }

  function btnRestore(btn) {
    btn.disabled = false;
    btn.innerHTML = btn._orig;
  }

  // ── 加载配置 ──────────────────────────────────────────────
  async function loadConfig() {
    try {
      const res = await fetch('/api/config');
      const data = await res.json();
      if (!data.success) return;
      const c = data.data;

      const set = (id, val) => { const el = document.getElementById(id); if (el) el.value = val || ''; };

      set('wechat-appid',       c.wechat_appid);
      set('wechat-appsecret',   c.wechat_appsecret);
      set('gemini-api-key',     c.gemini_api_key);
      set('gemini-model',       c.gemini_model || 'gemini-2.5-flash');
      set('deepseek-api-key',   c.deepseek_api_key);
      set('deepseek-model',     c.deepseek_model || 'deepseek-chat');
      set('dashscope-api-key',  c.dashscope_api_key);
      set('dashscope-model',    c.dashscope_model || 'qwen-turbo');
      set('pexels-api-key',     c.pexels_api_key);
      set('firecrawl-api-key',  c.firecrawl_api_key);
      set('inodetree-api-key',      c.inodetree_api_key);
      set('coze_token',         c.coze_token);
      set('coze_workflow_id',   c.coze_workflow_id);
      set('author-name',        c.author || 'AI笔记');
      set('content-source-url', c.content_source_url);

      // 更新状态徽章
      if (c.wechat_appid && c.wechat_appsecret)  setStatus('wechat-status',    true, '已配置');
      if (c.gemini_api_key)                       setStatus('gemini-status',    true, '已配置');
      if (c.deepseek_api_key)                     setStatus('deepseek-status',  true, '已配置');
      if (c.dashscope_api_key)                    setStatus('dashscope-status', true, '已配置');
      if (c.pexels_api_key)                       setStatus('pexels-status',    true, '已配置');
      if (c.firecrawl_api_key)                    setStatus('firecrawl-status', true, '已配置');
      if (c.inodetree_api_key)                        setStatus('inodetree-status',     true, '已配置');

    } catch (e) {
      Utils.showToast('加载配置失败：' + e.message, 'error');
    }
  }

  // ── 保存配置 ──────────────────────────────────────────────
  async function saveConfig() {
    const get = id => document.getElementById(id)?.value || '';
    const payload = {
      wechat_appid:        get('wechat-appid'),
      wechat_appsecret:    get('wechat-appsecret'),
      gemini_api_key:      get('gemini-api-key'),
      gemini_model:        get('gemini-model'),
      deepseek_api_key:    get('deepseek-api-key'),
      deepseek_model:      get('deepseek-model'),
      dashscope_api_key:   get('dashscope-api-key'),
      dashscope_model:     get('dashscope-model'),
      pexels_api_key:      get('pexels-api-key'),
      firecrawl_api_key:   get('firecrawl-api-key'),
      inodetree_api_key:       get('inodetree-api-key'),
      coze_token:          get('coze_token'),
      coze_workflow_id:    get('coze_workflow_id'),
      author:              get('author-name'),
      content_source_url:  get('content-source-url'),
    };
    try {
      const res  = await fetch('/api/config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      const data = await res.json();
      if (data.success) {
        Utils.showToast('配置保存成功', 'success');
        await loadConfig();
      } else {
        Utils.showToast('保存失败：' + data.message, 'error');
      }
    } catch (e) {
      Utils.showToast('保存配置异常：' + e.message, 'error');
    }
  }

  // ── 测试按钮通用封装 ──────────────────────────────────────
  async function testBtn(btnId, statusId, apiPath) {
    const btn = document.getElementById(btnId);
    if (!btn) return;
    btnLoading(btn);
    try {
      const res  = await fetch(apiPath, { method: 'POST' });
      const data = await res.json();
      setStatus(statusId, data.success, data.success ? '连接正常' : '连接失败');
      Utils.showToast(data.success ? '连接成功' : ('连接失败：' + data.message),
                      data.success ? 'success' : 'error');
    } catch (e) {
      setStatus(statusId, false, '请求失败');
      Utils.showToast('请求失败：' + e.message, 'error');
    } finally {
      btnRestore(btn);
    }
  }

  // ── 刷新模型列表 ──────────────────────────────────────────
  async function loadModels(btnId, selectId, apiPath) {
    const btn = document.getElementById(btnId);
    if (btn) btnLoading(btn, '刷新中…');
    try {
      const res  = await fetch(apiPath);
      const data = await res.json();
      const sel  = document.getElementById(selectId);
      if (data.success && sel && data.models?.length) {
        sel.innerHTML = '';
        data.models.forEach(m => {
          const opt = document.createElement('option');
          opt.value = typeof m === 'string' ? m : m.id;
          opt.textContent = typeof m === 'string' ? m : (m.name || m.id);
          sel.appendChild(opt);
        });
        Utils.showToast('模型列表已更新', 'success');
      }
    } catch (e) {
      Utils.showToast('刷新失败：' + e.message, 'error');
    } finally {
      if (btn) btnRestore(btn);
    }
  }

  // ── 公网 IP ───────────────────────────────────────────────
  function loadUserIP() {
    function isLocal(ip) {
      return ip === '127.0.0.1' || ip === '::1' ||
             ip.startsWith('192.168.') || ip.startsWith('10.') || ip.startsWith('172.');
    }
    fetch('/api/get_ip').then(r => r.json()).then(d => {
      const ip = d.ip || '获取失败';
      const set = v => {
        ['user-ip', 'user-ip-topup'].forEach(id => {
          const el = document.getElementById(id);
          if (el) el.textContent = v;
        });
      };
      if (isLocal(ip)) {
        fetch('https://api4.ipify.org?format=json').then(r => r.json())
          .then(d2 => set(d2.ip || ip)).catch(() => set(ip));
      } else {
        set(ip);
      }
    }).catch(() => {
      ['user-ip', 'user-ip-topup'].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.textContent = '获取失败';
      });
    });
  }


  // ── 初始化 ───────────────────────────────────────────────
  function init() {
    loadConfig();
    loadUserIP();

    document.getElementById('save-config')
      ?.addEventListener('click', saveConfig);

    // 测试连接按钮
    document.getElementById('test-wechat')
      ?.addEventListener('click', () => testBtn('test-wechat',    'wechat-status',    '/api/test-wechat'));
    document.getElementById('test-gemini')
      ?.addEventListener('click', () => testBtn('test-gemini',    'gemini-status',    '/api/test-gemini'));
    document.getElementById('test-deepseek')
      ?.addEventListener('click', () => testBtn('test-deepseek',  'deepseek-status',  '/api/test-deepseek'));
    document.getElementById('test-dashscope')
      ?.addEventListener('click', () => testBtn('test-dashscope', 'dashscope-status', '/api/test-dashscope'));
    document.getElementById('test-pexels')
      ?.addEventListener('click', () => testBtn('test-pexels',    'pexels-status',    '/api/test-pexels'));
    document.getElementById('test-firecrawl')
      ?.addEventListener('click', () => testBtn('test-firecrawl', 'firecrawl-status', '/api/test-firecrawl'));
    document.getElementById('test-inodetree')
      ?.addEventListener('click', () => testBtn('test-inodetree',     'inodetree-status',     '/api/test-inodetree'));

    // 刷新模型按钮
    document.getElementById('load-gemini-models')
      ?.addEventListener('click', () => loadModels('load-gemini-models',   'gemini-model',   '/api/gemini-models'));
    document.getElementById('load-deepseek-models')
      ?.addEventListener('click', () => loadModels('load-deepseek-models', 'deepseek-model', '/api/deepseek-models'));
    document.getElementById('load-dashscope-models')
      ?.addEventListener('click', () => loadModels('load-dashscope-models','dashscope-model','/api/dashscope-models'));
  }

  return { init, loadConfig, saveConfig };
})();

document.addEventListener('DOMContentLoaded', () => ConfigTab.init());
