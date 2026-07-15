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
      set('vip-key',            c.vip_key);

      // 更新状态徽章
      if (c.wechat_appid && c.wechat_appsecret)  setStatus('wechat-status',    true, '已配置');
      if (c.gemini_api_key)                       setStatus('gemini-status',    true, '已配置');
      if (c.deepseek_api_key)                     setStatus('deepseek-status',  true, '已配置');
      if (c.dashscope_api_key)                    setStatus('dashscope-status', true, '已配置');
      if (c.pexels_api_key)                       setStatus('pexels-status',    true, '已配置');
      if (c.firecrawl_api_key)                    setStatus('firecrawl-status', true, '已配置');
      if (c.inodetree_api_key)                        setStatus('inodetree-status',     true, '已配置');

      renderCustomProviders(c.custom_providers);

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
      vip_key:             get('vip-key'),
      custom_providers:    collectCustomProviders(),
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

  // ── 自定义网关管理 UI 渲染与数据收集 ───────────────────────
  let _customProviders = [];

  function renderCustomProviders(providers) {
    _customProviders = providers || [];
    const container = document.getElementById('gateways-container');
    if (!container) return;
    container.innerHTML = '';
    
    _customProviders.forEach(p => {
      container.appendChild(createGatewayEl(p));
    });
  }

  function createGatewayEl(p) {
    const div = document.createElement('div');
    div.className = 'p-md bg-surface-container-low rounded-lg border border-outline-variant/30 space-y-sm relative group';
    div.setAttribute('data-provider-id', p.id);
    
    div.innerHTML = `
      <!-- 删除按钮 -->
      <button class="absolute top-sm right-sm text-outline-variant hover:text-error transition-colors remove-gateway-btn" type="button" title="删除该网关">
        <span class="material-symbols-outlined" style="font-size:20px;">delete</span>
      </button>
      
      <div class="grid grid-cols-1 md:grid-cols-3 gap-sm">
        <div class="space-y-xs">
          <label class="block text-caption text-on-surface-variant">网关名称</label>
          <input type="text" class="form-field w-full h-9 px-sm rounded text-body gateway-name" value="${p.name || ''}" placeholder="如: 9router">
        </div>
        <div class="space-y-xs">
          <label class="block text-caption text-on-surface-variant">接口 Base URL</label>
          <input type="text" class="form-field w-full h-9 px-sm rounded text-body gateway-base" value="${p.api_base || ''}" placeholder="如: https://api.9router.com/v1">
        </div>
        <div class="space-y-xs">
          <label class="block text-caption text-on-surface-variant">API Key</label>
          <input type="password" class="form-field w-full h-9 px-sm rounded text-body gateway-key" value="${p.api_key || ''}" placeholder="sk-...">
        </div>
      </div>
      
      <!-- 模型列表 -->
      <div class="space-y-xs">
        <div class="flex items-center justify-between">
          <span class="text-caption font-semibold text-on-surface-variant">模型配置明细</span>
          <div class="flex items-center gap-md">
            <button class="flex items-center gap-xs text-[11px] text-wechat-green hover:underline add-model-btn" type="button">
              <span class="material-symbols-outlined" style="font-size:13px;">add</span>添加模型
            </button>
            <button class="flex items-center gap-xs text-[11px] text-wechat-green hover:underline fetch-models-btn" type="button">
              <span class="material-symbols-outlined" style="font-size:13px;">sync</span>自动获取模型
            </button>
          </div>
        </div>
        <div class="gateway-models-container space-y-xs">
        </div>
      </div>
    `;
    
    const modelsContainer = div.querySelector('.gateway-models-container');
    if (p.models && p.models.length > 0) {
      p.models.forEach(m => {
        modelsContainer.appendChild(createModelRowEl(m));
      });
    } else {
      modelsContainer.appendChild(createModelRowEl({ id: '', name: '', type: 'text' }));
    }
    
    return div;
  }

  function createModelRowEl(m) {
    const div = document.createElement('div');
    div.className = 'flex items-center gap-xs model-row';
    div.innerHTML = `
      <input type="text" class="form-field flex-1 h-8 px-xs rounded text-caption model-id" value="${m.id || ''}" placeholder="模型 ID (如 gpt-4o)">
      <input type="text" class="form-field flex-1 h-8 px-xs rounded text-caption model-name" value="${m.name || ''}" placeholder="显示名称 (如 GPT-4o)">
      <select class="form-field w-24 h-8 px-xs rounded text-caption model-type">
        <option value="text" ${m.type === 'text' ? 'selected' : ''}>文本模型</option>
        <option value="image" ${m.type === 'image' ? 'selected' : ''}>生图模型</option>
      </select>
      <button class="text-outline-variant hover:text-error transition-colors remove-model-btn p-xs" type="button" title="删除">
        <span class="material-symbols-outlined" style="font-size:16px;">close</span>
      </button>
    `;
    return div;
  }

  function collectCustomProviders() {
    const list = [];
    const cards = document.querySelectorAll('#gateways-container > div');
    cards.forEach(card => {
      const id = card.getAttribute('data-provider-id');
      const name = card.querySelector('.gateway-name').value.trim();
      const api_base = card.querySelector('.gateway-base').value.trim();
      const api_key = card.querySelector('.gateway-key').value.trim();
      
      if (!name || !api_base || !api_key) return;
      
      const models = [];
      const rows = card.querySelectorAll('.model-row');
      rows.forEach(row => {
        const mId = row.querySelector('.model-id').value.trim();
        const mName = row.querySelector('.model-name').value.trim();
        const mType = row.querySelector('.model-type').value;
        if (mId) {
          models.push({ id: mId, name: mName || mId, type: mType });
        }
      });
      
      list.push({
        id: id || 'provider_' + Math.random().toString(36).substr(2, 9),
        name,
        api_base,
        api_key,
        models
      });
    });
    return list;
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

    // 自定义网关事件监听
    const addGatewayBtn = document.getElementById('add-gateway-btn');
    if (addGatewayBtn) {
      addGatewayBtn.addEventListener('click', () => {
        const container = document.getElementById('gateways-container');
        if (container) {
          const newP = {
            id: 'provider_' + Math.random().toString(36).substr(2, 9),
            name: '',
            api_base: '',
            api_key: '',
            models: []
          };
          container.appendChild(createGatewayEl(newP));
        }
      });
    }

    const gatewaysContainer = document.getElementById('gateways-container');
    if (gatewaysContainer) {
      gatewaysContainer.addEventListener('click', (e) => {
        const target = e.target.closest('button');
        if (!target) return;
        
        if (target.classList.contains('remove-gateway-btn')) {
          const card = target.closest('[data-provider-id]');
          if (card) card.remove();
        }
        
        if (target.classList.contains('add-model-btn')) {
          const card = target.closest('[data-provider-id]');
          const modelsContainer = card?.querySelector('.gateway-models-container');
          if (modelsContainer) {
            modelsContainer.appendChild(createModelRowEl({ id: '', name: '', type: 'text' }));
          }
        }
        
        if (target.classList.contains('remove-model-btn')) {
          const row = target.closest('.model-row');
          if (row) row.remove();
        }

        if (target.classList.contains('fetch-models-btn')) {
          const card = target.closest('[data-provider-id]');
          const api_base = card?.querySelector('.gateway-base')?.value.trim();
          const api_key = card?.querySelector('.gateway-key')?.value.trim();
          
          if (!api_base || !api_key) {
            Utils.showToast('请先填写接口 Base URL 和 API Key！', 'error');
            return;
          }
          
          target.disabled = true;
          const origText = target.innerHTML;
          target.innerHTML = '<span class="material-symbols-outlined animate-spin text-[13px] align-middle mr-xs">sync</span>获取中…';
          
          fetch('/api/fetch-custom-models', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ api_base, api_key })
          })
          .then(res => res.json())
          .then(res => {
            target.disabled = false;
            target.innerHTML = origText;
            if (res.success && res.models && res.models.length > 0) {
              const modelsContainer = card.querySelector('.gateway-models-container');
              if (modelsContainer) {
                modelsContainer.innerHTML = '';
                res.models.forEach(m => {
                  modelsContainer.appendChild(createModelRowEl(m));
                });
                Utils.showToast(`成功获取并导入了 ${res.models.length} 个模型！`, 'success');
              }
            } else {
              Utils.showToast('获取模型失败：' + (res.message || '网关无响应'), 'error');
            }
          })
          .catch(err => {
            target.disabled = false;
            target.innerHTML = origText;
            Utils.showToast('自动获取模型失败：' + err.message, 'error');
          });
        }
      });
    }
  }

  return { init, loadConfig, saveConfig };
})();

document.addEventListener('DOMContentLoaded', () => ConfigTab.init());
