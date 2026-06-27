# -*- coding: utf-8 -*-
import os, ast

ROOT = os.path.dirname(os.path.abspath(__file__))
ctrl_path = os.path.join(ROOT, 'controllers', 'article_controller.py')
lines = open(ctrl_path, encoding='utf-8').read().splitlines(keepends=True)

# 找两个 else 的精确行号（0-indexed）
cfg_else = None
gen_else = None

for i, l in enumerate(lines):
    if l == '            else:\n':
        next_line = lines[i+1] if i+1 < len(lines) else ''
        if "'success': False" in next_line:
            prev = ''.join(lines[max(0, i-25):i])
            if 'dashscope_config' in prev and 'qwen-turbo' in prev and cfg_else is None:
                cfg_else = i
                print(f"配置检查 else 位于第 {i+1} 行")
            elif 'generate_article_content' in prev and 'dashscope' in prev and gen_else is None:
                gen_else = i
                print(f"内容生成 else 位于第 {i+1} 行")

print(f"cfg_else={cfg_else}, gen_else={gen_else}")

inodetree_gen_lines = [
    "            elif ai_model == 'inodetree':\n",
    "                content = self.inodetree_service.generate_article_content(\n",
    "                    title, model_name, word_count, format_template=format_template)\n",
]

inodetree_cfg_lines = [
    "            elif ai_model == 'inodetree':\n",
    "                inodetree_config = self.config_service.get_inodetree_config()\n",
    "                logger.info(f\"InodeTree配置检查: api_key={'已设置' if inodetree_config.get('api_key') else '未设置'}\")\n",
    "                if not inodetree_config['api_key']:\n",
    "                    return {'success': False, 'message': '请先配置 InodeTree API Key'}\n",
    "                self.inodetree_service.set_api_key(inodetree_config['api_key'])\n",
    "                model_name = inodetree_config.get('model', 'inodetree-2.0-flash')\n",
]

# 先插 gen（行号靠后），再插 cfg（行号靠前），避免偏移问题
if gen_else is not None:
    for j, ln in enumerate(inodetree_gen_lines):
        lines.insert(gen_else + j, ln)
    print(f"✓ 插入内容生成 inodetree 分支")
    # cfg_else 在 gen_else 前面，不受影响
else:
    print("✗ 未找到内容生成 else")

if cfg_else is not None:
    for j, ln in enumerate(inodetree_cfg_lines):
        lines.insert(cfg_else + j, ln)
    print(f"✓ 插入配置检查 inodetree 分支")
else:
    print("✗ 未找到配置检查 else")

result = ''.join(lines)
open(ctrl_path, 'w', encoding='utf-8').write(result)

try:
    ast.parse(result)
    print("✓ 语法检查通过")
except SyntaxError as e:
    print(f"✗ 语法错误: {e}")

# 验证
print("\n验证 inodetree 相关行：")
for i, l in enumerate(result.split('\n')):
    if 'inodetree' in l and any(k in l for k in ['elif', 'generate_article_content', 'set_api_key', 'get_inodetree']):
        print(f"  {i+1}: {l}")
