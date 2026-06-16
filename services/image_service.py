
"""
图像服务模块
处理图像生成和处理相关操作
"""

import os
import logging
import requests
from datetime import datetime
from typing import Optional, Dict, Any
from google import genai
from google.genai import types
from config.app_config import AppConfig
from services.prompt_manager import PromptManager

logger = logging.getLogger(__name__)

class ImageService:
    """图像服务类"""
    
    def __init__(self):
        self.client = None
        self.image_model = AppConfig.GEMINI_IMAGE_MODEL
        self.cache_folder = AppConfig.CACHE_FOLDER
        logger.info("图像服务初始化完成")
    
    def _get_gemini_client(self) -> genai.Client:
        """获取Gemini客户端"""
        if not self.client:
            api_key = os.environ.get("GEMINI_API_KEY")
            if not api_key:
                raise ValueError("未设置GEMINI_API_KEY环境变量")
            
            self.client = genai.Client(api_key=api_key)
            logger.info("Gemini客户端创建成功")
        
        return self.client
    
    def generate_article_image(self, title: str, description: str = "", image_model: str = "gemini", 
                             article_content: str = "", ai_model: str = "gemini", 
                             image_index: int = 1, total_images: int = 1,
                             dashscope_params: dict = None,
                             user_custom_prompt: str = "") -> Optional[str]:
        """
        生成文章配图
        :param title: 文章标题
        :param description: 文章描述
        :param image_model: 生图模型 (gemini, deepseek, dashscope, pexels)
        :param article_content: 文章内容（用于Pexels搜索的AI提示词生成）
        :param ai_model: AI模型 (gemini, deepseek, dashscope) - 用于Pexels搜索提示词生成
        :param image_index: 当前图片索引（从1开始）
        :param total_images: 总图片数量
        :param dashscope_params: dict，阿里云百炼生图专用参数
        :param user_custom_prompt: str，用户自定义生图提示词
        :return: 图片文件路径
        """
        try:
            logger.info(f"开始生成文章配图，标题: {title}, 生图模型: {image_model}, AI模型: {ai_model}, 图片索引: {image_index}/{total_images}")
            # 推荐逻辑：阿里云百炼/Coze如无正向提示词和自定义提示词，则用PromptManager.image_prompt生成完整提示词
            if image_model in ["dashscope", "coze"]:
                # 优先用用户输入
                final_prompt = user_custom_prompt or (dashscope_params.get('positive_prompt') if dashscope_params else None)
                if not final_prompt:
                    final_prompt = PromptManager.image_prompt_with_style(title, description, user_custom_prompt)
            else:
                final_prompt = PromptManager.image_prompt_with_style(title, description, user_custom_prompt)
            if image_model == "gemini":
                return self._generate_with_gemini(final_prompt)
            elif image_model == "deepseek":
                return self._generate_with_deepseek(final_prompt)
            elif image_model == "dashscope":
                # 新增：支持 dashscope_params，正向提示词用统一拼接
                if dashscope_params is None:
                    dashscope_params = {}
                dashscope_params['positive_prompt'] = final_prompt
                return self._generate_with_dashscope_v2(title, description, dashscope_params)
            elif image_model == "pexels":
                return self._search_with_pexels(title, description, article_content, ai_model, 
                                              image_index=image_index, total_images=total_images)
            elif image_model == "coze":
                return self._generate_with_coze(final_prompt)
            elif image_model == "inodetree":
                # InodeTree Image 直接生图
                return self._generate_with_inodetree_image(final_prompt)
            else:
                logger.error(f"不支持的生图模型: {image_model}")
                return None
        except Exception as e:
            logger.error(f"生成文章配图时发生错误: {str(e)}")
            return None
    
    def _generate_with_gemini(self, title: str, description: str = "") -> Optional[str]:
        """使用Gemini生成图片"""
        try:
            client = self._get_gemini_client()
            
            # 生成图片提示词
            image_prompt = PromptManager.image_prompt(title, description)
            
            # 生成文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"article_gemini_{timestamp}.jpg"
            image_path = os.path.join(self.cache_folder, filename)
            
            logger.debug(f"Gemini图片保存路径: {image_path}")
            
            response = client.models.generate_content(
                model=AppConfig.GEMINI_IMAGE_MODEL,
                contents=image_prompt,
                config=types.GenerateContentConfig(
                    response_modalities=['TEXT', 'IMAGE']
                )
            )
            
            if not response.candidates:
                logger.error("Gemini图片生成失败，无候选结果")
                return None
            
            content = response.candidates[0].content
            if not content or not content.parts:
                logger.error("Gemini图片生成失败，无内容部分")
                return None
            
            # 查找并保存图片数据
            image_saved = False
            for part in content.parts:
                if part.text:
                    logger.info(f"Gemini图片生成描述: {part.text}")
                elif part.inline_data and part.inline_data.data:
                    with open(image_path, 'wb') as f:
                        f.write(part.inline_data.data)
                    logger.info(f"Gemini文章配图生成成功: {image_path}")
                    image_saved = True
                    break
            
            if image_saved:
                return image_path
            else:
                logger.error("Gemini图片生成失败，未找到图片数据")
                return None
            
        except Exception as e:
            logger.error(f"Gemini生成文章配图时发生错误: {str(e)}")
            return None
    
    def _generate_with_deepseek(self, title: str, description: str = "") -> Optional[str]:
        """使用DeepSeek生成图片"""
        try:
            # 这里需要实现DeepSeek的图片生成API调用
            # 由于DeepSeek的图片生成API可能还在开发中，暂时返回None
            logger.warning("DeepSeek图片生成功能暂未实现")
            return None
            
        except Exception as e:
            logger.error(f"DeepSeek生成文章配图时发生错误: {str(e)}")
            return None
    
    def _generate_with_dashscope(self, title: str, description: str = "") -> Optional[str]:
        """使用阿里云百炼生成图片"""
        try:
            # 这里需要实现阿里云百炼的图片生成API调用
            # 由于阿里云百炼的图片生成API可能还在开发中，暂时返回None
            logger.warning("阿里云百炼图片生成功能暂未实现")
            return None
            
        except Exception as e:
            logger.error(f"阿里云百炼生成文章配图时发生错误: {str(e)}")
            return None
    
    def _generate_with_coze(self, title: str, description: str = "") -> Optional[str]:
        """使用Coze工作流API生成图片（非流式）"""
        try:
            from services.config_service import ConfigService
            import requests
            config_service = ConfigService()
            coze_config = config_service.get_coze_config()
            coze_token = coze_config.get('coze_token', '')
            workflow_id = coze_config.get('coze_workflow_id', '')
            if not coze_token:
                logger.error("Coze令牌未配置")
                return None
            if not workflow_id:
                logger.error("Coze工作流ID未配置")
                return None

            # 这里假设workflow_id和参数需要根据实际业务调整
            parameters = {
                "title": title,
                "description": description
            }
            url = "https://api.coze.cn/v1/workflow/run"
            headers = {
                "Authorization": f"Bearer {coze_token}",
                "Content-Type": "application/json"
            }
            payload = {
                "workflow_id": workflow_id,
                "parameters": parameters
            }
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            if response.status_code != 200:
                logger.error(f"Coze API请求失败，状态码: {response.status_code}, 响应: {response.text}")
                return None
            resp_json = response.json()
            if resp_json.get('code') != 0:
                logger.error(f"Coze API返回错误: {resp_json.get('msg')}")
                return None
            # 假设返回的data字段为JSON字符串，包含图片URL
            import json as _json
            data = resp_json.get('data')
            if not data:
                logger.error("Coze API未返回图片数据")
                return None
            try:
                data_obj = _json.loads(data) if isinstance(data, str) else data
            except Exception:
                data_obj = data
            image_url = data_obj.get('image_url') or data_obj.get('url') or data_obj.get('output') or data_obj.get('title') 
            if not image_url:
                logger.error(f"Coze返回数据未包含图片URL: {data_obj}")
                return None
            # 下载图片
            from datetime import datetime
            import os
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).rstrip()[:20]
            filename = f"article_coze_{safe_title}_{timestamp}.jpg"
            image_path = os.path.join(self.cache_folder, filename)
            img_resp = requests.get(image_url, timeout=30)
            if img_resp.status_code == 200:
                with open(image_path, 'wb') as f:
                    f.write(img_resp.content)
                logger.info(f"Coze文章配图生成成功: {image_path}")
                return image_path
            else:
                logger.error(f"Coze图片下载失败，状态码: {img_resp.status_code}")
                return None
        except Exception as e:
            logger.error(f"Coze生成文章配图时发生错误: {str(e)}")
            return None
    
    def _generate_with_dashscope_v2(self, title: str, description: str = "", dashscope_params: dict = None) -> Optional[str]:
        """新版：使用阿里云百炼SDK生成图片，支持正/反向提示词、图片比例、采样步数等参数"""
        try:
            import dashscope
            from dashscope import ImageSynthesis
            from http import HTTPStatus
            from urllib.parse import urlparse, unquote
            from pathlib import PurePosixPath
            # 参数准备
            if not dashscope_params:
                logger.error("未传递阿里云百炼生图参数")
                return None
            model_name = dashscope_params.get('model_name')
            positive_prompt = dashscope_params.get('positive_prompt') or title
            # 默认反向提示词
            negative_prompt = dashscope_params.get('negative_prompt')
            if not negative_prompt:
                negative_prompt = "模糊, 低质量, 扭曲, 失真, 过曝, 过暗, 低分辨率, artifact, blurry, bad anatomy, bad hands, watermark, signature, text, cropped, worst quality, low quality, jpeg artifacts"
            # 默认图片比例
            size = dashscope_params.get('size') or '1024*768'  # 4:3
            # 默认采样步数
            steps = dashscope_params.get('steps')
            if steps is None:
                steps = 25
            num_images = dashscope_params.get('num_images', 1)
            seed = dashscope_params.get('seed')
            guidance_scale = dashscope_params.get('guidance_scale')
            output_dir = self.cache_folder
            api_key = os.environ.get("DASHSCOPE_API_KEY")
            if not api_key:
                logger.error("未设置 DASHSCOPE_API_KEY 环境变量")
                return None
            params = {
                "api_key": api_key,
                "model": model_name,
                "prompt": positive_prompt,
                "n": num_images,
                "size": size,
            }
            if negative_prompt:
                params["negative_prompt"] = negative_prompt
            if steps is not None:
                params["steps"] = steps
            if seed is not None:
                params["seed"] = seed
            if guidance_scale is not None:
                params["guidance"] = guidance_scale
            logger.info(f"DashScope生图参数: {params}")
            try:
                rsp = ImageSynthesis.call(**params)
                logger.info(f"DashScope同步调用响应: {rsp}")
                if rsp.status_code == HTTPStatus.OK:
                    if not os.path.exists(output_dir):
                        os.makedirs(output_dir)
                    downloaded_urls = []
                    for result in rsp.output.results:
                        file_name = PurePosixPath(unquote(urlparse(result.url).path)).parts[-1]
                        file_path = os.path.join(output_dir, file_name)
                        try:
                            with open(file_path, 'wb+') as f:
                                f.write(requests.get(result.url).content)
                            logger.info(f"图片已保存到: {file_path}")
                            downloaded_urls.append(file_path)
                        except Exception as e:
                            logger.error(f"下载图片 {result.url} 失败: {e}")
                    if downloaded_urls:
                        return downloaded_urls[0]  # 只返回第一张
                    else:
                        logger.error("DashScope图片下载失败")
                        return None
                else:
                    logger.error(f"DashScope同步调用失败, 状态码: {rsp.status_code}, 错误码: {getattr(rsp, 'code', None)}, 消息: {getattr(rsp, 'message', None)}")
                    return None
            except Exception as e:
                logger.error(f"DashScope同步调用发生异常: {e}")
                return None
        except Exception as e:
            logger.error(f"阿里云百炼生成文章配图时发生错误: {str(e)}")
            return None
    
    def _search_with_pexels(self, title: str, description: str = "", article_content: str = "", ai_model: str = "gemini",
                           orientation: str = "landscape", size: str = "large", 
                           per_page: int = 5, image_index: int = 1, total_images: int = 1) -> Optional[str]:
        """
        使用Pexels搜索图片
        :param title: 文章标题
        :param description: 文章描述
        :param article_content: 文章内容（用于AI生成搜索提示词）
        :param ai_model: AI模型 (gemini, deepseek, dashscope) - 用于生成搜索提示词
        :param orientation: 图片方向 (landscape, portrait, square)
        :param size: 图片大小 (large, medium, small)
        :param per_page: 每页结果数量
        :param image_index: 当前图片索引（从1开始）
        :param total_images: 总图片数量
        :return: 图片文件路径
        """
        try:
            logger.info(f"开始使用Pexels搜索图片，标题: {title}, AI模型: {ai_model}, 图片索引: {image_index}/{total_images}")
            
            # 获取Pexels API密钥
            from services.config_service import ConfigService
            config_service = ConfigService()
            pexels_config = config_service.get_pexels_config()
            
            if not pexels_config.get('api_key'):
                logger.error("Pexels API密钥未配置")
                return None
            
            pexels_api_key = pexels_config['api_key']
            
            # 使用指定AI模型生成搜索提示词
            search_query = self._generate_pexels_search_query_with_ai(title, description, article_content, ai_model, image_index, total_images)
            
            if not search_query:
                logger.warning("AI生成搜索提示词失败，使用备用关键词")
                search_query = self._build_pexels_search_query(title, description)
            
            # 构建API请求参数
            params = {
                'query': search_query,
                'orientation': orientation,
                'size': size,
                'per_page': per_page,
                'page': 1
            }
            
            headers = {
                'Authorization': pexels_api_key
            }
            
            # 发送API请求
            response = requests.get(
                'https://api.pexels.com/v1/search',
                params=params,
                headers=headers,
                timeout=AppConfig.API_TIMEOUT
            )
            
            logger.info(f"Pexels API响应状态码: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                photos = data.get('photos', [])
                
                if not photos:
                    logger.warning("Pexels搜索未找到相关图片")
                    return None
                
                logger.info(f"Pexels搜索到 {len(photos)} 张图片")
                
                # 随机选择一张图片，避免总是选择第一张
                import random
                if len(photos) > 1:
                    # 如果有多个结果，随机选择（但避免选择第一张，增加多样性）
                    selected_index = random.randint(1, min(len(photos) - 1, 3))  # 在前4张中随机选择（除了第1张）
                else:
                    selected_index = 0
                
                photo = photos[selected_index]
                photo_url = photo.get('src', {}).get('large2x') or photo.get('src', {}).get('large')
                
                if not photo_url:
                    logger.error("Pexels图片URL获取失败")
                    return None
                
                logger.info(f"选择了第{selected_index + 1}张图片（共{len(photos)}张）")
                
                # 下载图片
                image_path = self._download_pexels_image(photo_url, title)
                
                if image_path:
                    logger.info(f"Pexels图片下载成功: {image_path}")
                    return image_path
                else:
                    logger.error("Pexels图片下载失败")
                    return None
                    
            else:
                logger.error(f"Pexels API请求失败，状态码: {response.status_code}, 响应: {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Pexels搜索图片时发生错误: {str(e)}")
            return None
    
    def _generate_pexels_search_query_with_ai(self, title: str, description: str = "", article_content: str = "", ai_model: str = "gemini", image_index: int = 1, total_images: int = 1) -> Optional[str]:
        """
        使用AI生成Pexels搜索提示词
        :param title: 文章标题
        :param description: 文章描述
        :param article_content: 文章内容
        :param ai_model: AI模型 (gemini, deepseek, dashscope)
        :param image_index: 当前图片索引（从1开始）
        :param total_images: 总图片数量
        :return: AI生成的搜索提示词
        """
        try:
            # 构建用于AI分析的文本内容
            analysis_text = title
            if description:
                analysis_text += f"\n描述: {description}"
            if article_content:
                # 提取文章前100字左右的内容用于分析
                content_preview = self._extract_content_preview(article_content, 100)
                analysis_text += f"\n文章内容预览: {content_preview}"
            # 构建AI提示词
            prompt = PromptManager.pexels_search_prompt(analysis_text, image_index, total_images)
            # 根据选择的AI模型调用相应的服务
            if ai_model == "gemini":
                search_query = self._generate_with_gemini_ai(prompt)
            elif ai_model == "deepseek":
                search_query = self._generate_with_deepseek_ai(prompt)
            elif ai_model == "dashscope":
                search_query = self._generate_with_dashscope_ai(prompt)
            elif ai_model == "inodetree":
                search_query = self._generate_with_inodetree_ai(prompt)
            else:
                logger.warning(f"不支持的AI模型: {ai_model}，使用Gemini作为默认")
                search_query = self._generate_with_gemini_ai(prompt)
            if search_query:
                # 清理和验证搜索提示词
                search_query = self._clean_search_query(search_query)
                logger.info(f"使用{ai_model}生成的Pexels搜索提示词: {search_query}")
                return search_query
            else:
                logger.error(f"{ai_model}生成搜索提示词失败")
                return None
        except Exception as e:
            logger.error(f"AI生成Pexels搜索提示词时发生错误: {str(e)}")
            return None
    
    def _extract_content_preview(self, content: str, max_chars: int = 100) -> str:
        """
        提取文章内容预览
        :param content: 文章内容
        :param max_chars: 最大字符数
        :return: 内容预览
        """
        try:
            # 清理HTML标签
            import re
            clean_content = re.sub(r'<[^>]+>', '', content)
            # 移除多余空白
            clean_content = re.sub(r'\s+', ' ', clean_content).strip()
            
            # 截取指定长度
            if len(clean_content) <= max_chars:
                return clean_content
            else:
                # 在合适的位置截断，避免截断单词
                preview = clean_content[:max_chars]
                last_space = preview.rfind(' ')
                if last_space > max_chars * 0.7:  # 如果空格位置合理
                    preview = preview[:last_space]
                return preview + "..."
                
        except Exception as e:
            logger.error(f"提取内容预览时发生错误: {str(e)}")
            return content[:max_chars] if content else ""
    
    def _generate_with_gemini_ai(self, prompt: str) -> Optional[str]:
        """
        使用Gemini AI生成搜索提示词
        :param prompt: AI提示词
        :return: 生成的搜索提示词
        """
        try:
            client = self._get_gemini_client()
            response = client.models.generate_content(
                model=AppConfig.GEMINI_DEFAULT_MODEL,
                contents=prompt
            )
            
            if response and response.text:
                return response.text.strip()
            else:
                logger.error("Gemini AI生成搜索提示词失败，响应为空")
                return None
                
        except Exception as e:
            logger.error(f"Gemini AI生成搜索提示词时发生错误: {str(e)}")
            return None
    
    def _generate_with_deepseek_ai(self, prompt: str) -> Optional[str]:
        """
        使用DeepSeek AI生成搜索提示词
        :param prompt: AI提示词
        :return: 生成的搜索提示词
        """
        try:
            from services.deepseek_service import DeepSeekService
            from services.config_service import ConfigService
            
            config_service = ConfigService()
            deepseek_config = config_service.get_deepseek_config()
            
            if not deepseek_config.get('api_key'):
                logger.error("DeepSeek API密钥未配置")
                return None
            
            deepseek_service = DeepSeekService()
            deepseek_service.set_api_key(deepseek_config['api_key'])
            model_name = deepseek_config.get('model', 'deepseek-chat')
            
            search_query = deepseek_service.generate_content(prompt, model_name)
            return search_query
            
        except Exception as e:
            logger.error(f"DeepSeek AI生成搜索提示词时发生错误: {str(e)}")
            return None
    
    def _generate_with_dashscope_ai(self, prompt: str) -> Optional[str]:
        """
        使用阿里云百炼AI生成搜索提示词
        :param prompt: AI提示词
        :return: 生成的搜索提示词
        """
        try:
            from services.dashscope_service import DashScopeService
            from services.config_service import ConfigService
            
            config_service = ConfigService()
            dashscope_config = config_service.get_dashscope_config()
            
            if not dashscope_config.get('api_key'):
                logger.error("阿里云百炼API密钥未配置")
                return None
            
            dashscope_service = DashScopeService(dashscope_config['api_key'])
            model_name = dashscope_config.get('model', 'qwen-turbo')
            
            result = dashscope_service.generate_content(prompt, model_name, max_tokens=200)
            if result.get('success') and result.get('content'):
                return result['content'].strip()
            else:
                logger.error(f"阿里云百炼生成搜索提示词失败: {result.get('message', '未知错误')}")
                return None
                
        except Exception as e:
            logger.error(f"阿里云百炼AI生成搜索提示词时发生错误: {str(e)}")
            return None
    
    def _generate_with_inodetree_image(self, prompt: str) -> Optional[str]:
        """使用 InodeTree Image 2.1 Flash 生成图片"""
        try:
            from services.inodetree_service import InodeTreeService
            from services.config_service import ConfigService
            config_service = ConfigService()
            inodetree_config = config_service.get_inodetree_config()
            if not inodetree_config.get('api_key'):
                logger.error("InodeTree API Key 未配置，无法生图")
                return None
            inodetree = InodeTreeService(inodetree_config['api_key'])
            return inodetree.generate_image(prompt, size="1024x768", save_dir=self.cache_folder)
        except Exception as e:
            logger.error(f"InodeTree 图片生成失败: {e}")
            return None

    def _generate_with_inodetree_ai(self, prompt: str) -> Optional[str]:
        """使用 InodeTree AI 生成 Pexels 搜索提示词"""
        try:
            from services.inodetree_service import InodeTreeService
            from services.config_service import ConfigService
            config_service = ConfigService()
            inodetree_config = config_service.get_inodetree_config()
            if not inodetree_config.get('api_key'):
                logger.error("InodeTree API Key 未配置")
                return None
            inodetree = InodeTreeService(inodetree_config['api_key'])
            inodetree.model = inodetree_config.get('model', 'inodetree-2.0-flash')
            result = inodetree.generate_content(prompt, max_tokens=100)
            return result
        except Exception as e:
            logger.error(f"InodeTree AI 生成搜索提示词时发生错误: {str(e)}")
            return None

    def _generate_prompt_with_inodetree(self, prompt: str) -> Optional[str]:
        """用 InodeTree 润色生图提示词"""
        try:
            from services.inodetree_service import InodeTreeService
            from services.config_service import ConfigService
            config_service = ConfigService()
            inodetree_config = config_service.get_inodetree_config()
            if not inodetree_config.get('api_key'):
                return prompt
            inodetree = InodeTreeService(inodetree_config['api_key'])
            return inodetree.generate_content(prompt, max_tokens=300) or prompt
        except Exception as e:
            logger.error(f"InodeTree 润色 prompt 失败: {e}")
            return prompt

    def _clean_search_query(self, search_query: str) -> str:
        """
        清理和验证搜索提示词
        :param search_query: 原始搜索提示词
        :return: 清理后的搜索提示词
        """
        try:
            # 移除多余的标点符号和特殊字符
            import re
            cleaned = re.sub(r'[^\w\s]', '', search_query)
            # 移除多余空白
            cleaned = re.sub(r'\s+', ' ', cleaned).strip()
            # 转换为小写
            cleaned = cleaned.lower()
            
            # 验证关键词数量
            keywords = cleaned.split()
            if len(keywords) < 1:
                return "business technology"
            elif len(keywords) > 4:
                cleaned = ' '.join(keywords[:4])
            
            return cleaned
            
        except Exception as e:
            logger.error(f"清理搜索提示词时发生错误: {str(e)}")
            return "business technology"
    
    def _build_pexels_search_query(self, title: str, description: str = "") -> str:
        """
        构建Pexels搜索关键词
        :param title: 文章标题
        :param description: 文章描述
        :return: 搜索关键词
        """
        # 从标题中提取关键词
        keywords = []
        
        # 移除常见的无意义词汇
        stop_words = ['的', '了', '在', '是', '有', '和', '与', '或', '但', '而', '如果', '因为', '所以', '如何', '什么', '为什么', '怎么', '哪些', '这个', '那个', '这些', '那些']
        
        # 简单的关键词提取
        title_words = title.replace('《', '').replace('》', '').replace('：', ' ').replace(':', ' ').split()
        
        for word in title_words:
            if len(word) > 1 and word not in stop_words:
                keywords.append(word)
        
        # 如果关键词太少，添加一些通用词汇
        if len(keywords) < 2:
            keywords.extend(['business', 'technology', 'innovation'])
        
        # 组合搜索关键词
        search_query = ' '.join(keywords[:3])  # 最多使用3个关键词
        
        logger.info(f"Pexels搜索关键词: {search_query}")
        return search_query
    
    def _download_pexels_image(self, image_url: str, title: str) -> Optional[str]:
        """
        下载Pexels图片
        :param image_url: 图片URL
        :param title: 文章标题（用于生成文件名）
        :return: 图片文件路径
        """
        try:
            # 生成文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).rstrip()[:20]
            filename = f"article_pexels_{safe_title}_{timestamp}.jpg"
            image_path = os.path.join(self.cache_folder, filename)
            
            logger.debug(f"Pexels图片保存路径: {image_path}")
            
            # 下载图片
            response = requests.get(image_url, timeout=AppConfig.API_TIMEOUT)
            
            if response.status_code == 200:
                with open(image_path, 'wb') as f:
                    f.write(response.content)
                
                logger.info(f"Pexels图片下载成功: {image_path}")
                return image_path
            else:
                logger.error(f"Pexels图片下载失败，状态码: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"下载Pexels图片时发生错误: {str(e)}")
            return None
    
    def validate_image_file(self, image_path: str) -> bool:
        """
        验证图片文件
        :param image_path: 图片路径
        :return: 验证结果
        """
        try:
            if not os.path.exists(image_path):
                logger.error(f"图片文件不存在: {image_path}")
                return False
            
            file_size = os.path.getsize(image_path)
            if file_size == 0:
                logger.error(f"图片文件为空: {image_path}")
                return False
            
            # 检查文件大小（微信限制10MB）
            max_size = 10 * 1024 * 1024  # 10MB
            if file_size > max_size:
                logger.error(f"图片文件过大: {file_size} bytes, 最大限制: {max_size} bytes")
                return False
            
            logger.info(f"图片文件验证通过: {image_path}, 大小: {file_size} bytes")
            return True
            
        except Exception as e:
            logger.error(f"验证图片文件时发生错误: {str(e)}")
            return False
    
    def get_image_info(self, image_path: str) -> Dict[str, Any]:
        """
        获取图片信息
        :param image_path: 图片路径
        :return: 图片信息
        """
        try:
            if not os.path.exists(image_path):
                return {'exists': False}
            
            file_size = os.path.getsize(image_path)
            file_name = os.path.basename(image_path)
            
            return {
                'exists': True,
                'file_name': file_name,
                'file_size': file_size,
                'file_size_mb': round(file_size / (1024 * 1024), 2),
                'full_path': image_path,
                'relative_path': os.path.relpath(image_path, '.'),
                'created_time': datetime.fromtimestamp(os.path.getctime(image_path)).strftime('%Y-%m-%d %H:%M:%S')
            }
            
        except Exception as e:
            logger.error(f"获取图片信息时发生错误: {str(e)}")
            return {'exists': False, 'error': str(e)}
    
    def cleanup_old_images(self, days: int = 7) -> int:
        """
        清理旧图片文件
        :param days: 保留天数
        :return: 清理的文件数量
        """
        try:
            if not os.path.exists(self.cache_folder):
                return 0
            
            import time
            current_time = time.time()
            cutoff_time = current_time - (days * 24 * 60 * 60)
            
            cleaned_count = 0
            for filename in os.listdir(self.cache_folder):
                if filename.startswith('article_') and filename.endswith('.jpg'):
                    file_path = os.path.join(self.cache_folder, filename)
                    if os.path.getmtime(file_path) < cutoff_time:
                        os.remove(file_path)
                        cleaned_count += 1
                        logger.info(f"删除旧图片: {filename}")
            
            logger.info(f"清理完成，删除了 {cleaned_count} 个旧图片文件")
            return cleaned_count
            
        except Exception as e:
            logger.error(f"清理旧图片时发生错误: {str(e)}")
            return 0
    
    def get_cache_folder_info(self) -> Dict[str, Any]:
        """
        获取缓存文件夹信息
        :return: 文件夹信息
        """
        try:
            if not os.path.exists(self.cache_folder):
                return {'exists': False}
            
            files = []
            total_size = 0
            
            for filename in os.listdir(self.cache_folder):
                file_path = os.path.join(self.cache_folder, filename)
                if os.path.isfile(file_path):
                    file_size = os.path.getsize(file_path)
                    total_size += file_size
                    files.append({
                        'name': filename,
                        'size': file_size,
                        'modified': datetime.fromtimestamp(os.path.getmtime(file_path)).strftime('%Y-%m-%d %H:%M:%S')
                    })
            
            return {
                'exists': True,
                'file_count': len(files),
                'total_size': total_size,
                'total_size_mb': round(total_size / (1024 * 1024), 2),
                'files': files
            }
            
        except Exception as e:
            logger.error(f"获取缓存文件夹信息时发生错误: {str(e)}")
            return {'exists': False, 'error': str(e)}
    
    def _process_images_in_content(self, content: str, title: str, description: str, image_count: int, image_model: str = "gemini", ai_model: str = "gemini", custom_image_prompt: str = "", dashscope_params: dict = None, dashscope_image_model_code: str = "") -> str:
        try:
            logger.info(f"开始处理文章配图，计划生成{image_count}张图片（仅本地路径，不上传微信）")
            paragraphs = content.split('</p>')
            total_paragraphs = len(paragraphs)
            if total_paragraphs < 2 or image_count < 1:
                logger.warning("文章段落过少或配图数量小于1，跳过配图插入")
                return content
            if image_count >= total_paragraphs:
                insert_positions = list(range(1, total_paragraphs))[:image_count]
            else:
                insert_positions = [round((i + 1) * total_paragraphs / (image_count + 1)) for i in range(image_count)]
            logger.info(f"计划在第{insert_positions}段后插入配图")
            generated_images = []
            if dashscope_params is None:
                dashscope_params = {}
            for i, position in enumerate(insert_positions):
                try:
                    logger.info(f"生成第{i+1}张配图，使用模型: {image_model}")
                    # 1. 提取插图位置前100字+后100字内容
                    def extract_paragraph_content(paragraphs, pos, max_chars=100):
                        idx = max(0, pos-1)
                        text_before = paragraphs[idx] if idx < len(paragraphs) else ''
                        text_after = paragraphs[idx+1] if (idx+1) < len(paragraphs) else ''
                        import re
                        text_before = re.sub(r'<[^>]+>', '', text_before).strip()[:max_chars]
                        text_after = re.sub(r'<[^>]+>', '', text_after).strip()[:max_chars]
                        return text_before + (" " if text_before and text_after else "") + text_after
                    current_paragraph = extract_paragraph_content(paragraphs, position)
                    # 2. 拼接系统模板+用户风格
                    base_prompt = PromptManager.image_prompt_with_style(title, description, custom_image_prompt)
                    # 3. 拼接段落内容
                    full_prompt = f"{base_prompt}\n本段内容：{current_paragraph}"
                    # 4. 用AI大模型润色生成最终prompt（所有模型都适用）
                    ai_prompt = self._generate_prompt_with_ai(ai_model, full_prompt)
                    # dashscope模型ID优先用dashscope_params['model_name']，否则用dashscope_image_model_code
                    if image_model == 'dashscope':
                        if not dashscope_params.get('model_name') and dashscope_image_model_code:
                            dashscope_params['model_name'] = dashscope_image_model_code
                        if not dashscope_params.get('model_name'):
                            logger.error("阿里云百炼模型ID未传递")
                            return content
                    image_path = self.image_service.generate_article_image(
                        title=title,
                        description=description,
                        image_model=image_model,
                        article_content=content,
                        ai_model=ai_model,
                        image_index=i+1,
                        total_images=image_count,
                        dashscope_params=dashscope_params,
                        user_custom_prompt=ai_prompt
                    )
                    if image_path:
                        image_html = f'<img src="{image_path}" alt="文章配图" style="max-width: 100%; height: auto;">'
                        logger.info(f"第{i+1}张配图处理完成，使用本地路径: {image_path}")
                        generated_images.append({
                            'local_path': image_path,
                            'image_html': image_html,
                            'position': position
                        })
                    else:
                        logger.warning(f"第{i+1}张配图生成失败")
                except Exception as e:
                    logger.error(f"生成第{i+1}张配图时出错: {str(e)}")
            processed_content = content
            for img_info in sorted(generated_images, key=lambda x: -x['position']):
                position = img_info['position']
                image_html = f'<p style="text-align: center;">{img_info["image_html"]}</p>'
                parts = processed_content.split('</p>')
                if position < len(parts):
                    parts.insert(position, image_html)
                    processed_content = '</p>'.join(parts)
                    logger.info(f"在第{position}段后插入配图")
            logger.info(f"配图处理完成，共插入{len(generated_images)}张图片")
            return processed_content
        except Exception as e:
            logger.error(f"处理配图时发生错误: {str(e)}")
            return content  # 出错时返回原始内容
    
    def _generate_prompt_with_ai(self, ai_model, prompt):
        """
        用指定AI大模型润色/扩写生图提示词
        """
        try:
            if ai_model == 'gemini':
                from services.gemini_service import GeminiService
                gemini = GeminiService()
                return gemini.generate_content(prompt)
            elif ai_model == 'deepseek':
                from services.deepseek_service import DeepSeekService
                deepseek = DeepSeekService()
                return deepseek.generate_content(prompt)
            elif ai_model == 'inodetree':
                return self._generate_prompt_with_inodetree(prompt)
            else:
                return prompt
        except Exception as e:
            logger.error(f"AI大模型润色prompt失败: {str(e)}")
            return prompt