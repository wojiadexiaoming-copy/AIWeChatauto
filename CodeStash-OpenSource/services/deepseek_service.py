"""
DeepSeek AI服务模块
处理DeepSeek AI相关操作
"""

import os
import logging
import requests
from datetime import datetime
from typing import Optional, Dict, Any
from config.app_config import AppConfig
from services.prompt_manager import PromptManager

logger = logging.getLogger(__name__)

class DeepSeekService:
    """DeepSeek AI服务类"""
    
    def __init__(self):
        self.api_base_url = "https://api.deepseek.com/v1"
        self.default_model = AppConfig.DEEPSEEK_DEFAULT_MODEL
        logger.info("DeepSeek服务初始化完成")
    
    def _get_headers(self) -> Dict[str, str]:
        """获取请求头"""
        api_key = os.environ.get("DEEPSEEK_API_KEY")
        if not api_key:
            raise ValueError("未设置DEEPSEEK_API_KEY环境变量")
        
        return {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
    
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
            headers = self._get_headers()
            logger.info(f"开始生成内容，使用模型: {model}")

            payload = {
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 4000,
                "temperature": 0.7
            }

            response = requests.post(
                f"{self.api_base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=AppConfig.API_TIMEOUT
            )

            if response.status_code == 200:
                result = response.json()
                tokens_used = result.get('usage', {}).get('total_tokens', 0) or 0
                if result.get('choices') and len(result['choices']) > 0:
                    content = result['choices'][0]['message']['content'].strip()
                    logger.info(f"内容生成成功，长度: {len(content)} 字符，token: {tokens_used}")
                    return content, tokens_used
                else:
                    logger.error("内容生成失败，响应格式异常")
                    return None, 0
            else:
                logger.error(f"API请求失败，状态码: {response.status_code}, 响应: {response.text}")
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
        
        # 截取内容前800字符用于生成摘要
        content_preview = self._clean_html_content(content[:800]) if content else ""
        
        prompt = PromptManager.digest_prompt(title, content_preview)
        digest = self.generate_content(prompt, model)
        
        if digest:
            # 限制摘要长度
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
        测试DeepSeek AI连接
        :param model: 模型名称
        :return: 测试结果
        """
        logger.info("开始测试DeepSeek AI连接")
        
        try:
            test_content = self.generate_content("请说'测试成功'", model)
            
            if test_content and "测试成功" in test_content:
                logger.info("DeepSeek AI连接测试成功")
                return {
                    'success': True,
                    'message': 'DeepSeek AI连接成功',
                    'data': {
                        'response': test_content,
                        'model': model or self.default_model
                    }
                }
            else:
                logger.error("DeepSeek AI连接测试失败")
                return {
                    'success': False,
                    'message': 'DeepSeek AI连接失败，请检查API密钥'
                }
                
        except Exception as e:
            error_msg = str(e)
            logger.error(f"测试DeepSeek AI连接时发生错误: {error_msg}")
            
            # 特殊处理API密钥错误
            if "401" in error_msg or "UNAUTHORIZED" in error_msg:
                return {
                    'success': False,
                    'message': 'API密钥无效，请检查您的DeepSeek API密钥是否正确',
                    'error_type': 'invalid_key'
                }
            # 特殊处理配额错误
            elif "429" in error_msg or "RATE_LIMIT" in error_msg:
                return {
                    'success': False,
                    'message': 'API配额已用完，请检查您的DeepSeek API配额或等待配额重置',
                    'error_type': 'quota_exceeded',
                    'details': '当前模型可能已达到配额限制，建议升级API计划'
                }
            # 其他错误
            else:
                return {
                    'success': False,
                    'message': f'DeepSeek AI连接测试失败: {error_msg}'
                }
    
    def set_api_key(self, api_key: str):
        """
        设置API密钥
        :param api_key: API密钥
        """
        os.environ["DEEPSEEK_API_KEY"] = api_key
        logger.info("DeepSeek API密钥已更新")
    
    def get_available_models(self) -> list:
        """获取可用的模型列表"""
        try:
            headers = self._get_headers()
            logger.info("开始获取DeepSeek可用模型列表")
            
            response = requests.get(
                f"{self.api_base_url}/models",
                headers=headers,
                timeout=AppConfig.API_TIMEOUT
            )
            
            logger.info(f"DeepSeek API响应状态码: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"DeepSeek API响应内容: {result}")
                
                models = []
                for model in result.get('data', []):
                    model_id = model.get('id', '')
                    logger.info(f"发现模型: {model_id}")
                    # 包含所有deepseek相关模型
                    if 'deepseek' in model_id.lower():
                        models.append(model_id)
                
                logger.info(f"找到 {len(models)} 个DeepSeek模型: {models}")
                return models
                
            else:
                logger.error(f"获取模型列表失败，状态码: {response.status_code}, 响应: {response.text}")
                # API获取失败时返回空列表
                return []
                
        except Exception as e:
            logger.error(f"获取可用模型列表时发生错误: {str(e)}")
            # API获取失败时返回空列表
            return []
    
    def get_api_info(self) -> Dict[str, Any]:
        """获取API详细信息，用于调试"""
        try:
            headers = self._get_headers()
            logger.info("获取DeepSeek API详细信息")
            
            response = requests.get(
                f"{self.api_base_url}/models",
                headers=headers,
                timeout=AppConfig.API_TIMEOUT
            )
            
            return {
                'status_code': response.status_code,
                'headers': dict(response.headers),
                'content': response.text,
                'json': response.json() if response.status_code == 200 else None
            }
            
        except Exception as e:
            logger.error(f"获取API信息时发生错误: {str(e)}")
            return {
                'error': str(e)
            }