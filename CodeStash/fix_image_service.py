# -*- coding: utf-8 -*-
"""在 image_service.py 第83行（else前）插入 inodetree/inodetree_pexels 分支"""
import os, ast

ROOT = os.path.dirname(os.path.abspath(__file__))
path = os.path.join(ROOT, 'services', 'image_service.py')
lines = open(path, encoding='utf-8').read().split('\n')

# 验证第82/83行
print(f"行82: {repr(lines[81])}")
print(f"行83: {repr(lines[82])}")

# 在第83行（0-indexed=82）的 else 前插入 inodetree 和 inodetree_pexels 分支
insert_idx = 82  # else 所在行的 0-indexed

new_lines = [
    "            elif image_model == \"inodetree\":",
    "                # InodeTree Image 2.1 Flash 直接生图",
    "                return self._generate_with_inodetree_image(final_prompt)",
    "            elif image_model == \"inodetree_pexels\":",
    "                # InodeTree 生成搜索词 + Pexels 取图",
    "                return self._search_with_pexels(title, description, article_content, \"inodetree\",",
    "                                              image_index=image_index, total_images=total_images)",
]

for j, ln in enumerate(new_lines):
    lines.insert(insert_idx + j, ln)

result = '\n'.join(lines)
open(path, 'w', encoding='utf-8').write(result)

try:
    ast.parse(result)
    print("✓ 语法检查通过")
except SyntaxError as e:
    print(f"✗ 语法错误: {e}")

# 验证插入结果
print("\n验证 image_model 分支：")
for i, l in enumerate(result.split('\n')[60:100], 61):
    print(f"  {i}: {l}")
