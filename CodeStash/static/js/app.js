/**
 * app.js — 全局工具模块
 * 仅包含：ApiClient、Utils (showToast / addLog)
 * 业务逻辑已拆分到 tab_create.js / tab_config.js / tab_topup.js
 */

// ── ApiClient ────────────────────────────────────────────────
const ApiClient = {
  async get(url) {
    const res = await fetch(url);
    return res.json();
  },
  async post(url, body) {
    const res = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    return res.json();
  },
};

// ── Utils ────────────────────────────────────────────────────
const Utils = {
  /**
   * 显示 Toast 通知
   * @param {string} message
   * @param {'success'|'error'|'warning'|'info'} type
   * @param {number} duration ms
   */
  showToast(message, type = 'info', duration = 3000) {
    const container = document.getElementById('toast-container');
    if (!container) return;

    const toast = document.createElement('div');
    toast.className = `toast-msg toast-${type}`;
    toast.textContent = message;
    container.appendChild(toast);

    setTimeout(() => {
      toast.style.transition = 'opacity 0.3s';
      toast.style.opacity = '0';
      setTimeout(() => toast.remove(), 300);
    }, duration);
  },

  /** 控制台日志（兼容旧代码调用） */
  addLog(message, level = 'info') {
    const prefix = level === 'error' ? '[ERR]' : '[LOG]';
    console.log(`${prefix} ${message}`);
  },
};
