/**
 * tab_topup.js — 模型充值 Tab
 * 负责：数据统计（天/周/月）、模型状态
 */

const TopupTab = (() => {
  'use strict';

  const get = id => document.getElementById(id);
  const set = (id, v) => { const el = get(id); if (el) el.textContent = v; };

  let currentPeriod = 'week';

  // ── 数据统计 ──────────────────────────────────────────────
  async function loadStats(period) {
    currentPeriod = period || currentPeriod;
    try {
      const res  = await fetch(`/api/stats?period=${currentPeriod}`);
      const data = await res.json();
      if (!data.success) return;

      const r = data.range;
      const a = data.all;

      // 区间数据
      set('stat-total',     r.total);
      set('stat-published', r.published);
      set('stat-draft',     r.draft);
      set('stat-tokens',    r.tokens >= 10000
        ? (r.tokens / 10000).toFixed(1) + 'w'
        : r.tokens);
      set('stat-images',    r.images);
      set('stat-videos',    r.videos);

      // 累计
      set('stat-all-total',     a.total);
      set('stat-all-published', a.published);
      set('stat-all-draft',     a.draft);

    } catch (e) { console.warn('loadStats:', e); }
  }

  // ── 时间段切换 ──────────────────────────────────────────
  function initPeriodSwitcher() {
    const switcher = get('stats-period-switcher');
    if (!switcher) return;
    switcher.querySelectorAll('.stats-period-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        switcher.querySelectorAll('.stats-period-btn').forEach(b => {
          b.classList.remove('bg-white', 'shadow-sm', 'text-wechat-green');
          b.classList.add('text-on-surface-variant');
        });
        btn.classList.add('bg-white', 'shadow-sm', 'text-wechat-green');
        btn.classList.remove('text-on-surface-variant');
        loadStats(btn.dataset.period);
      });
    });
  }

  // ── 模型状态 ──────────────────────────────────────────────
  async function loadModelStatus() {
    try {
      const res  = await fetch('/api/config-status');
      const data = await res.json();
      const list = get('model-status-list');
      if (!list || !data.success) return;

      const s = data.data || {};
      const models = [
        { key: 'wechat_configured',    label: '微信公众号',    icon: 'chat',         color: 'text-wechat-green' },
        { key: 'gemini_configured',    label: 'Google Gemini', icon: 'auto_awesome', color: 'text-blue-500' },
        { key: 'deepseek_configured',  label: 'DeepSeek',      icon: 'psychology',   color: 'text-gray-700' },
        { key: 'dashscope_configured', label: '阿里云百炼',    icon: 'cloud_queue',  color: 'text-orange-500' },
        { key: 'inodetree_configured',     label: 'InodeTree',     icon: 'hub',          color: 'text-wechat-green' },
        { key: 'pexels_configured',    label: 'Pexels',        icon: 'image_search', color: 'text-green-500' },
      ];

      list.innerHTML = models.map(m => `
        <div class="flex items-center gap-sm px-xs py-xs rounded-lg hover:bg-surface-container-low transition-all">
          <div class="w-8 h-8 rounded-lg flex items-center justify-center ${s[m.key] ? 'bg-wechat-green/10' : 'bg-surface-container-high'}">
            <span class="material-symbols-outlined ${s[m.key] ? m.color : 'text-on-surface-variant'}" style="font-size:16px;${s[m.key] ? "font-variation-settings:'FILL' 1;" : ''}">${m.icon}</span>
          </div>
          <span class="flex-1 text-body">${m.label}</span>
          <span class="text-caption px-xs py-[2px] rounded-full ${s[m.key] ? 'bg-wechat-green/10 text-wechat-green' : 'bg-surface-container-highest text-on-surface-variant'}">
            ${s[m.key] ? '✓ 已配置' : '未配置'}
          </span>
        </div>
      `).join('');

    } catch (e) { console.warn('loadModelStatus:', e); }
  }

  // ── 初始化 ────────────────────────────────────────────────
  function init() {
    initPeriodSwitcher();
    loadStats('week');
    loadModelStatus();

    // 切换到此 tab 时刷新
    document.querySelectorAll('.tab-item').forEach(btn => {
      if (btn.dataset.tab === 'topup') {
        btn.addEventListener('click', () => {
          loadStats(currentPeriod);
          loadModelStatus();
        });
      }
    });
  }

  return { init };
})();

document.addEventListener('DOMContentLoaded', () => TopupTab.init());
