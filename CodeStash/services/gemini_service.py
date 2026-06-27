
"""
Gemini AI服务模块
处理Google Gemini AI相关操作
"""

import os
import logging
from datetime import datetime
from typing import Optional, Dict, Any
from google import genai
from google.genai import types
from config.app_config import AppConfig
from services.prompt_manager import PromptManager

logger = logging.getLogger(__name__)

class GeminiService:
    """Gemini AI服务类"""
    
    def __init__(self):
        self.client = None
        self.default_model = AppConfig.GEMINI_DEFAULT_MODEL
        self.image_model = AppConfig.GEMINI_IMAGE_MODEL
        logger.info("Gemini服务初始化完成")
    
    def _get_client(self) -> genai.Client:
        """获取Gemini客户端"""
        if not self.client:
            api_key = os.environ.get("GEMINI_API_KEY")
            if not api_key:
                raise ValueError("未设置GEMINI_API_KEY环境变量")
            
            self.client = genai.Client(api_key=api_key)
            logger.info("Gemini客户端创建成功")
        
        return self.client
    
    def generate_content(self, prompt: str, model: str = None) -> Optional[str]:
        """
        生成内容
        :param prompt: 提示词
        :param model: 模型名称
        :return: 生成的内容
        """
        text, _ = self.generate_with_usage(prompt, model)
        return text

    def generate_with_usage(self, prompt: str, model: str = None) -> tuple:
        """
        生成内容并返回 token 用量
        :return: (text, tokens_used)
        """
        if not model:
            model = self.default_model

        try:
            client = self._get_client()
            logger.info(f"开始生成内容，使用模型: {model}")

            response = client.models.generate_content(
                model=model,
                contents=prompt
            )

            tokens_used = 0
            try:
                meta = response.usage_metadata
                if meta:
                    tokens_used = (getattr(meta, 'total_token_count', 0) or
                                   (getattr(meta, 'prompt_token_count', 0) +
                                    getattr(meta, 'candidates_token_count', 0)))
            except Exception:
                pass

            if response and response.text:
                content = response.text.strip()
                logger.info(f"内容生成成功，长度: {len(content)} 字符，token: {tokens_used}")
                return content, tokens_used
            else:
                logger.error("内容生成失败，响应为空")
                return None, 0

        except Exception as e:
            logger.error(f"生成内容时发生错误: {str(e)}")
            return None, 0
    
    def generate_article_content(self, title: str, model: str = None, word_count: int = None, format_template: str = '') -> Optional[str]:
        """
        生成公众号文章内容，支持自定义格式模板
        :param title: 文章标题
        :param model: AI模型
        :param word_count: 目标字数
        :param format_template: 用户自定义的HTML格式模板
        :return: 文章内容
        """
        char_limit = 20000
        prompt = PromptManager.article_prompt(title, word_count, char_limit, format_template=format_template)
        content = self.generate_content(prompt, model)
        if content:
            logger.info("文章内容生成成功")
            return content
        else:
            logger.error("文章内容生成失败")
            return None
    
    def generate_digest(self, title: str, content: str, model: str = None) -> str:
        """
        生成文章摘要
        :param title: 文章标题
        :param content: 文章内容
        :param model: 模型名称
        :return: 文章摘要
        """
        logger.info(f"开始生成文章摘要，标题: {title}")
        content_preview = self._clean_html_content(content[:800]) if content else ""
        prompt = PromptManager.digest_prompt(title, content_preview)
        digest = self.generate_content(prompt, model)
        if digest:
            if len(digest) > 120:
                digest = digest[:100] + "..."
            logger.info(f"文章摘要生成成功: {digest}")
            return digest
        else:
            default_digest = f"探索{title}的深度解析，获取独特见解和实用价值。"
            logger.warning(f"摘要生成失败，使用默认摘要: {default_digest}")
            return default_digest
    
    def _clean_html_content(self, html_content: str) -> str:
        """清理HTML内容，提取纯文本"""
        import re
        # 移除HTML标签
        clean_text = re.sub(r'<[^>]+>', '', html_content)
        # 移除多余空白
        clean_text = re.sub(r'\s+', ' ', clean_text)
        return clean_text.strip()
    
    def test_connection(self, model: str = None) -> Dict[str, Any]:
        """
        测试Gemini AI连接
        :param model: 模型名称
        :return: 测试结果
        """
        logger.info("开始测试Gemini AI连接")
        
        try:
            test_content = self.generate_content("请说'测试成功'", model)
            
            if test_content and "测试成功" in test_content:
                logger.info("Gemini AI连接测试成功")
                return {
                    'success': True,
                    'message': 'Gemini AI连接成功',
                    'data': {
                        'response': test_content,
                        'model': model or self.default_model
                    }
                }
            else:
                logger.error("Gemini AI连接测试失败")
                return {
                    'success': False,
                    'message': 'Gemini AI连接失败，请检查API密钥'
                }
                
        except Exception as e:
            error_msg = str(e)
            logger.error(f"测试Gemini AI连接时发生错误: {error_msg}")
            
            # 特殊处理429错误（配额超限）
            if "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg:
                return {
                    'success': False,
                    'message': 'API配额已用完，请检查您的Gemini API配额或等待配额重置',
                    'error_type': 'quota_exceeded',
                    'details': '当前模型可能已达到每日免费配额限制，建议切换到其他模型或升级API计划'
                }
            # 特殊处理API密钥错误
            elif "401" in error_msg or "UNAUTHENTICATED" in error_msg:
                return {
                    'success': False,
                    'message': 'API密钥无效，请检查您的Gemini API密钥是否正确',
                    'error_type': 'invalid_key'
                }
            # 其他错误
            else:
                return {
                    'success': False,
                    'message': f'Gemini AI连接测试失败: {error_msg}'
                }
    
    def set_api_key(self, api_key: str):
        """
        设置API密钥
        :param api_key: API密钥
        """
        os.environ["GEMINI_API_KEY"] = api_key
        # 重置客户端，强制使用新密钥
        self.client = None
        logger.info("Gemini API密钥已更新")
    
    def get_available_models(self) -> list:
        """获取可用的模型列表"""
        try:
            client = self._get_client()
            logger.info("开始获取可用模型列表")
            
            # 使用Google GenAI API获取模型列表
            models = client.models.list()
            
            # 过滤出Gemini模型
            gemini_models = []
            for model in models:
                model_name = model.name
                if 'gemini' in model_name.lower():
                    # 提取模型名称（去掉models/前缀）
                    if '/' in model_name:
                        model_name = model_name.split('/')[-1]
                    gemini_models.append(model_name)
            
            logger.info(f"获取到 {len(gemini_models)} 个可用模型: {gemini_models}")
            return gemini_models
            
        except Exception as e:
            logger.error(f"获取可用模型列表时发生错误: {str(e)}")
            # API获取失败时返回空列表
            return []
    
    def _format_content_as_html(self, content: str) -> str:
        """
        将纯文本内容格式化为HTML
        :param content: 纯文本内容
        :return: HTML格式内容
        """
        try:
            logger.info("正在将内容格式化为HTML")
            
            # 按行分割
            lines = content.split('\n')
            html_lines = []
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                    
                # 检测标题
                if line.startswith('# '):
                    html_lines.append(f'<h2>{line[2:]}</h2>')
                elif line.startswith('## '):
                    html_lines.append(f'<h3>{line[3:]}</h3>')
                elif line.startswith('- '):
                    # 简单的列表项处理
                    if not html_lines or not html_lines[-1].startswith('<ul>'):
                        html_lines.append('<ul>')
                    html_lines.append(f'<li>{line[2:]}</li>')
                else:
                    # 关闭未关闭的列表
                    if html_lines and html_lines[-1].startswith('<li>'):
                        html_lines.append('</ul>')
                    # 普通段落
                    html_lines.append(f'<p>{line}</p>')
            
            # 关闭可能未关闭的列表
            if html_lines and html_lines[-1].startswith('<li>'):
                html_lines.append('</ul>')
            
            formatted_content = '\n'.join(html_lines)
            logger.info("内容HTML格式化完成")
            
            return formatted_content
            
        except Exception as e:
            logger.error(f"HTML格式化时发生错误: {str(e)}")
            return f'<p>{content}</p>'  # fallback