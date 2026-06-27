/**
 * tab_create.js — 文章创作与预览 Tab
 * 负责：生成文章、保存草稿、发布文章、历史记录、视频/图片模型参数联动
 */

const CreateTab = (() => {
  'use strict';

  let _currentArticle = null;  // 当前生成的文章数据

  // ── 工具 ──────────────────────────────────────────────────
  const get  = id  => document.getElementById(id);
  const val  = id  => get(id)?.value?.trim() || '';
  const chk  = id  => get(id)?.checked || false;

  function setProgress(pct, text) {
    const bar = get('progress-bar');
    const txt = get('progress-text');
    if (bar) bar.style.width = pct + '%';
    if (txt) txt.textContent = text || '';
  }
  function showProgress(show) {
    get('generation-progress')?.classList.toggle('hidden', !show);
  }

  // ── 标题模式切换 ──────────────────────────────────────────
  function initTitleModeToggle() {
    const btnManual = get('title-mode-manual');
    const btnAuto   = get('title-mode-auto');
    const secManual = get('title-manual-section');
    const secHot    = get('hot-options-section');

    function setMode(isHot) {
      [btnManual, btnAuto].forEach(b => { if (!b) return; });
      if (btnManual) {
        const on = !isHot;
        btnManual.classList.toggle('border-wechat-green', on);
        btnManual.classList.toggle('text-wechat-green', on);
        btnManual.classList.toggle('font-semibold', on);
        btnManual.classList.toggle('bg-wechat-green/5', on);
      }
      if (btnAuto) {
        const on = isHot;
        btnAuto.classList.toggle('border-wechat-green', on);
        btnAuto.classList.toggle('text-wechat-green', on);
        btnAuto.classList.toggle('font-semibold', on);
        btnAuto.classList.toggle('bg-wechat-green/5', on);
      }
      secManual?.classList.toggle('hidden', isHot);
      secHot?.classList.toggle('hidden', !isHot);
    }

    btnManual?.addEventListener('click', () => setMode(false));
    btnAuto  ?.addEventListener('click', () => setMode(true));
    setMode(false);
  }

  // ── 生图模型切换联动 ──────────────────────────────────────
  function initImageModelToggle() {
    const sel    = get('image-model-select');
    const extra  = get('dashscope-extra-fields');
    const prompt = get('custom-image-prompt');
    if (!sel) return;

    function update() {
      const isDash = sel.value === 'dashscope';
      extra ?.classList.toggle('hidden', !isDash);
      prompt?.classList.toggle('hidden', isDash);
    }
    sel.addEventListener('change', update);
    update();
  }

  // ── 阿里云百炼自定义下拉 ──────────────────────────────────
  function initDashscopeDropdown() {
    const btn    = get('dashscopeImageModelBtn');
    const menu   = get('dashscope-dropdown-menu');
    const hidden = get('dashscope-image-model-value');
    if (!btn || !menu) return;

    // 展开/收起
    btn.addEventListener('click', e => {
      e.stopPropagation();
      menu.classList.toggle('hidden');
    });

    // 选择项
    menu.querySelectorAll('a[data-value]').forEach(a => {
      a.addEventListener('click', e => {
        e.preventDefault();
        const v = a.dataset.value;
        if (hidden) hidden.value = v;
        // 更新按钮文字（去掉"限免"角标文字）
        const label = a.childNodes[0]?.textContent?.trim() || a.textContent.trim();
        const span  = btn.querySelector('span:first-child');
        if (span) span.textContent = label;
        menu.classList.add('hidden');
      });
    });

    // 点击外部关闭
    document.addEventListener('click', () => menu.classList.add('hidden'));
  }

  // ── 视频参数联动 ──────────────────────────────────────────
  function initVideoToggle() {
    const chkEl   = get('enable-video');
    const params  = get('video-params');
    const fpsSel  = get('video-fps');
    const hint    = get('video-duration-hint');
    const FPS_MAP = { '24': '≈ 15s', '30': '≈ 10s', '60': '≈ 5s' };

    function updateHint() {
      if (hint && fpsSel) hint.textContent = FPS_MAP[fpsSel.value] || '≈ 15s';
    }

    if (chkEl && params) {
      chkEl.addEventListener('change', () => {
        params.classList.toggle('hidden', !chkEl.checked);
      });
    }
    fpsSel?.addEventListener('change', updateHint);
    updateHint();
  }

  // ── 样式模板 ──────────────────────────────────────────────
  async function loadStyleTemplates() {
    try {
      const res  = await fetch('/api/style-templates');
      const data = await res.json();
      const wrap = get('style-template-select-wrapper');
      if (!wrap || !data.success) return;

      const sel = document.createElement('select');
      sel.id = 'style-template-select';
      sel.className = 'form-field w-full h-11 px-md rounded text-body';

      const blank = new Option('— 不使用样式模板 —', '');
      sel.appendChild(blank);

      (data.templates || []).forEach(t => {
        sel.appendChild(new Option(t.name || t.id, t.content || t.name || ''));
      });

      wrap.innerHTML = '';
      wrap.appendChild(sel);

      sel.addEventListener('change', () => {
        const ft = get('format-template');
        if (ft) ft.value = sel.value;
      });
    } catch (e) {
      console.warn('loadStyleTemplates:', e);
    }
  }

  // ── 加载人设列表 ──────────────────────────────────────────
  async function loadPersonas() {
    try {
      const res = await fetch('/api/config');
      const data = await res.json();
      if (data.success && data.data && data.data.skills) {
        const select = document.getElementById('persona-select');
        if (select) {
          select.innerHTML = '<option value="">默认人设 (公众号爆款创作者)</option>';
          data.data.skills.forEach(skill => {
            const opt = document.createElement('option');
            opt.value = skill.id;
            opt.textContent = `${skill.name} (${skill.description})`;
            select.appendChild(opt);
          });
        }
      }
    } catch (e) {
      console.warn('loadPersonas:', e);
    }
  }

  // ── 生成文章 ──────────────────────────────────────────────
  async function generateArticle() {
    const isHot = !get('hot-options-section')?.classList.contains('hidden');
    const title = isHot ? '' : val('article-title');
    if (!isHot && !title) { Utils.showToast('请输入文章标题', 'warning'); return; }

    // 行业 / 平台
    let industry = '', platform = '';
    for (const r of document.getElementsByName('industry'))  if (r.checked) industry = r.value;
    for (const r of document.getElementsByName('platform'))  if (r.checked) platform = r.value;

    // 生图
    const imageModel = val('image-model-select') || 'gemini';
    let dashscope_params;
    if (imageModel === 'dashscope') {
      const modelVal = val('dashscope-image-model-value');
      if (!modelVal) { Utils.showToast('请选择阿里云百炼生图模型', 'warning'); return; }
      dashscope_params = {
        model_name:      modelVal,
        positive_prompt: val('dashscope-positive-prompt'),
        negative_prompt: val('dashscope-negative-prompt'),
        size:            val('dashscope-image-ratio'),
        steps:           val('dashscope-steps') ? parseInt(val('dashscope-steps')) : undefined,
      };
    }

    // 视频
    const enableVideo = chk('enable-video');
    const video_model = enableVideo ? 'inodetree' : '';
    const video_count = enableVideo ? (parseInt(val('video-count')) || 1)  : 0;
    const video_fps   = enableVideo ? (parseInt(val('video-fps'))   || 24) : 24;

    const body = {
      title,
      persona_id:          val('persona-select') || '',
      word_count:          parseInt(val('article-word-count'))  || 8000,
      image_count:         parseInt(val('article-image-count')) || 3,
      format_template:     val('format-template'),
      ai_model:            val('ai-model-select') || 'gemini',
      image_model:         imageModel,
      custom_image_prompt: val('custom-image-prompt'),
      dashscope_params,
      industry,
      platform,
      video_model,
      video_count,
      video_fps,
    };

    showProgress(true);
    setProgress(5, '接收需求…');
    const genBtn = get('generate-article');
    if (genBtn) genBtn.disabled = true;

    // 模拟进度步骤
    const steps = [[15,'生成文章内容…'],[45,'生成摘要…'],[65,'生成配图…'],[85,'清理内容…'],[93,'即将完成…']];
    let si = 0;
    const timer = setInterval(() => { if (si < steps.length) { setProgress(...steps[si]); si++; } }, 3500);

    try {
      const res  = await fetch('/api/generate-article', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(body),
      });
      const data = await res.json();
      clearInterval(timer);

      if (data.success) {
        setProgress(100, '生成完成！');
        _currentArticle = data.data;
        renderPreview(data.data);
        prependHistory(data.data);
        // 如果文章含视频占位符，启动轮询
        scanAndStartVideoPollers();
        Utils.showToast('文章生成成功', 'success');
      } else {
        Utils.showToast('生成失败：' + data.message, 'error');
      }
    } catch (e) {
      clearInterval(timer);
      Utils.showToast('生成异常：' + e.message, 'error');
    } finally {
      if (genBtn) genBtn.disabled = false;
      setTimeout(() => showProgress(false), 2000);
    }
  }

  // ── 预览渲染 ──────────────────────────────────────────────
  function renderPreview(data) {
    const preview = get('article-preview');
    if (!preview || !data) return;
    preview.innerHTML = `
      <h2 style="font-size:18px;font-weight:700;line-height:1.4;margin-bottom:8px;">${data.title || ''}</h2>
      <div style="display:flex;gap:8px;font-size:11px;color:#666;margin-bottom:12px;">
        <span style="color:#07c160;font-weight:500;">${data.author || 'AI笔记'}</span>
        <span>${data.generated_at || ''}</span>
      </div>
      ${data.content || ''}
    `;
  }

  // ── 历史记录 ──────────────────────────────────────────────
  let _historyItems = [];   // 全量缓存

  const STATUS_LABEL = {
    published: { text: '已发布', cls: 'bg-wechat-green/10 text-wechat-green' },
    saved:     { text: '已保存', cls: 'bg-blue-500/10 text-blue-500' },
    generated: { text: '已生成', cls: 'bg-surface-container-highest text-on-surface-variant' },
  };

  function _statusInfo(item) {
    if (item.status === 'published' || item.published_at) return STATUS_LABEL.published;
    if (item.status === 'saved'     || item.media_id)     return STATUS_LABEL.saved;
    return STATUS_LABEL.generated;
  }

  function _buildHistoryEl(item) {
    const st  = _statusInfo(item);
    const el  = document.createElement('div');
    el.className = 'flex items-start gap-xs p-xs rounded-lg hover:bg-surface-container cursor-pointer transition-all';
    el.dataset.id = item.id || '';
    el.innerHTML = `
      <div class="w-8 h-8 rounded-md bg-surface-container-high flex-shrink-0 flex items-center justify-center mt-[2px]">
        <span class="material-symbols-outlined text-on-surface-variant" style="font-size:15px;">article</span>
      </div>
      <div class="flex-1 min-w-0">
        <p class="text-body font-medium truncate leading-snug">${item.title || '无标题'}</p>
        <p class="text-caption text-on-surface-variant mt-[1px] leading-snug">
          ${(item.generated_at || '').slice(5, 16)}
          · ${item.content_length || 0} 字
          · ${item.image_count || 0} 图
          ${item.tokens_used ? '· ' + item.tokens_used + ' tk' : ''}
        </p>
      </div>
      <span class="flex-shrink-0 text-[10px] px-xs py-[1px] rounded-full font-medium ${st.cls}">${st.text}</span>
    `;
    el.addEventListener('click', async () => {
      // 高亮选中
      document.querySelectorAll('#history-list > div[data-id]').forEach(e => e.classList.remove('bg-surface-container'));
      el.classList.add('bg-surface-container');

      // 如果 item 已有 content 直接渲染
      if (item.content) {
        _currentArticle = item;
        renderPreview(item);
        scanAndStartVideoPollers();   // 历史记录可能含未完成的视频占位符
        return;
      }

      // 否则从 cache_files 按需加载
      const cacheFiles = item.cache_files || [];
      if (!cacheFiles.length && !item.title) {
        Utils.showToast('该记录无缓存文件，无法预览', 'warning');
        return;
      }

      try {
        const res  = await fetch('/api/article-content', {
          method:  'POST',
          headers: { 'Content-Type': 'application/json' },
          body:    JSON.stringify({ cache_files: cacheFiles, title: item.title || '' }),
        });
        const data = await res.json();
        if (data.success && data.content) {
          item.content = data.content;
          _currentArticle = item;
          renderPreview(item);
          scanAndStartVideoPollers();
        } else if (data.success && data.data && data.data.content) {
          item.content = data.data.content;
          _currentArticle = item;
          renderPreview(item);
          scanAndStartVideoPollers();
        } else {
          Utils.showToast('加载文章内容失败', 'error');
        }
      } catch (e) {
        Utils.showToast('加载失败：' + e.message, 'error');
      }
    });
    return el;
  }

  function _renderHistoryList() {
    const list     = get('history-list');
    const search   = (get('history-search')?.value || '').toLowerCase();
    const filterSt = get('history-filter-status')?.value || '';
    const sort     = get('history-sort')?.value || 'time_desc';

    if (!list) return;

    // 过滤
    let items = _historyItems.filter(item => {
      const matchSearch = !search || (item.title || '').toLowerCase().includes(search);
      const matchStatus = !filterSt || (
        filterSt === 'published' ? (item.status === 'published' || !!item.published_at) :
        filterSt === 'saved'     ? (item.status === 'saved' || (!!item.media_id && !item.published_at)) :
        item.status === 'generated' || (!item.media_id && !item.published_at)
      );
      return matchSearch && matchStatus;
    });

    // 排序
    const sorters = {
      time_desc:    (a, b) => (b.generated_at || '').localeCompare(a.generated_at || ''),
      time_asc:     (a, b) => (a.generated_at || '').localeCompare(b.generated_at || ''),
      length_desc:  (a, b) => (b.content_length || 0) - (a.content_length || 0),
      length_asc:   (a, b) => (a.content_length || 0) - (b.content_length || 0),
      images_desc:  (a, b) => (b.image_count || 0)    - (a.image_count || 0),
      tokens_desc:  (a, b) => (b.tokens_used || 0)    - (a.tokens_used || 0),
    };
    items.sort(sorters[sort] || sorters.time_desc);

    // 渲染
    list.innerHTML = '';
    if (!items.length) {
      list.innerHTML = '<div data-empty class="text-caption text-on-surface-variant text-center py-md">暂无匹配记录</div>';
    } else {
      items.forEach(item => list.appendChild(_buildHistoryEl(item)));
    }

    // 更新计数
    const countEl = get('history-count');
    if (countEl) countEl.textContent = items.length + ' / ' + _historyItems.length;
  }

  function prependHistory(item) {
    // 去重（同 id 或同标题+时间）
    _historyItems = _historyItems.filter(i => i.id !== item.id);
    _historyItems.unshift(item);
    _renderHistoryList();
  }

  async function loadHistory() {
    try {
      const res  = await fetch('/api/generation-history?limit=100');
      const data = await res.json();
      if (!data.success) return;
      _historyItems = Array.isArray(data.data) ? data.data : [];
      _renderHistoryList();

      // 绑定筛选/排序/搜索事件（只绑一次）
      ['history-search', 'history-filter-status', 'history-sort'].forEach(id => {
        get(id)?.addEventListener('input',  _renderHistoryList);
        get(id)?.addEventListener('change', _renderHistoryList);
      });
    } catch (e) { console.warn('loadHistory:', e); }
  }

  // ── 保存草稿 ──────────────────────────────────────────────
  async function saveDraft() {
    if (!_currentArticle) { Utils.showToast('请先生成文章', 'warning'); return; }
    const btn = get('save-draft');
    const origHtml = btn?.innerHTML;
    if (btn) { btn.disabled = true; btn.innerHTML = '<span class="material-symbols-outlined animate-spin" style="font-size:16px;">sync</span> 保存中…'; }

    try {
      const res  = await fetch('/api/save-draft', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ article: _currentArticle }),
      });
      const data = await res.json();
      if (data.success) {
        _currentArticle._media_id = data.data?.media_id;
        Utils.showToast('草稿保存成功', 'success');
      } else {
        Utils.showToast('保存失败：' + data.message, 'error');
      }
    } catch (e) {
      Utils.showToast('保存异常：' + e.message, 'error');
    } finally {
      if (btn) { btn.disabled = false; btn.innerHTML = origHtml; }
    }
    return _currentArticle._media_id;
  }

  // ── 发布文章 ──────────────────────────────────────────────
  async function publishArticle() {
    if (!_currentArticle) { Utils.showToast('请先生成文章', 'warning'); return; }

    // 确保有 media_id
    if (!_currentArticle._media_id) {
      Utils.showToast('正在保存草稿…', 'info', 1500);
      const mid = await saveDraft();
      if (!mid) { Utils.showToast('保存草稿失败，无法发布', 'error'); return; }
    }

    const statusEl = get('publish-status');
    const msgEl    = get('publish-message');
    const enableMass = chk('enable-mass-send');

    if (statusEl) { statusEl.classList.remove('hidden'); statusEl.className = 'mb-sm text-label rounded-lg px-md py-sm bg-blue-50 border border-blue-200 text-blue-700'; }
    if (msgEl)    msgEl.textContent = '发布中，请稍候…';

    const btn = get('publish-article');
    const orig = btn?.innerHTML;
    if (btn) { btn.disabled = true; btn.innerHTML = '<span class="material-symbols-outlined animate-spin" style="font-size:16px;">sync</span> 发布中…'; }

    try {
      const res  = await fetch('/api/publish-draft', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ media_id: _currentArticle._media_id, enable_mass_send: enableMass }),
      });
      const data = await res.json();

      if (data.success) {
        if (statusEl) statusEl.className = 'mb-sm text-label rounded-lg px-md py-sm bg-wechat-green/10 border border-wechat-green/30 text-wechat-green';
        if (msgEl)    msgEl.textContent = '发布任务已提交！请在微信公众号后台确认最终结果（发布异步进行约1-2分钟）。';
        Utils.showToast('发布成功', 'success');
      } else {
        if (statusEl) statusEl.className = 'mb-sm text-label rounded-lg px-md py-sm bg-red-50 border border-red-200 text-red-600';
        if (msgEl)    msgEl.textContent = '发布失败：' + data.message;
        Utils.showToast('发布失败：' + data.message, 'error');
      }
    } catch (e) {
      if (msgEl) msgEl.textContent = '发布异常：' + e.message;
      Utils.showToast('发布异常：' + e.message, 'error');
    } finally {
      if (btn) { btn.disabled = false; btn.innerHTML = orig; }
    }
  }

  // ── 视频轮询 ──────────────────────────────────────────────
  // 策略：提交任务后等待 10s，再每 10s 查一次，最多 30 次
  const _videoPollers = new Map();  // video_id → { timer, attempts }

  function startVideoPoller(videoId) {
    if (_videoPollers.has(videoId)) return;  // 已在轮询中

    // 多个视频错开启动，避免同时发请求触发限流（每个额外随机 0-2 秒）
    const jitter = _videoPollers.size * 5_000 + Math.random() * 2_000;
    const firstDelay = 10_000 + jitter;
    console.log(`[video] ${videoId} 任务已提交，${Math.round(firstDelay/1000)}s 后开始轮询`);
    _updateVideoPlaceholder(videoId, 'pending', 0);

    const state = { attempts: 0, timer: null };
    _videoPollers.set(videoId, state);

    state.timer = setTimeout(() => _pollOnce(videoId), firstDelay);
  }

  async function _pollOnce(videoId) {
    const state = _videoPollers.get(videoId);
    if (!state) return;

    state.attempts++;
    console.log(`[video] ${videoId} 第 ${state.attempts}/24 次轮询`);

    try {
      const res  = await fetch(`/api/video-status?video_id=${encodeURIComponent(videoId)}`);
      const data = await res.json();

      if (!data.success) {
        const errMsg = (data.message && data.message !== 'None') ? data.message : '请稍后重试';
        _updateVideoPlaceholder(videoId, 'error', state.attempts, errMsg);
        _videoPollers.delete(videoId);
        return;
      }

      const { status, progress, cache_url } = data;
      _updateVideoPlaceholder(videoId, status, progress, null, cache_url);

      if (status === 'completed' && cache_url) {
        console.log(`[video] ${videoId} 生成完成: ${cache_url}`);
        _videoPollers.delete(videoId);
        Utils.showToast('视频生成完成', 'success');
        return;
      }

      // completed 但没有 cache_url：云函数转存未完成或还在处理，继续轮询几次
      if (status === 'completed' && !cache_url) {
        console.log(`[video] ${videoId} completed 但 cache_url 为空，继续等待转存... (${state.attempts}/8)`);
        if (state.attempts >= 8) {
          // 8次内没拿到 URL，停止轮询，提示用户
          _updateVideoPlaceholder(videoId, 'timeout', 100);
          _videoPollers.delete(videoId);
          Utils.showToast('视频已生成，但转存链接获取失败，请重新部署云函数', 'warning');
        } else {
          state.timer = setTimeout(() => _pollOnce(videoId), 10_000);
        }
        return;
      }

      if (status === 'failed') {
        _videoPollers.delete(videoId);
        Utils.showToast('视频生成失败', 'error');
        return;
      }

      // 超过 30 次放弃（约5分钟）
      if (state.attempts >= 30) {
        _updateVideoPlaceholder(videoId, 'timeout', 100);
        _videoPollers.delete(videoId);
        Utils.showToast('视频生成超时（约5分钟），可稍后刷新', 'warning');
        return;
      }

      // 继续 10 秒后轮询
      state.timer = setTimeout(() => _pollOnce(videoId), 10_000);

    } catch (e) {
      console.warn(`[video] ${videoId} 轮询异常:`, e);
      if (state.attempts < 30) {
        state.timer = setTimeout(() => _pollOnce(videoId), 10_000);
      } else {
        _videoPollers.delete(videoId);
      }
    }
  }

  function _updateVideoPlaceholder(videoId, status, progress, errMsg, cacheUrl) {
    // 同时更新预览区和 _currentArticle.content 里的占位符
    const preview = get('article-preview');
    if (!preview) return;

    // 健壮性转义 CSS 选择器中的特殊字符，防止 DOMException 报错导致脚本崩溃
    const escapedVid = (window.CSS && CSS.escape) ? CSS.escape(videoId) : videoId.replace(/([!"#$%&'()*+,./:;<=>?@\[\\\]^`{|}~])/g, '\\$1');
    const el = preview.querySelector(`[data-video-placeholder="${escapedVid}"]`);
    if (!el) return;

    if (status === 'completed' && cacheUrl) {
      // 替换为真实 video 标签
      el.outerHTML = `<video src="${cacheUrl}" controls
        style="max-width:100%;height:auto;border-radius:8px;margin:8px 0;"
        preload="metadata"></video>`;
      // 同步更新 _currentArticle.content
      if (_currentArticle) {
        _currentArticle.content = (_currentArticle.content || '').replace(
          new RegExp(`<div[^>]*data-video-placeholder="${videoId.replace(/[+/=]/g, '\\$&')}[^>]*>[\\s\\S]*?</div>`, 'g'),
          `<video src="${cacheUrl}" controls style="max-width:100%;height:auto;border-radius:8px;margin:8px 0;" preload="metadata"></video>`
        );
      }
    } else if (status === 'error' || status === 'failed') {
      el.innerHTML = `<span style="color:#ba1a1a;">⚠️ 视频生成失败${errMsg ? '：' + errMsg : ''}</span>`;
    } else if (status === 'timeout') {
      el.innerHTML = `<span style="color:#f59e0b;">⏱ 视频生成超时，任务仍在后台运行</span>`;
    } else {
      // pending / processing
      const pct = progress > 0 ? ` (${progress}%)` : '';
      const waiting = status === 'pending' ? '等待队列中' : '生成中';
      el.innerHTML = `
        <div style="display:flex;align-items:center;gap:8px;justify-content:center;">
          <div style="width:16px;height:16px;border:2px solid #07c160;border-top-color:transparent;
            border-radius:50%;animation:spin 0.8s linear infinite;"></div>
          <span>🎬 视频${waiting}${pct}，请勿关闭页面</span>
        </div>`;
    }
  }

  // 扫描预览内容中的所有占位符并启动轮询
  function scanAndStartVideoPollers() {
    const preview = get('article-preview');
    if (!preview) return;
    preview.querySelectorAll('[data-video-placeholder]').forEach(el => {
      const vid = el.dataset.videoPlaceholder;
      if (vid) startVideoPoller(vid);
    });
  }
  function copyHTML() {
    const preview = get('article-preview');
    if (!preview) return;
    const text = preview.innerHTML;
    if (navigator.clipboard) {
      navigator.clipboard.writeText(text)
        .then(() => Utils.showToast('HTML 已复制到剪贴板', 'success'))
        .catch(() => _fallbackCopy(text));
    } else {
      _fallbackCopy(text);
    }
  }

  function _fallbackCopy(text) {
    const ta = Object.assign(document.createElement('textarea'), { value: text });
    document.body.appendChild(ta);
    ta.select();
    try { document.execCommand('copy'); Utils.showToast('HTML 已复制', 'success'); }
    catch { Utils.showToast('复制失败，请手动复制', 'error'); }
    document.body.removeChild(ta);
  }

  // ── 初始化 ───────────────────────────────────────────────
  function init() {
    initTitleModeToggle();
    initVideoToggle();
    initImageModelToggle();
    initDashscopeDropdown();
    loadStyleTemplates();
    loadPersonas();
    loadHistory();

    get('generate-article') ?.addEventListener('click', generateArticle);
    get('save-draft')        ?.addEventListener('click', saveDraft);
    get('publish-article')   ?.addEventListener('click', publishArticle);
    get('copy-html-btn')     ?.addEventListener('click', copyHTML);
    get('refresh-preview-btn')?.addEventListener('click', () => {
      if (_currentArticle) renderPreview(_currentArticle);
    });
  }

  return { init, renderPreview };
})();

document.addEventListener('DOMContentLoaded', () => CreateTab.init());
