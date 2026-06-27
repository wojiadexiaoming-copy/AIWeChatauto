# -*- coding: utf-8 -*-
"""把 initDashscopeDropdown 从 tab_config.js 移到 tab_create.js"""
import os

ROOT = os.path.dirname(os.path.abspath(__file__))

cfg_path = os.path.join(ROOT, 'static', 'js', 'tab_config.js')
crt_path = os.path.join(ROOT, 'static', 'js', 'tab_create.js')
cfg = open(cfg_path, encoding='utf-8').read()
crt = open(crt_path, encoding='utf-8').read()

# 从 tab_config.js 提取 initDashscopeDropdown 方法
import re
m = re.search(r'(  // ── 阿里云百炼自定义下拉 ──.+?(?=\n  // ──|\n  function init\b))', cfg, re.DOTALL)
if m:
    fn_block = m.group(1)
    # 从 config 里删
    cfg = cfg.replace(fn_block, '', 1)
    # config init 里删调用
    cfg = cfg.replace('    initDashscopeDropdown();\n', '', 1)
    open(cfg_path, 'w', encoding='utf-8').write(cfg)
    print("✓ tab_config.js 已移除 initDashscopeDropdown")

    # 加到 tab_create.js 的 initVideoToggle 前
    crt = crt.replace(
        '  // ── 视频参数联动 ──────────────────────────────────────',
        fn_block.strip() + '\n\n  // ── 视频参数联动 ──────────────────────────────────────',
        1
    )
    # create init 里加调用（在 initVideoToggle 后）
    crt = crt.replace(
        '    initVideoToggle();\n    initImageModelToggle();\n',
        '    initVideoToggle();\n    initImageModelToggle();\n    initDashscopeDropdown();\n',
        1
    )
    open(crt_path, 'w', encoding='utf-8').write(crt)
    print("✓ tab_create.js 已加入 initDashscopeDropdown")
else:
    print("未找到 initDashscopeDropdown，已在 create 里？检查…")
    if 'initDashscopeDropdown' in crt:
        print("  已存在于 tab_create.js ✓")
    else:
        print("  两者都没有，需要手动检查")

print("完成")
