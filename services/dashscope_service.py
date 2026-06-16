import os
import sys
import json
import logging
from datetime import datetime
from typing import List, Dict, Optional
from openai import OpenAI
import requests
from services.prompt_manager import PromptManager

logger = logging.getLogger(__name__)

class DashScopeService:
    """阿里云百炼服务类"""
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("DASHSCOPE_API_KEY")
        self.base_url = "https://dashscope.aliyuncs.com/compatible-mode/v1"
        self.client = None
        
    def _get_client(self) -> Optional[OpenAI]:
        """获取OpenAI客户端"""
        if not self.api_key:
            logger.error("阿里云百炼API密钥未配置")
            return None
            
        try:
            self.client = OpenAI(
                api_key=self.api_key,
                base_url=self.base_url
            )
            return self.client
        except Exception as e:
            logger.error(f"创建阿里云百炼客户端失败: {e}")
            return None
    
    def get_models(self) -> List[Dict]:
        """获取阿里云百炼模型列表 - 优先使用兼容模式API获取完整列表"""
        try:
            if not self.api_key:
                logger.error("API密钥未配置，无法获取模型列表")
                return []
            
            # 优先使用兼容模式API，因为它返回更完整的模型列表
            logger.info("尝试使用OpenAI兼容模式获取模型列表")
            client = self._get_client()
            if client:
                try:
                    # 调用阿里云百炼的模型列表API
                    response = client.models.list()
                    logger.info(f"兼容模式API返回模型数量: {len(response.data) if response.data else 0}")

                    models = []
                    if response.data:
                        for model in response.data:
                            # 过滤掉非标准的模型ID
                            if self._is_valid_model_id(model.id):
                                model_info = {
                                    "id": model.id,
                                    "name": model.id,
                                    "description": f"{model.id} 模型",
                                    "provider": self._get_model_provider(model.id),
                                    "created": getattr(model, 'created', None),
                                    "object": getattr(model, 'object', 'model')
                                }
                                models.append(model_info)

                    if models:
                        logger.info(f"成功从兼容模式获取到 {len(models)} 个有效模型")
                        return models

                except Exception as compat_error:
                    logger.error(f"兼容模式API获取模型列表失败: {compat_error}")

            # 如果兼容模式失败，尝试官方SDK
            try:
                logger.info("尝试导入dashscope模块")
                import dashscope
                logger.info(f"dashscope模块导入成功，模块路径: {dashscope.__file__}")

                # 尝试使用dashscope的Models API
                try:
                    from dashscope import Models
                    logger.info("Models类导入成功")

                    # 获取模型列表
                    response = Models.list(api_key=self.api_key)
                    logger.info(f"Models API响应: {response}")

                    all_models = []
                    if response and hasattr(response, 'output') and response.output:
                        model_list = response.output.get('models', [])
                        total = response.output.get('total', 0)
                        logger.info(f"API返回总数: {total}, 当前页模型数: {len(model_list)}")

                        all_models.extend(model_list)

                    models = []
                    for model in all_models:
                        model_info = {
                            "id": model.get('name', ''),  # 使用name字段作为model_id
                            "name": model.get('name', ''),
                            "description": model.get('description', ''),
                            "provider": self._get_model_provider(model.get('name', '')),
                            "created": model.get('create_time', None),
                            "object": "model"
                        }
                        models.append(model_info)
                        logger.info(f"发现模型: {model.get('name', '')}")

                    if models:
                        logger.info(f"成功从Models API获取到 {len(models)} 个模型")
                    return models

                except Exception as models_error:
                    logger.error(f"Models API获取模型列表失败: {models_error}")

            except ImportError as import_error:
                logger.error(f"DashScope SDK导入失败: {import_error}")
                logger.error("请确保已安装dashscope: pip install dashscope")
                logger.error(f"Python路径: {sys.path}")

            # 如果所有方法都失败，使用默认模型列表
            logger.warning("所有API获取模型列表失败，使用默认模型列表")
            return self._get_default_models()
                
        except Exception as e:
            logger.error(f"获取阿里云百炼模型列表失败: {e}")
            return self._get_default_models()
    
    def _is_valid_model_id(self, model_id: str) -> bool:
        """检查模型ID是否有效（过滤掉奇怪的模型ID）"""
        # 定义有效的模型前缀
        valid_prefixes = [
            "qwen", "deepseek", "baichuan", "yi", "llama", "chatglm", 
            "internlm", "black-forest", "dbrx", "minimax", "stable-code"
        ]
        
        # 过滤掉明显无效的模型ID
        invalid_patterns = [
            "qvq",  # 过滤掉qvq开头的模型
        ]
        
        # 检查是否包含无效模式
        for pattern in invalid_patterns:
            if pattern in model_id.lower():
                logger.info(f"过滤掉无效模型ID: {model_id}")
                return False
        
        # 检查是否有有效前缀
        for prefix in valid_prefixes:
            if model_id.lower().startswith(prefix):
                return True
        
        # 如果没有匹配的有效前缀，也过滤掉
        logger.info(f"过滤掉未知前缀的模型ID: {model_id}")
        return False
    
    def _get_default_models(self) -> List[Dict]:
        """获取默认的阿里云百炼模型列表"""
        return [
            {"id": "qwen-turbo", "name": "qwen-turbo", "description": "通义千问-Turbo", "provider": "阿里云", "object": "model"},
            {"id": "qwen-plus", "name": "qwen-plus", "description": "通义千问-Plus", "provider": "阿里云", "object": "model"},
            {"id": "qwen-max", "name": "qwen-max", "description": "通义千问-Max", "provider": "阿里云", "object": "model"},
            {"id": "qwen-omni-turbo", "name": "qwen-omni-turbo", "description": "通义千问-Omni-Turbo", "provider": "阿里云", "object": "model"},
            {"id": "qwen2.5-7b-instruct", "name": "qwen2.5-7b-instruct", "description": "通义千问2.5-7B指令版", "provider": "阿里云", "object": "model"},
            {"id": "qwen2.5-14b-instruct", "name": "qwen2.5-14b-instruct", "description": "通义千问2.5-14B指令版", "provider": "阿里云", "object": "model"},
            {"id": "qwen2.5-32b-instruct", "name": "qwen2.5-32b-instruct", "description": "通义千问2.5-32B指令版", "provider": "阿里云", "object": "model"},
            {"id": "qwen2.5-72b-instruct", "name": "qwen2.5-72b-instruct", "description": "通义千问2.5-72B指令版", "provider": "阿里云", "object": "model"},
        ]
    

    

    
    def _get_model_provider(self, model_id: str) -> str:
        """获取模型提供商"""
        provider_mapping = {
            "qwen": "阿里云",
            "deepseek": "DeepSeek",
            "baichuan": "百川智能",
            "yi": "季一万物",
            "llama": "Meta",
            "chatglm": "智谱AI",
            "internlm": "上海AI实验室",
            "black-forest": "Black Forest Labs",
            "dbrx": "Databricks",
            "minimax": "MiniMax",
            "stable-code": "Stability AI"
        }
        
        for prefix, provider in provider_mapping.items():
            if model_id.startswith(prefix):
                return provider
        return "其他"
    
    def test_connection(self, model: str = "qwen-turbo") -> Dict:
        """测试阿里云百炼连接"""
        try:
            client = self._get_client()
            if not client:
                return {
                    "success": False,
                    "message": "API密钥未配置或客户端创建失败"
                }
            
            # 测试连接
            completion = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": "你好"}],
                max_tokens=50,
                stream=False
            )
            
            if completion.choices and completion.choices[0].message:
                return {
                    "success": True,
                    "message": "连接成功",
                    "response": completion.choices[0].message.content
                }
            else:
                return {
                    "success": False,
                    "message": "连接成功但未收到有效响应"
                }
                
        except Exception as e:
            error_msg = str(e)
            logger.error(f"阿里云百炼连接测试失败: {error_msg}")
            
            # 根据错误类型提供更友好的提示
            if "api_key" in error_msg.lower() or "authentication" in error_msg.lower():
                return {
                    "success": False,
                    "message": "API密钥无效或已过期"
                }
            elif "quota" in error_msg.lower() or "limit" in error_msg.lower():
                return {
                    "success": False,
                    "message": "API配额已用完，请稍后重试或升级套餐"
                }
            elif "model" in error_msg.lower():
                return {
                    "success": False,
                    "message": f"模型 {model} 不存在或无权限访问"
                }
            else:
                return {
                    "success": False,
                    "message": f"连接失败: {error_msg}"
                }
    
    def generate_content(self, prompt: str, model: str = "qwen-turbo", max_tokens: int = 1000) -> Dict:
        """生成内容，返回 dict（兼容旧接口）"""
        try:
            client = self._get_client()
            if not client:
                return {"success": False, "message": "API密钥未配置或客户端创建失败"}

            completion = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                stream=False
            )

            if completion.choices and completion.choices[0].message:
                usage = completion.usage.dict() if completion.usage else None
                return {
                    "success": True,
                    "content": completion.choices[0].message.content,
                    "usage": usage
                }
            else:
                return {"success": False, "message": "生成失败，未收到有效响应"}

        except Exception as e:
            logger.error(f"阿里云百炼内容生成失败: {e}")
            return {"success": False, "message": f"生成失败: {str(e)}"}

    def generate_with_usage(self, prompt: str, model: str = "qwen-turbo", max_tokens: int = 1000) -> tuple:
        """生成内容，返回 (text, tokens_used)"""
        result = self.generate_content(prompt, model, max_tokens)
        if result.get('success'):
            tokens_used = (result.get('usage') or {}).get('total_tokens', 0) or 0
            return result['content'], tokens_used
        return None, 0
    
    def generate_article_content(self, title: str, model: str = "qwen-turbo", word_count: int = None, format_template: str = '') -> str:
        """
        生成公众号文章内容，支持自定义格式模板
        :param title: 文章标题
        :param model: AI模型
        :param word_count: 目标字数
        :param format_template: 用户自定义的HTML格式模板
        :return: 文章内容
        """
        try:
            char_limit = 20000
            prompt = PromptManager.article_prompt(title, word_count, char_limit, format_template=format_template)
            result = self.generate_content(prompt, model, max_tokens=4000)
            if result['success']:
                return result['content']
            else:
                logger.error(f"文章内容生成失败: {result['message']}")
                return None
        except Exception as e:
            logger.error(f"生成文章内容时发生错误: {e}")
            return None
    
    def generate_digest(self, title: str, content: str, model: str = "qwen-turbo") -> str:
        """
        生成文章摘要
        :param title: 文章标题
        :param content: 文章内容
        :param model: 模型名称
        :return: 文章摘要
        """
        try:
            logger.info(f"开始生成文章摘要，标题: {title}")
            
            # 截取内容前800字符用于生成摘要
            content_preview = self._clean_html_content(content[:800]) if content else ""
            
            prompt = PromptManager.digest_prompt(title, content_preview)
            result = self.generate_content(prompt, model, max_tokens=200)
            
            if result['success']:
                digest = result['content']
                # 限制摘要长度
                if len(digest) > 120:
                    digest = digest[:100] + "..."
                logger.info(f"文章摘要生成成功: {digest}")
                return digest
            else:
                default_digest = f"探索{title}的深度解析，获取独特见解和实用价值。"
                logger.warning(f"摘要生成失败，使用默认摘要: {default_digest}")
                return default_digest
                
        except Exception as e:
            logger.error(f"生成摘要时发生错误: {e}")
            default_digest = f"探索{title}的深度解析，获取独特见解和实用价值。"
            return default_digest
    
    def _clean_html_content(self, content: str) -> str:
        """清理HTML内容，提取纯文本"""
        import re
        # 移除HTML标签
        clean_text = re.sub(r'<[^>]+>', '', content)
        # 移除多余空白
        clean_text = re.sub(r'\s+', ' ', clean_text).strip()
        return clean_text
    
    def get_api_info(self) -> Dict:
        """获取API详细信息（用于调试）"""
        try:
            if not self.api_key:
                return {
                    "success": False,
                    "message": "API密钥未配置",
                    "api_info": {
                        "has_api_key": False,
                        "base_url": self.base_url
                    }
                }
            
            client = self._get_client()
            if not client:
                return {
                    "success": False,
                    "message": "无法创建客户端",
                    "api_info": {
                        "has_api_key": True,
                        "base_url": self.base_url,
                        "client_created": False
                    }
                }
            
            # 尝试获取模型列表
            try:
                response = client.models.list()
                models_data = []
                if response.data:
                    for model in response.data:
                        models_data.append({
                            "id": model.id,
                            "object": getattr(model, 'object', 'model'),
                            "created": getattr(model, 'created', None),
                            "owned_by": getattr(model, 'owned_by', None)
                        })
                
                return {
                    "success": True,
                    "message": "API信息获取成功",
                    "api_info": {
                        "has_api_key": True,
                        "base_url": self.base_url,
                        "client_created": True,
                        "models_count": len(models_data),
                        "models": models_data,
                        "response_type": type(response).__name__,
                        "response_attributes": dir(response)
                    }
                }
                
            except Exception as api_error:
                return {
                    "success": False,
                    "message": f"API调用失败: {str(api_error)}",
                    "api_info": {
                        "has_api_key": True,
                        "base_url": self.base_url,
                        "client_created": True,
                        "error": str(api_error),
                        "error_type": type(api_error).__name__
                    }
                }
                
        except Exception as e:
            return {
                "success": False,
                "message": f"获取API信息失败: {str(e)}",
                "api_info": {
                    "error": str(e),
                    "error_type": type(e).__name__
                }
            } 