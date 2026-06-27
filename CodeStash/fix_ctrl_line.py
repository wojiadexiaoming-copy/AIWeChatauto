# -*- coding: utf-8 -*-
"""直接按行号插入 inodetree 分支（行号基于 1-indexed）"""
import os, ast

ROOT = os.path.dirname(os.path.abspath(__file__))
ctrl_path = os.path.join(ROOT, 'controllers', 'article_controller.py')
lines = open(ctrl_path, encoding='utf-8').read().split('\n')

# 验证关键行内容
print(f"行200: {repr(lines[199])}")
print(f"行201: {repr(lines[200])}")
print(f"行220: {repr(lines[219])}")
print(f"行221: {repr(lines[220])}")

# ── 两处要插入的内容（作为行列表）──

inodetree_cfg = [
    "            elif ai_model == 'inodetree':",
    "                inodetree_config = self.config_service.get_inodetree_config()",
    "                logger.info(f\"InodeTree配置: api_key={'已设置' if inodetree_config.get('api_key') else '未设置'}\")",
    "                if not inodetree_config['api_key']:",
    "                    return {'success': False, 'message': '请先配置 InodeTree API Key'}",
    "                self.inodetree_service.set_api_key(inodetree_config['api_key'])",
    "                model_name = inodetree_config.get('model', 'inodetree-2.0-flash')",
    "",
]

inodetree_gen = [
    "            elif ai_model == 'inodetree':",
    "                content = self.inodetree_service.generate_article_content(",
    "                    title, model_name, word_count, format_template=format_template)",
]

# 行200 是 else（0-indexed=199），在它前面插入 inodetree_cfg
# 行220 是 else（0-indexed=219），在它前面插入 inodetree_gen
# 先插后面那个（220行），再插前面（200行），避免偏移

# 插入到 0-indexed=219（第220行前）
for j, ln in enumerate(inodetree_gen):
    lines.insert(219 + j, ln)
print(f"✓ 插入内容生成 inodetree 分支（原第220行前）")

# 插入到 0-indexed=199（第200行前，因为gen插入了{len(inodetree_gen)}行，偏移不影响此处）
for j, ln in enumerate(inodetree_cfg):
    lines.insert(199 + j, ln)
print(f"✓ 插入配置检查 inodetree 分支（原第200行前）")

result = '\n'.join(lines)
open(ctrl_path, 'w', encoding='utf-8').write(result)

try:
    ast.parse(result)
    print("✓ 语法检查通过")
except SyntaxError as e:
    print(f"✗ 语法错误: {e}")

# 验证
print("\n验证 inodetree 相关行：")
for i, l in enumerate(result.split('\n')):
    if 'inodetree' in l and any(k in l for k in ['elif', 'generate_article', 'set_api_key', 'get_inodetree', 'model_name']):
        print(f"  {i+1}: {l}")
