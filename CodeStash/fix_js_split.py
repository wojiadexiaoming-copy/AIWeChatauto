# -*- coding: utf-8 -*-
"""
把 initImageModelToggle 从 tab_config.js 移到 tab_create.js
顺便把 user-ip-topup 的设置加进 tab_config.js 的 loadUserIP
"""
import os

ROOT = os.path.dirname(os.path.abspath(__file__))

# ── 1. tab_config.js：去掉 initImageModelToggle，调用也去掉 ──
cfg_path = os.path.join(ROOT, 'static', 'js', 'tab_config.js')
cfg = open(cfg_path, encoding='utf-8').read()

# 去掉方法定义
OLD_METHOD = """
  // ── 生图模型切换联动 ─────────────────────────────────────
  function initImageModelToggle() {
    const sel   = document.getElementById('image-model-select');
    const extra = document.getElementById('dashscope-extra-fields');
    const prompt = document.getElementById('custom-image-prompt');
    if (!sel) return;

    function update() {
      const isDash = sel.value === 'dashscope';
      if (extra)  extra.classList.toggle('hidden', !isDash);
      if (prompt) prompt.classList.toggle('hidden', isDash);
    }
    sel.addEventListener('change', update);
    update();
  }"""
cfg = cfg.replace(OLD_METHOD, '', 1)

# 去掉调用
cfg = cfg.replace('    initImageModelToggle();\n', '', 1)

open(cfg_path, 'w', encoding='utf-8').write(cfg)
print("✓ tab_config.js 已移除 initImageModelToggle")

# ── 2. tab_create.js：在 init() 里加上 initImageModelToggle ──
crt_path = os.path.join(ROOT, 'static', 'js', 'tab_create.js')
crt = open(crt_path, encoding='utf-8').read()

IMAGE_TOGGLE_FN = """
  // ── 生图模型切换联动 ──────────────────────────────────────
  function initImageModelToggle() {
    const sel    = document.getElementById('image-model-select');
    const extra  = document.getElementById('dashscope-extra-fields');
    const prompt = document.getElementById('custom-image-prompt');
    if (!sel) return;

    function update() {
      const isDash = sel.value === 'dashscope';
      if (extra)  extra.classList.toggle('hidden', !isDash);
      if (prompt) prompt.classList.toggle('hidden', isDash);
    }
    sel.addEventListener('change', update);
    update();
  }

"""

# 插在 initVideoToggle 前
crt = crt.replace(
    '  // ── 视频参数联动 ──────────────────────────────────────',
    IMAGE_TOGGLE_FN + '  // ── 视频参数联动 ──────────────────────────────────────',
    1
)

# 在 init() 里加调用（在 initVideoToggle 后）
crt = crt.replace(
    '    initVideoToggle();\n',
    '    initVideoToggle();\n    initImageModelToggle();\n',
    1
)

open(crt_path, 'w', encoding='utf-8').write(crt)
print("✓ tab_create.js 已加入 initImageModelToggle")

# ── 3. tab_config.js：loadUserIP 也同步更新 user-ip-topup ──
cfg = open(cfg_path, encoding='utf-8').read()

# user-ip-topup 在 loadUserIP 里已经有了（['user-ip', 'user-ip-topup']），
# 但 tab_topup.html 用的是 user-ip-topup，确认已包含
if 'user-ip-topup' in cfg:
    print("✓ tab_config.js 已包含 user-ip-topup")
else:
    # 补充
    cfg = cfg.replace(
        "['user-ip'].forEach(id => {",
        "['user-ip', 'user-ip-topup'].forEach(id => {",
        1
    )
    open(cfg_path, 'w', encoding='utf-8').write(cfg)
    print("✓ tab_config.js 补充 user-ip-topup")

print("\n全部完成")
