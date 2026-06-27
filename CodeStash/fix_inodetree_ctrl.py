# -*- coding: utf-8 -*-
"""精确修复 article_controller.py 两处漏掉 inodetree 的分支"""
import os

ROOT = os.path.dirname(os.path.abspath(__file__))
ctrl_path = os.path.join(ROOT, 'controllers', 'article_controller.py')
ctrl = open(ctrl_path, encoding='utf-8').read()

# ── 修复1：配置检查 else 前插入 inodetree 分支 ──
OLD1 = """            elif ai_model == 'dashscope':
                # 检查阿里云百炼配置
                dashscope_config = self.config_service.get_dashscope_config()
                logger.info(f"阿里云百炼配置检查: api_key={'已设置' if dashscope_config.get('api_key') else '未设置'}")

                if not dashscope_config['api_key']:
                    return {
                        'success': False,
                        'message': '请先配置阿里云百炼API密钥'
                    }

                # 设置API密钥
                self.dashscope_service = DashScopeService(dashscope_config['api_key'])
                model_name = dashscope_config.get('model', 'qwen-turbo')

            else:
                return {
                    'success': False,
                    'message': f'不支持的AI模型: {ai_model}'
                }

            # 新增：接收前端传递的字数、配图数量和格式模板"""

NEW1 = """            elif ai_model == 'dashscope':
                # 检查阿里云百炼配置
                dashscope_config = self.config_service.get_dashscope_config()
                logger.info(f"阿里云百炼配置检查: api_key={'已设置' if dashscope_config.get('api_key') else '未设置'}")

                if not dashscope_config['api_key']:
                    return {
                        'success': False,
                        'message': '请先配置阿里云百炼API密钥'
                    }

                # 设置API密钥
                self.dashscope_service = DashScopeService(dashscope_config['api_key'])
                model_name = dashscope_config.get('model', 'qwen-turbo')

            elif ai_model == 'inodetree':
                inodetree_config = self.config_service.get_inodetree_config()
                logger.info(f"InodeTree配置检查: api_key={'已设置' if inodetree_config.get('api_key') else '未设置'}")
                if not inodetree_config['api_key']:
                    return {'success': False, 'message': '请先配置 InodeTree API Key'}
                self.inodetree_service.set_api_key(inodetree_config['api_key'])
                model_name = inodetree_config.get('model', 'inodetree-2.0-flash')

            else:
                return {
                    'success': False,
                    'message': f'不支持的AI模型: {ai_model}'
                }

            # 新增：接收前端传递的字数、配图数量和格式模板"""

if OLD1 in ctrl:
    ctrl = ctrl.replace(OLD1, NEW1, 1)
    print("✓ 修复1：配置检查加 inodetree 分支")
else:
    print("✗ 修复1 未匹配，打印关键段落调试：")
    # 输出第 185-205 行
    for i, l in enumerate(ctrl.split('\n')[184:205], 185):
        print(f"  {i}: {repr(l)}")

# ── 修复2：generate_article_content 调用加 inodetree 分支 ──
OLD2 = """            elif ai_model == 'dashscope':
                content = self.dashscope_service.generate_article_content(title,
 model_name, word_count, format_template=format_template)
            else:
                return {
                    'success': False,
                    'message': f'不支持的AI模型: {ai_model}'
                }"""

NEW2 = """            elif ai_model == 'dashscope':
                content = self.dashscope_service.generate_article_content(title,
 model_name, word_count, format_template=format_template)
            elif ai_model == 'inodetree':
                content = self.inodetree_service.generate_article_content(title, model_name, word_count, format_template=format_template)
            else:
                return {
                    'success': False,
                    'message': f'不支持的AI模型: {ai_model}'
                }"""

if OLD2 in ctrl:
    ctrl = ctrl.replace(OLD2, NEW2, 1)
    print("✓ 修复2：generate_article_content 加 inodetree 分支")
else:
    print("✗ 修复2 未匹配，打印关键段落调试：")
    for i, l in enumerate(ctrl.split('\n')[213:226], 214):
        print(f"  {i}: {repr(l)}")

open(ctrl_path, 'w', encoding='utf-8').write(ctrl)

import ast
try:
    ast.parse(ctrl)
    print("✓ 语法检查通过")
except SyntaxError as e:
    print(f"✗ 语法错误: {e}")
