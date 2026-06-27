# -*- coding: utf-8 -*-
"""用行号精确插入 inodetree 分支"""
import os

ROOT = os.path.dirname(os.path.abspath(__file__))
ctrl_path = os.path.join(ROOT, 'controllers', 'article_controller.py')
lines = open(ctrl_path, encoding='utf-8').read().splitlines(keepends=True)

# ── 定位两处 else ──
# 找到"配置检查 else"（第 200 行附近）和"generate_article_content else"（第 220 行附近）
# 通过精确内容比对找行号

cfg_else_idx = None      # 第一处 else（配置检查）
gen_else_idx = None      # 第二处 else（内容生成）

for i, l in enumerate(lines):
    stripped = l.strip()
    if stripped == 'else:' and cfg_else_idx is None:
        # 看下一行是否是 return {'success': False, ...}
        if i+1 < len(lines) and "'success': False," in lines[i+1]:
            # 再确认上文里有 dashscope 字样
            ctx = ''.join(lines[max(0,i-20):i])
            if 'dashscope' in ctx and '配置检查' in ctx:
                cfg_else_idx = i
                print(f"找到配置检查 else 在第 {i+1} 行")

for i, l in enumerate(lines):
    stripped = l.strip()
    if stripped == 'else:' and i != cfg_else_idx:
        if i+1 < len(lines) and "'success': False," in lines[i+1]:
            ctx = ''.join(lines[max(0,i-10):i])
            if 'generate_article_content' in ctx:
                gen_else_idx = i
                print(f"找到内容生成 else 在第 {i+1} 行")
                break

print(f"cfg_else_idx={cfg_else_idx}, gen_else_idx={gen_else_idx}")

inodetree_cfg_block = """\
            elif ai_model == 'inodetree':
                inodetree_config = self.config_service.get_inodetree_config()
                logger.info(f"InodeTree配置检查: api_key={'已设置' if inodetree_config.get('api_key') else '未设置'}")
                if not inodetree_config['api_key']:
                    return {'success': False, 'message': '请先配置 InodeTree API Key'}
                self.inodetree_service.set_api_key(inodetree_config['api_key'])
                model_name = inodetree_config.get('model', 'inodetree-2.0-flash')
"""

inodetree_gen_block = """\
            elif ai_model == 'inodetree':
                content = self.inodetree_service.generate_article_content(title, model_name, word_count, format_template=format_template)
"""

# 先插 gen_else（行号大的先插，避免偏移）
if gen_else_idx is not None:
    lines.insert(gen_else_idx, inodetree_gen_block)
    print(f"✓ 插入内容生成 inodetree 分支（原第 {gen_else_idx+1} 行前）")
    # cfg_else_idx 未受影响（在前面）
else:
    print("✗ 未找到内容生成 else，跳过")

if cfg_else_idx is not None:
    lines.insert(cfg_else_idx, inodetree_cfg_block)
    print(f"✓ 插入配置检查 inodetree 分支（原第 {cfg_else_idx+1} 行前）")
else:
    print("✗ 未找到配置检查 else，跳过")

result = ''.join(lines)
open(ctrl_path, 'w', encoding='utf-8').write(result)

import ast
try:
    ast.parse(result)
    print("✓ 语法检查通过")
except SyntaxError as e:
    print(f"✗ 语法错误: {e}")

# 验证结果
lines2 = result.split('\n')
print("\n验证 inodetree 分支位置：")
for i, l in enumerate(lines2):
    if 'inodetree' in l and ('elif' in l or 'content' in l or 'config' in l):
        print(f"  {i+1}: {l[:120]}")
