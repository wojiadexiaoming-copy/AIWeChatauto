"""
文章控制器模块
处理文章生成和发布相关的HTTP请求
"""

import logging
from flask import request, jsonify
from typing import Dict, Any
from services.config_service import ConfigService
from services.gemini_service import GeminiService
from services.deepseek_service import DeepSeekService
from services.dashscope_service import DashScopeService
from services.image_service import ImageService
from services.wechat_service import WeChatService
from services.inodetree_service import InodeTreeService
from services.draft_service import DraftService
from services.history_service import HistoryService

logger = logging.getLogger(__name__)

class ArticleController:
    """文章控制器类"""
    
    def __init__(self):
        self.config_service = ConfigService()
        self.gemini_service = GeminiService()
        self.deepseek_service = DeepSeekService()
        self.dashscope_service = DashScopeService()
        self.image_service = ImageService()
        self.wechat_service = WeChatService()
        self.draft_service = DraftService()
        self.history_service = HistoryService()
        self.inodetree_service = InodeTreeService()
        logger.info("文章控制器初始化完成")
    
    def generate_article(self) -> Dict[str, Any]:
        """
        生成文章
        实现完整的文章生成逻辑：
        1. 根据标题联网搜索或AI理解生成内容
        2. 根据文章长度生成合适数量的配图
        3. 记录配图插入位置
        4. 生成配图并插入图片URL
        :return: 响应数据
        """
        import uuid
        req_id = str(uuid.uuid4())
        logger.info(f"【唯一请求ID】{req_id} - generate_article")
        try:
            data = request.get_json()
            logger.info(f"收到文章生成请求: {data}")
            
            if not data:
                logger.error("请求数据为空")
                return {
                    'success': False,
                    'message': '请求数据为空'
                }
            
            # 新增：接收行业和平台参数
            industry = data.get('industry', '').strip()
            platform = data.get('platform', '').strip().lower()
            logger.info(f"接收到参数：industry={industry}, platform={platform}")
            
            # 新增：抖音平台特殊流程
            # TODO: 抖音热点标题生成待重写优化
            if platform == '抖音' or platform == 'douyin':
                logger.info(f"检测到抖音平台，行业: {industry}")
                from services.douyin_hotspot_crawler import get_douyin_hotspot_markdown
                from services.prompt_manager import PromptManager
                markdown = get_douyin_hotspot_markdown(industry)
                logger.info(f"抖音热点markdown内容前100字: {markdown[:100]}")
                ai_model = data.get('ai_model', 'gemini')
                logger.info(f"调用大模型生成标题，ai_model={ai_model}")
                prompt = PromptManager.douyin_hotspot_title_prompt(markdown, industry)
                title = None
                model_name = None
                if ai_model == 'gemini':
                    gemini_config = self.config_service.get_gemini_config()
                    if not gemini_config['api_key']:
                        return {'success': False, 'message': '请先配置Gemini API密钥'}
                    self.gemini_service.set_api_key(gemini_config['api_key'])
                    model_name = gemini_config.get('model', 'gemini-1.5-flash')
                    title = self.gemini_service.generate_content(prompt, model_name)
                elif ai_model == 'deepseek':
                    deepseek_config = self.config_service.get_deepseek_config()
                    if not deepseek_config['api_key']:
                        return {'success': False, 'message': '请先配置DeepSeek API密钥'}
                    self.deepseek_service.set_api_key(deepseek_config['api_key'])
                    model_name = deepseek_config.get('model', 'deepseek-chat')
                    title = self.deepseek_service.generate_content(prompt, model_name)
                elif ai_model == 'dashscope':
                    dashscope_config = self.config_service.get_dashscope_config()
                    if not dashscope_config['api_key']:
                        return {'success': False, 'message': '请先配置阿里云百炼API密钥'}
                    self.dashscope_service = self.dashscope_service or DashScopeService(dashscope_config['api_key'])
                    model_name = dashscope_config.get('model', 'qwen-turbo')
                    raw = self.dashscope_service.generate_content(prompt, model_name)
                    title = raw.get('content') if isinstance(raw, dict) else raw
                elif ai_model == 'inodetree':
                    inodetree_config = self.config_service.get_inodetree_config()
                    if not inodetree_config['api_key']:
                        return {'success': False, 'message': '请先配置 inodetree API Key'}
                    self.inodetree_service.set_api_key(inodetree_config['api_key'])
                    _raw_model = inodetree_config.get('model', 'inodetree-pro')
                    model_name = {'inodetree-2.0-flash': 'inodetree-pro'}.get(_raw_model, _raw_model) or 'inodetree-pro'
                    title = self.inodetree_service.generate_content(prompt, model_name)
                else:
                    return {'success': False, 'message': f'不支持的AI模型: {ai_model}'}
                logger.info(f"大模型返回标题：{title}")
                if isinstance(title, dict) and 'content' in title:
                    title = title['content']
                if not title:
                    return {'success': False, 'message': '大模型未能生成建议标题，请重试或检查API配置'}
                # 其余参数继续后续流程
            else:
                title = data.get('title', '').strip()
                logger.info(f"普通流程，title={title}")
                if not title:
                    logger.error("文章标题为空")
                    return {
                        'success': False,
                        'message': '请输入文章标题'
                    }
            
            logger.info(f"开始生成文章，标题: {title}")
            
            # 获取AI模型配置
            ai_model = data.get('ai_model', 'gemini')  # 默认使用Gemini
            image_model = data.get('image_model', 'gemini')  # 默认使用Gemini生图
            _model_display = {'inodetree': 'inodetree', 'gemini': 'Gemini', 'deepseek': 'DeepSeek', 'dashscope': '阿里云百炼'}
            logger.info(f"使用AI模型: {_model_display.get(ai_model, ai_model)}, 生图模型: {_model_display.get(image_model, image_model)}")
            
            # 根据选择的模型进行配置检查
            if ai_model == 'gemini':
                # 检查Gemini配置
                gemini_config = self.config_service.get_gemini_config()
                logger.info(f"Gemini配置检查: api_key={'已设置' if gemini_config.get('api_key') else '未设置'}")
                
                if not gemini_config['api_key']:
                    return {
                        'success': False,
                        'message': '请先配置Gemini API密钥'
                    }
                
                # 设置API密钥
                self.gemini_service.set_api_key(gemini_config['api_key'])
                model_name = gemini_config.get('model', 'gemini-1.5-flash')
                
            elif ai_model == 'deepseek':
                # 检查DeepSeek配置
                deepseek_config = self.config_service.get_deepseek_config()
                logger.info(f"DeepSeek配置检查: api_key={'已设置' if deepseek_config.get('api_key') else '未设置'}")
                
                if not deepseek_config['api_key']:
                    return {
                        'success': False,
                        'message': '请先配置DeepSeek API密钥'
                    }
                
                # 设置API密钥
                self.deepseek_service.set_api_key(deepseek_config['api_key'])
                model_name = deepseek_config.get('model', 'deepseek-chat')
                
            elif ai_model == 'dashscope':
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
                logger.info(f"inodetree配置: api_key={'已设置' if inodetree_config.get('api_key') else '未设置'}")
                if not inodetree_config['api_key']:
                    return {'success': False, 'message': '请先配置 inodetree API Key'}
                self.inodetree_service.set_api_key(inodetree_config['api_key'])
                # 旧 config 可能存了 inodetree-2.0-flash，统一转成对外品牌名
                _raw_model = inodetree_config.get('model', 'inodetree-pro')
                model_name = {
                    'inodetree-2.0-flash': 'inodetree-pro',
                }.get(_raw_model, _raw_model) or 'inodetree-pro'

            else:
                return {
                    'success': False,
                    'message': f'不支持的AI模型: {ai_model}'
                }
            
            # 新增：接收前端传递的字数、配图数量和格式模板
            word_count = data.get('word_count')
            image_count = data.get('image_count')
            format_template = data.get('format_template', '')

            # token 累计器
            tokens_used = 0

            # 第一步：生成文章内容（包含搜索结果和AI理解）
            logger.info(f"第一步：开始生成文章内容，使用模型: {model_name}")

            from services.prompt_manager import PromptManager
            char_limit = 20000
            
            persona_id = data.get('persona_id')
            role_prompt = None
            if persona_id:
                config = self.config_service.load_config()
                skills = config.get('skills', [])
                selected_skill = next((s for s in skills if s.get('id') == persona_id), None)
                if selected_skill:
                    identity = selected_skill.get('identity', '').strip()
                    user = selected_skill.get('user', '').strip()
                    workflow = selected_skill.get('workflow', '').strip()
                    
                    role_parts = []
                    if identity:
                        role_parts.append(f"# 角色性格与自我认知 (IDENTITY)\n{identity}")
                    if user:
                        role_parts.append(f"# 目标受众画像 (AUDIENCE)\n{user}")
                    if workflow:
                        role_parts.append(f"# 写作流程与排版规范 (WORKFLOW)\n{workflow}")
                        
                    # 兼容旧版单一的 system_prompt
                    if not role_parts and selected_skill.get('system_prompt'):
                        role_parts.append(selected_skill.get('system_prompt'))
                        
                    role_prompt = "\n\n".join(role_parts)
                    logger.info(f"使用选定人设: {selected_skill.get('name')}")
            
            article_prompt = PromptManager.article_prompt(title, word_count, char_limit, format_template=format_template, role_prompt=role_prompt)

            if ai_model == 'gemini':
                content, t = self.gemini_service.generate_with_usage(article_prompt, model_name)
            elif ai_model == 'deepseek':
                content, t = self.deepseek_service.generate_with_usage(article_prompt, model_name)
            elif ai_model == 'dashscope':
                content, t = self.dashscope_service.generate_with_usage(article_prompt, model_name, max_tokens=4000)
            elif ai_model == 'inodetree':
                content, t = self.inodetree_service.generate_with_usage(article_prompt, model_name)
            else:
                return {'success': False, 'message': f'不支持的AI模型: {ai_model}'}
            tokens_used += t or 0
            
            if not content:
                logger.error("文章内容生成失败")
                return {
                    'success': False,
                    'message': '文章内容生成失败'
                }
            logger.info(f"文章内容生成成功，长度: {len(content)}字符")

            # 第二步：生成文章摘要
            logger.info("第二步：开始生成文章摘要")
            content_preview = content[:800]
            digest_prompt = PromptManager.digest_prompt(title, content_preview, role_prompt=role_prompt)
            if ai_model == 'gemini':
                digest_raw, t = self.gemini_service.generate_with_usage(digest_prompt, model_name)
            elif ai_model == 'deepseek':
                digest_raw, t = self.deepseek_service.generate_with_usage(digest_prompt, model_name)
            elif ai_model == 'dashscope':
                digest_raw, t = self.dashscope_service.generate_with_usage(digest_prompt, model_name, max_tokens=200)
            elif ai_model == 'inodetree':
                digest_raw, t = self.inodetree_service.generate_with_usage(digest_prompt, model_name, max_tokens=256)
            else:
                digest_raw, t = None, 0
            tokens_used += t or 0
            if digest_raw:
                digest = digest_raw[:120] if len(digest_raw) > 120 else digest_raw
            else:
                digest = f"探索{title}的深度解析，获取独特见解和实用价值。"
            logger.info(f"摘要生成完成: {digest[:50]}…  (本步 token: {t})")

            # 第三步：根据参数或内容确定配图数量
            if not word_count:
                word_count = len(content.replace('<', '').replace('>', ''))
            if not image_count:
                image_count = max(1, min(3, int(word_count) // 500))
            else:
                image_count = int(image_count)
            logger.info(f"文章字数约: {word_count}，计划生成配图数量: {image_count}")

            # 第四步：生成配图并插入
            logger.info("第四步：开始生成和插入配图")
            custom_image_prompt = data.get('custom_image_prompt', '').strip()
            dashscope_image_model_code = data.get('dashscope_image_model_code', '').strip()
            if image_model == 'dashscope' and dashscope_image_model_code:
                image_model_code = dashscope_image_model_code
            else:
                image_model_code = image_model
            # 后续传递 image_model_code 给图片生成逻辑
            dashscope_params = data.get('dashscope_params', {})
            content_with_images = self._process_images_in_content(
                content, title, digest, image_count, image_model_code, ai_model, custom_image_prompt,
                dashscope_params=dashscope_params, dashscope_image_model_code=dashscope_image_model_code
            )
            
            # 第四点六步：生成视频并插入（可选）
            video_model = data.get('video_model', '')
            video_count = int(data.get('video_count', 0) or 0)
            video_fps = int(data.get('video_fps', 24) or 24)
            if video_model and video_count > 0:
                logger.info(f"第四点六步：开始生成视频，模型: {video_model}, 数量: {video_count}, FPS: {video_fps}")
                content_with_images = self._process_videos_in_content(
                    content_with_images, title, digest, video_count, video_model, video_fps, ai_model
                )
            else:
                logger.info("未配置视频生成，跳过")


            # 第四点五步：输出原始文章内容到cache文件夹，便于对比
            try:
                import os
                from datetime import datetime
                safe_title = ''.join(c for c in title if c.isalnum() or c in (' ', '-', '_')).rstrip()[:20]
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                cache_dir = 'cache'
                if not os.path.exists(cache_dir):
                    os.makedirs(cache_dir)
                raw_file_path = os.path.join(cache_dir, f"article_raw_{safe_title}_{timestamp}.html")
                with open(raw_file_path, 'w', encoding='utf-8') as f:
                    f.write(content_with_images)
                logger.info(f"原始文章内容已保存到: {raw_file_path}")
            except Exception as e:
                logger.error(f"保存原始文章内容到cache失败: {str(e)}")

            # 第五步：清理AI生成内容中的多余部分
            logger.info("第五步：开始清理内容中的多余部分")
            processed_content = self._clean_ai_generated_content(content_with_images)
            
            # 限制最终HTML内容不超过2万字符，但要在完整标签处截断
            max_chars = 20000
            if len(processed_content) > max_chars:
                logger.warning(f"生成内容超出2万字符，已自动截断。原长度: {len(processed_content)}")
                # 从 max_chars 往前找最近的完整闭合标签（</p> </div> </section>）
                truncated = processed_content[:max_chars]
                for end_tag in ('</section>', '</div>', '</p>', '</li>'):
                    idx = truncated.rfind(end_tag)
                    if idx > max_chars * 0.8:  # 截断点不少于80%内容
                        truncated = truncated[:idx + len(end_tag)]
                        break
                # 动态平衡未闭合的 HTML 标签
                tag_pattern = _re.compile(r'<(/)?([a-zA-Z1-6]+)(?:\s+[^>]*?)?(/)?>')
                stack = []
                self_closing = {'img', 'br', 'hr', 'input', 'link', 'meta', 'source'}
                
                for match in tag_pattern.finditer(truncated):
                    is_close = bool(match.group(1))
                    tag_name = match.group(2).lower()
                    is_self_closing = bool(match.group(3))
                    
                    if tag_name in self_closing or is_self_closing:
                        continue
                        
                    if is_close:
                        if tag_name in stack:
                            while stack:
                                popped = stack.pop()
                                if popped == tag_name:
                                    break
                    else:
                        stack.append(tag_name)
                        
                closed_tags = ''.join(f'</{tag}>' for tag in reversed(stack))
                processed_content = truncated + closed_tags
            
            # 第六步：保存删减后的文章到cache文件夹
            try:
                import os
                from datetime import datetime
                safe_title = ''.join(c for c in title if c.isalnum() or c in (' ', '-', '_')).rstrip()[:20]
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                cache_dir = 'cache'
                if not os.path.exists(cache_dir):
                    os.makedirs(cache_dir)
                cleaned_file_path = os.path.join(cache_dir, f"article_cleaned_{safe_title}_{timestamp}.html")
                with open(cleaned_file_path, 'w', encoding='utf-8') as f:
                    f.write(processed_content)
                logger.info(f"删减后的文章内容已保存到: {cleaned_file_path}")
            except Exception as e:
                logger.error(f"保存删减后文章内容到cache失败: {str(e)}")
            
            # 记录带图内容摘要
            logger.info(f"[历史记录] 生成文章: 标题={title}, 内容前100字={processed_content[:100]}, 图片数={processed_content.count('<img')}")
            
            # 构建响应数据
            import os
            from datetime import datetime
            response_data = {
                'title': title,
                'content': processed_content,
                'digest': digest,
                'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'content_length': len(processed_content),
                'image_count': image_count,
                'video_count': video_count if 'video_count' in dir() else 0,
                'tokens_used': tokens_used,
                'author': self.config_service.get_config_value('author', 'AI笔记'),
                'content_source_url': self.config_service.get_config_value('content_source_url', '')
            }
            logger.info(f"本次生成累计消耗 token: {tokens_used}")
            
            # 添加生成历史记录
            self.history_service.add_generation_history(response_data)
            
            logger.info("文章生成完成")
            logger.info(f"生成结果预览: 标题={title}, 内容长度={len(processed_content)}, 配图数量={image_count}")
            
            return {
                'success': True,
                'message': '文章生成成功',
                'data': response_data
            }
            
        except Exception as e:
            logger.error(f"生成文章时发生错误: {str(e)}", exc_info=True)
            return {
                'success': False,
                'message': f'生成文章失败: {str(e)}'
            }
    
    def save_draft(self) -> Dict[str, Any]:
        """
        保存文章草稿到微信公众号
        :return: 响应数据
        """
        import uuid
        req_id = str(uuid.uuid4())
        logger.info(f"【唯一请求ID】{req_id} - save_draft")
        try:
            data = request.get_json()
            if not data:
                return {
                    'success': False,
                    'message': '请求数据为空'
                }
            
            article_data = data.get('article')
            if not article_data:
                return {
                    'success': False,
                    'message': '缺少文章数据'
                }
            
            logger.info(f"开始保存草稿: {article_data.get('title', 'Unknown')}")
            
            # 检查微信配置
            wechat_config = self.config_service.get_wechat_config()
            if not wechat_config['appid'] or not wechat_config['appsecret']:
                return {
                    'success': False,
                    'message': '请先配置微信公众号信息'
                }
            
            # 获取access_token
            logger.info("获取微信access_token")
            token_info = self.wechat_service.get_access_token(
                wechat_config['appid'],
                wechat_config['appsecret']
            )
            
            if not token_info or not token_info.get('access_token'):
                return {
                    'success': False,
                    'message': '获取微信access_token失败'
                }
            
            access_token = token_info['access_token']
            
            # 处理文章内容中的图片，上传到微信平台并替换为微信URL，并收集media_id
            image_process_result = self._process_content_images(article_data['content'], access_token)
            processed_content = image_process_result['content']

            # ── 清理微信不接受的内容 ──────────────────────────────
            import re as _re
            # 1. 移除视频占位符 div 及其外层 <p> 包裹（视频还没生成完，不能提交给微信）
            processed_content = _re.sub(
                r'<p[^>]*>\s*<div[^>]*data-video-placeholder=["\'][^"\']*["\'][^>]*>.*?</div>\s*</p>',
                '', processed_content, flags=_re.DOTALL
            )
            # 兜底：再移除裸露的占位符 div（不在 <p> 内的情况）
            processed_content = _re.sub(
                r'<div[^>]*data-video-placeholder=["\'][^"\']*["\'][^>]*>.*?</div>',
                '', processed_content, flags=_re.DOTALL
            )
            # 2. 移除外部域名图片（placeholder.com 等，微信会拒绝）
            processed_content = _re.sub(
                r'<img[^>]*src=["\']https?://(?!mmbiz\.qpic\.cn)[^"\']+["\'][^>]*>',
                '', processed_content
            )
            # 3. 清理多余的空 <p></p>（移除占位符后可能留下）
            processed_content = _re.sub(r'<p[^>]*>\s*</p>', '', processed_content)
            # 4. 修复畸形 video 标签（<div video src=...> 或未闭合的）→ 直接移除，微信不支持 video
            processed_content = _re.sub(
                r'<(?:div|p)[^>]*\bvideo\s+src=["\'][^"\']*["\'][^>]*>(?:.*?</(?:div|p)>)?',
                '', processed_content, flags=_re.DOTALL
            )
            # 5. 移除正常的 <video> 标签（微信公众号不支持 video 标签）
            processed_content = _re.sub(
                r'<video[^>]*>.*?</video>',
                '', processed_content, flags=_re.DOTALL
            )
            # 6. 移除 AI 模板中的占位符图片（src 不是真实 URL）
            processed_content = _re.sub(
                r'<img[^>]*src=["\']【[^】]*】["\'][^>]*>',
                '', processed_content
            )
            # 7. 修复 style 属性里的裸双引号（如 font-family: "Noto Serif SC" 会破坏 JSON）
            #    用正则把 style 属性值里的双引号替换为单引号
            def _fix_style_inner_quotes(m):
                # m.group(1) = style=" 之后到结束的内容
                # 把值里面的双引号换成单引号
                inner = m.group(1).replace('"', "'")
                return f'style="{inner}"'
            processed_content = _re.sub(
                r'style="(.*?)"(?=\s*/?>|\s+[a-zA-Z\-]+=)',
                _fix_style_inner_quotes,
                processed_content,
                flags=_re.DOTALL
            )
            # ─────────────────────────────────────────────────────

            # 记录草稿内容摘要
            logger.info(f"[草稿保存] 标题={article_data.get('title', 'Unknown')}, 内容前100字={processed_content[:100]}, 图片数={processed_content.count('<img')}")
            images = image_process_result['images']
            thumb_media_id = images[0]['media_id'] if images and images[0].get('media_id') else ''

            if not thumb_media_id:
                logger.error("封面图 media_id 为空，无法创建草稿（文章内至少需要一张本地配图）")
                return {'success': False, 'message': '封面图上传失败，请确认文章中包含已生成的配图'}
            
            # 获取作者配置
            author_config = self.config_service.get_author_config()
            
            # 创建草稿数据，使用第一个图片的media_id作为thumb_media_id
            logger.info("开始创建草稿")
            draft_data = self.draft_service.build_draft_data(
                title=article_data['title'],
                content=processed_content,
                author=author_config['author'],
                digest=article_data.get('digest', ''),
                thumb_media_id=thumb_media_id,
                content_source_url=author_config['content_source_url']
            )
            
            # 验证草稿数据
            if not self.draft_service.validate_draft_data(draft_data):
                return {
                    'success': False,
                    'message': '草稿数据验证失败'
                }
            
            # 创建草稿
            draft_result = self.draft_service.create_draft(access_token, draft_data)
            if not draft_result or not draft_result.get('media_id'):
                error_msg = draft_result.get('errmsg', '创建草稿失败') if draft_result else '创建草稿失败'
                logger.error(f"创建草稿失败: {error_msg}")
                return {
                    'success': False,
                    'message': f'创建草稿失败: {error_msg}'
                }
            
            media_id = draft_result['media_id']
            logger.info(f"草稿保存成功，media_id: {media_id}")
            
            # 更新历史记录状态
            self.history_service.update_draft_status(article_data['title'], media_id)
            
            return {
                'success': True,
                'message': '草稿保存成功',
                'data': {
                    'media_id': media_id,
                    'draft_info': self.draft_service.get_draft_info(draft_data)
                }
            }
                
        except Exception as e:
            logger.error(f"保存草稿时发生错误: {str(e)}")
            return {
                'success': False,
                'message': f'保存草稿失败: {str(e)}'
            }
    
    def publish_draft(self) -> Dict[str, Any]:
        """
        发布草稿到微信公众号
        :return: 响应数据
        """
        import uuid
        req_id = str(uuid.uuid4())
        logger.info(f"【唯一请求ID】{req_id} - publish_draft")
        try:
            data = request.get_json()
            if not data:
                return {
                    'success': False,
                    'message': '请求数据为空'
                }
            
            media_id = data.get('media_id')
            if not media_id:
                return {
                    'success': False,
                    'message': '缺少草稿media_id'
                }
            
            logger.info(f"开始发布草稿，media_id: {media_id}")
            
            # 检查微信配置
            wechat_config = self.config_service.get_wechat_config()
            if not wechat_config['appid'] or not wechat_config['appsecret']:
                return {
                    'success': False,
                    'message': '请先配置微信公众号信息'
                }
            
            # 获取access_token
            logger.info("获取微信access_token")
            token_info = self.wechat_service.get_access_token(
                wechat_config['appid'],
                wechat_config['appsecret']
            )
            
            if not token_info or not token_info.get('access_token'):
                return {
                    'success': False,
                    'message': '获取微信access_token失败'
                }
            
            access_token = token_info['access_token']
            
            # 发布草稿
            logger.info("开始发布草稿")
            publish_result = self.draft_service.publish_draft(access_token, media_id)
            
            if publish_result and publish_result.get('errcode') == 0:
                logger.info("草稿发布成功")
                
                # 更新历史记录状态
                publish_data = {
                    'publish_id': publish_result.get('publish_id'),
                    'msg_data_id': publish_result.get('msg_data_id')
                }
                self.history_service.update_publish_status(media_id, publish_data)
                
                return {
                    'success': True,
                    'message': '草稿发布成功',
                    'data': {
                        'publish_id': publish_result.get('publish_id'),
                        'msg_data_id': publish_result.get('msg_data_id'),
                        'media_id': media_id
                    }
                }
            else:
                error_msg = publish_result.get('errmsg', '发布失败') if publish_result else '发布失败'
                logger.error(f"草稿发布失败: {error_msg}")
                return {
                    'success': False,
                    'message': f'草稿发布失败: {error_msg}'
                }
                
        except Exception as e:
            logger.error(f"发布草稿时发生错误: {str(e)}")
            return {
                'success': False,
                'message': f'发布草稿失败: {str(e)}'
            }
    
    def _process_content_images(self, content: str, access_token: str) -> dict:
        """
        处理文章内容中的图片，将本地图片上传到微信平台并替换为微信URL格式，并返回media_id和url列表
        :param content: 原始内容
        :param access_token: 微信access_token
        :return: {'content': 替换后的内容, 'images': [{'media_id':..., 'url':...}, ...]}
        """
        try:
            import re
            # 查找所有本地图片路径
            local_image_pattern = r'<img[^>]*src=["\'](cache\\[^"\']+)["\'][^>]*>'
            matches = re.findall(local_image_pattern, content)
            
            processed_content = content
            images = []
            for local_path in matches:
                # 上传图片到微信平台获取URL（用于文章内容）
                image_url = self.wechat_service.upload_article_image(access_token, local_path)
                if image_url:
                    # 替换为微信URL格式
                    img_pattern = rf'<img[^>]*src=["\']{re.escape(local_path)}["\'][^>]*>'
                    url_replacement = f'<img src="{image_url}" alt="文章配图" style="max-width: 100%; height: auto;">'
                    processed_content = re.sub(img_pattern, url_replacement, processed_content)
                    
                    # 同时上传为永久素材获取media_id（用于封面）
                    upload_result = self.wechat_service.upload_permanent_material(
                        access_token, local_path, 'image'
                    )
                    media_id = upload_result.get('media_id') if upload_result else None
                    images.append({'media_id': media_id, 'url': image_url})
                    logger.info(f"图片上传成功，本地路径: {local_path}, 微信URL: {image_url}, media_id: {media_id}")
                else:
                    logger.warning(f"图片上传失败，保持本地路径: {local_path}")
            
            return {'content': processed_content, 'images': images}
            
        except Exception as e:
            logger.error(f"处理内容图片时发生错误: {str(e)}")
            return {'content': content, 'images': []}  # 出错时返回原始内容
    
    def _get_image_path(self, image_url: str) -> str:
        """
        从图片URL获取本地路径
        :param image_url: 图片URL
        :return: 本地路径
        """
        if image_url.startswith('/cache/'):
            return image_url.replace('/cache/', 'cache/')
        return image_url
    

    def _process_videos_in_content(self, content: str, title: str, description: str,
                                    video_count: int, video_model: str = "inodetree",
                                    video_fps: int = 24, ai_model: str = "gemini") -> str:
        """
        在文章内容中均匀插入视频占位符，并返回含占位符的 HTML。
        实际视频异步生成，前端轮询 /api/video-status 完成后替换占位符。
        占位符格式: <div data-video-placeholder="VIDEO_ID_xxx" ...></div>
        """
        import re as _re
        try:
            FPS_FRAMES = {24: 361, 30: 241, 60: 121}
            num_frames = FPS_FRAMES.get(video_fps, 361)

            paragraphs = content.split('</p>')
            total_paragraphs = len(paragraphs)
            if total_paragraphs < 2 or video_count < 1:
                return content

            if video_count >= total_paragraphs:
                insert_positions = list(range(1, total_paragraphs))[:video_count]
            else:
                insert_positions = [round((i + 1) * total_paragraphs / (video_count + 1))
                                    for i in range(video_count)]

            inodetree_cfg = self.config_service.get_inodetree_config()
            if not inodetree_cfg.get('api_key'):
                logger.error("inodetree API Key 未配置，跳过视频生成")
                return content

            from services.inodetree_service import InodeTreeService
            inodetree = InodeTreeService(inodetree_cfg['api_key'])

            placeholders = []  # [(position, video_id, placeholder_html)]
            for idx, position in enumerate(insert_positions):
                para_idx = max(0, position - 1)
                para_text = paragraphs[para_idx] if para_idx < len(paragraphs) else ''
                para_text = _re.sub(r'<[^>]+>', '', para_text).strip()[:200]
                prompt = (
                    f"cinematic video about {title}, "
                    f"{para_text[:100] if para_text else description}, "
                    "smooth motion, high quality, realistic"
                )
                task = inodetree.create_video_task(
                    prompt=prompt,
                    width=1152, height=768,
                    num_frames=num_frames,
                    frame_rate=video_fps
                )
                if task and task.get('video_id'):
                    vid = task['video_id']
                    placeholder = (
                        f'<div data-video-placeholder="{vid}" '
                        f'style="background:#f3f4f6;border-radius:8px;padding:24px;text-align:center;'
                        f'color:#666;font-size:13px;margin:12px 0;">'
                        f'<span>🎬 视频生成中，请稍候…</span>'
                        f'</div>'
                    )
                    placeholders.append((position, vid, placeholder))
                    logger.info(f"视频任务已提交 video_id={vid}，插入位置={position}")
                else:
                    logger.error(f"第{idx+1}个视频任务提交失败")

            # 从后往前插入占位符
            processed = content
            for position, vid, placeholder in sorted(placeholders, key=lambda x: -x[0]):
                parts = processed.split('</p>')
                if position < len(parts):
                    parts.insert(position, f'<p style="text-align:center;">{placeholder}</p>')
                    processed = '</p>'.join(parts)

            return processed

        except Exception as e:
            logger.error(f"提交视频任务失败: {str(e)}")
            return content

    def get_video_status(self) -> Dict[str, Any]:
        """
        查询单个视频状态，前端轮询用
        GET /api/video-status?video_id=xxx
        通过 inodetree 云函数代理查询，不直连 InodeTree
        """
        video_id = request.args.get('video_id', '').strip()
        if not video_id:
            return {'success': False, 'message': '缺少 video_id 参数'}

        inodetree_cfg = self.config_service.get_inodetree_config()
        if not inodetree_cfg.get('api_key'):
            return {'success': False, 'message': 'inodetree API Key 未配置'}

        from services.inodetree_service import InodeTreeService, INODETREE_BASE_URL
        import requests as req_lib

        try:
            inodetree = InodeTreeService(inodetree_cfg['api_key'])
            resp = req_lib.get(
                INODETREE_BASE_URL,
                headers={**inodetree._headers(), 'X-Action': 'video_result'},
                params={'action': 'video_result', 'video_id': video_id},
                timeout=25
            )
            logger.info(f"[video_status] HTTP {resp.status_code}  body前200={resp.text[:200]}")
            resp.raise_for_status()
            data = inodetree._unwrap(resp)
            logger.info(f"[video_status] unwrap后 data={str(data)[:300]}")

            if data.get('error'):   # error字段存在且不为 None/空 才报错
                err_val = data['error']
                err_code = err_val.get('code') if isinstance(err_val, dict) else None
                logger.warning(f"[video_status] data包含error字段: {err_val}")
                # 429 限流：不报失败，让前端继续轮询（稍后重试）
                if err_code == 429:
                    return {
                        'success': True,
                        'status': 'in_progress',
                        'progress': 0,
                        'video_id': video_id,
                        'local_path': None,
                        'cache_url': None,
                    }
                return {'success': False, 'message': str(err_val)}

            status    = data.get('status', 'pending')
            video_url = (data.get('video_url') or
                         data.get('remixed_from_video_id') or
                         data.get('url')) if status == 'completed' else None

            logger.info(f"[video_status] status={status} video_url={str(video_url)[:80] if video_url else None}")

            # 视频完成后优先用云函数返回的云存储 CDN URL
            local_path = None
            cache_url  = None
            if status == 'completed':
                cdn_url   = data.get('cdn_video_url')   # 云函数上传到云存储后的 CDN 链接
                video_b64 = data.get('video_b64')       # 旧 base64 方案（降级兜底）

                if cdn_url:
                    # 从 CDN URL 下载到本地 cache（前端播放 + 后续上传微信用）
                    try:
                        import os, time
                        os.makedirs('cache', exist_ok=True)
                        save_path = os.path.join('cache', f'inodetree_vid_{int(time.time())}.mp4')
                        dl = req_lib.get(cdn_url, timeout=120, stream=True)
                        dl.raise_for_status()
                        with open(save_path, 'wb') as f:
                            for chunk in dl.iter_content(chunk_size=1024 * 1024):
                                f.write(chunk)
                        local_path = save_path
                        cache_url  = f'/cache/{os.path.basename(save_path)}'
                        logger.info(f"[video_status] 视频下载到本地成功: {save_path}")
                        # 持久化 video_id → 本地路径映射，供历史记录加载时使用
                        self._save_video_mapping(video_id, save_path)
                    except Exception as dl_err:
                        logger.warning(f"[video_status] 视频本地下载失败，使用 CDN URL: {dl_err}")
                        cache_url = cdn_url

                elif video_b64:
                    # 降级：云函数返回了 base64（文件较小时）
                    try:
                        import base64 as _b64, os, time
                        os.makedirs('cache', exist_ok=True)
                        save_path = os.path.join('cache', f'inodetree_vid_{int(time.time())}.mp4')
                        with open(save_path, 'wb') as f:
                            f.write(_b64.b64decode(video_b64))
                        local_path = save_path
                        cache_url  = f'/cache/{os.path.basename(save_path)}'
                        logger.info(f"[video_status] 视频 base64 写入成功: {save_path}")
                    except Exception as b64_err:
                        logger.warning(f"[video_status] 视频 base64 解码失败: {b64_err}")

                # 都没有，把原始 video_url 透传（前端可能播不了但总比报 None 好）
                if not cache_url and video_url:
                    cache_url = video_url
                    logger.warning(f"[video_status] 无 CDN URL，透传原始 URL: {video_url[:80]}")

            return {
                'success': True,
                'status': status,
                'progress': data.get('progress', 0),
                'video_id': video_id,
                'local_path': local_path,
                'cache_url': cache_url,
            }
        except Exception as e:
            logger.error(f"查询视频状态失败: {str(e)}")
            return {'success': False, 'message': str(e)}

    # ── 视频 ID → 本地路径 映射持久化 ─────────────────────────
    _VIDEO_MAP_FILE = 'data/video_map.json'

    def _save_video_mapping(self, video_id: str, local_path: str):
        """保存 video_id → 本地文件路径 的映射到 data/video_map.json"""
        import json, os
        try:
            os.makedirs('data', exist_ok=True)
            mapping = {}
            if os.path.exists(self._VIDEO_MAP_FILE):
                with open(self._VIDEO_MAP_FILE, 'r', encoding='utf-8') as f:
                    mapping = json.load(f)
            mapping[video_id] = local_path
            with open(self._VIDEO_MAP_FILE, 'w', encoding='utf-8') as f:
                json.dump(mapping, f, ensure_ascii=False)
        except Exception as e:
            logger.warning(f"保存视频映射失败: {e}")

    def _load_video_mapping(self) -> dict:
        """加载 video_id → 本地路径 映射"""
        import json, os
        try:
            if os.path.exists(self._VIDEO_MAP_FILE):
                with open(self._VIDEO_MAP_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception:
            pass
        return {}

    def get_article_preview(self) -> Dict[str, Any]:
        """
        获取文章预览
        :return: 响应数据
        """
        try:
            data = request.get_json()
            if not data:
                return {
                    'success': False,
                    'message': '请求数据为空'
                }
            
            # 只用带图内容
            preview_content = data.get('content', '')
            logger.info(f"[预览] 标题={data.get('title', 'Unknown')}, 内容前100字={preview_content[:100]}, 图片数={preview_content.count('<img')}")
            
            return {
                'success': True,
                'message': '预览数据获取成功',
                'data': data
            }
            
        except Exception as e:
            logger.error(f"获取文章预览时发生错误: {str(e)}")
            return {
                'success': False,
                'message': f'获取预览失败: {str(e)}'
            }
    
    def _process_images_in_content(self, content: str, title: str, description: str, image_count: int, image_model: str = "gemini", ai_model: str = "gemini", custom_image_prompt: str = "", dashscope_params: dict = None, dashscope_image_model_code: str = "") -> str:
        """
        在文章内容中处理配图：生成图片并插入到合适位置，仅插入本地图片路径，不上传到公众号平台。
        :param content: 原始文章内容
        :param title: 文章标题
        :param description: 文章描述
        :param image_count: 配图数量
        :param image_model: 生图模型
        :param ai_model: AI模型（用于Pexels搜索提示词生成）
        :param custom_image_prompt: 自定义图片提示词
        :return: 插入配图后的内容
        """
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
                    user_custom_prompt = custom_image_prompt
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
                        user_custom_prompt=user_custom_prompt
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
    
    def get_generation_history(self) -> Dict[str, Any]:
        """
        获取文章生成历史
        :return: 响应数据
        """
        try:
            limit = request.args.get('limit', 20, type=int)
            history = self.history_service.get_generation_history(limit)
            
            return {
                'success': True,
                'message': '获取历史记录成功',
                'data': history
            }
            
        except Exception as e:
            logger.error(f"获取生成历史时发生错误: {str(e)}")
            return {
                'success': False,
                'message': f'获取历史记录失败: {str(e)}'
            }
    
    def get_publish_history(self) -> Dict[str, Any]:
        """
        获取发布历史
        :return: 响应数据
        """
        try:
            limit = request.args.get('limit', 20, type=int)
            publish_history = self.history_service.get_publish_history(limit)
            
            return {
                'success': True,
                'message': '获取发布历史成功',
                'data': publish_history
            }
            
        except Exception as e:
            logger.error(f"获取发布历史时发生错误: {str(e)}")
            return {
                'success': False,
                'message': f'获取发布历史失败: {str(e)}'
            }
    
    def get_article_content(self) -> Dict[str, Any]:
        """
        获取指定文章的内容
        :return: 响应数据
        """
        try:
            data = request.get_json()
            if not data:
                return {
                    'success': False,
                    'message': '请求数据为空'
                }
            
            cache_files = data.get('cache_files', [])
            title       = data.get('title', '')

            if not cache_files and not title:
                return {
                    'success': False,
                    'message': '缺少cache文件信息'
                }

            content = self.history_service.get_article_content(cache_files)

            # cache_files 路径失效（换机器/路径变了）时，用 title 重新匹配
            if content is None and title:
                fallback_files = self.history_service._find_cache_files(title)
                content = self.history_service.get_article_content(fallback_files)

            if content is None:
                return {
                    'success': False,
                    'message': '文章内容不存在'
                }

            # ── 替换已下载的视频占位符 ───────────────────────────────
            # 查映射表，把已下载视频的占位符直接替换为 <video> 标签，无需前端轮询
            import re as _re, os as _os
            video_map = self._load_video_mapping()

            def _replace_video_placeholder(m):
                video_id = m.group(1)
                local_path = video_map.get(video_id)
                if local_path and _os.path.exists(local_path):
                    cache_url = '/cache/' + _os.path.basename(local_path)
                    logger.info(f"[load] 视频占位符 → 本地文件 {local_path}")
                    return (f'<video src="{cache_url}" controls '
                            f'style="max-width:100%;height:auto;border-radius:8px;margin:8px 0;" '
                            f'preload="metadata"></video>')
                return m.group(0)   # 没找到本地文件，保留占位符让前端轮询

            content = _re.sub(
                r'<div[^>]*data-video-placeholder=["\']([^"\']+)["\'][^>]*>.*?</div>',
                _replace_video_placeholder,
                content,
                flags=_re.DOTALL
            )
            # ─────────────────────────────────────────────────────────

            return {
                'success': True,
                'message': '获取文章内容成功',
                'content': content,
                'data': {
                    'content': content
                }
            }
            
        except Exception as e:
            logger.error(f"获取文章内容时发生错误: {str(e)}")
            return {
                'success': False,
                'message': f'获取文章内容失败: {str(e)}'
            }
    
    def _clean_ai_generated_content(self, content: str) -> str:
        """
        清理AI生成内容中的多余部分，只保留正文HTML，去除AI附加说明、代码块标记等
        :param content: 原始内容
        :return: 清理后的内容
        """
        try:
            import re
            from bs4 import BeautifulSoup
            logger.info("开始清理AI生成内容（修正版）")
            original_length = len(content)
            
            # 1. 删除开头的 ```html 标记
            content = re.sub(r'^```html\s*', '', content, flags=re.IGNORECASE | re.MULTILINE)
            
            # 2. 找到最后一个</div>的位置，只保留到这里
            last_div_idx = content.rfind('</div>')
            if last_div_idx != -1:
                content = content[:last_div_idx + len('</div>')]
                logger.info(f"找到最后一个</div>，截断到位置: {last_div_idx + len('</div>')}")
            else:
                logger.warning("未找到</div>标签，保留全部内容")
            
            # 3. 处理样式内联化（新增）
            content = self._inline_styles(content)
            
            # 4. 清理多余空白
            content = content.strip()
            
            cleaned_length = len(content)
            removed_chars = original_length - cleaned_length
            
            if cleaned_length == 0:
                logger.error("清理后内容为空，返回原始内容")
                return content  # 如果清理后为空，返回原始内容
            elif removed_chars > 0:
                logger.info(f"内容清理完成，移除了 {removed_chars} 个字符，清理后长度: {cleaned_length}")
            else:
                logger.info("内容清理完成，未发现需要清理的内容")
            
            return content
            
        except Exception as e:
            logger.error(f"清理AI生成内容时发生错误: {str(e)}")
            return content  # 出错时返回原始内容
    
    def _inline_styles(self, content: str) -> str:
        """
        将<style>标签中的CSS样式转换为内联样式
        :param content: 原始HTML内容
        :return: 内联样式后的HTML内容
        """
        try:
            from bs4 import BeautifulSoup
            import re
            
            soup = BeautifulSoup(content, 'html.parser')
            
            # 查找<style>标签
            style_tags = soup.find_all('style')
            if not style_tags:
                logger.info("未发现<style>标签，无需内联处理")
                return content
            
            logger.info(f"发现{len(style_tags)}个<style>标签，开始内联处理")
            
            # 收集所有CSS规则
            css_rules = []
            for style_tag in style_tags:
                css_text = style_tag.get_text()
                # 解析CSS规则
                rules = self._parse_css_rules(css_text)
                css_rules.extend(rules)
                # 删除<style>标签
                style_tag.decompose()
            
            # 应用CSS规则到对应的HTML元素
            for selector, properties in css_rules:
                elements = soup.select(selector)
                for element in elements:
                    # 获取现有样式
                    existing_style = element.get('style', '')
                    # 合并新样式
                    new_style = self._merge_styles(existing_style, properties)
                    element['style'] = new_style
            
            logger.info(f"样式内联处理完成，应用了{len(css_rules)}个CSS规则")
            return str(soup)
            
        except Exception as e:
            logger.error(f"样式内联处理时发生错误: {str(e)}")
            return content
    
    def _parse_css_rules(self, css_text: str) -> list:
        """
        解析CSS文本，提取选择器和属性
        :param css_text: CSS文本
        :return: [(selector, properties_dict), ...]
        """
        import re
        
        rules = []
        # 移除注释和多余空白
        css_text = re.sub(r'/\*.*?\*/', '', css_text, flags=re.DOTALL)
        css_text = re.sub(r'\s+', ' ', css_text)
        
        # 匹配CSS规则
        pattern = r'([^{]+)\{([^}]+)\}'
        matches = re.findall(pattern, css_text)
        
        for selector, properties_text in matches:
            selector = selector.strip()
            properties = {}
            
            # 解析属性
            for prop in properties_text.split(';'):
                prop = prop.strip()
                if ':' in prop:
                    key, value = prop.split(':', 1)
                    properties[key.strip()] = value.strip()
            
            if properties:
                rules.append((selector, properties))
        
        return rules
    
    def _merge_styles(self, existing_style: str, new_properties: dict) -> str:
        """
        合并现有样式和新属性
        :param existing_style: 现有样式字符串
        :param new_properties: 新属性字典
        :return: 合并后的样式字符串
        """
        # 解析现有样式
        existing_props = {}
        if existing_style:
            for prop in existing_style.split(';'):
                prop = prop.strip()
                if ':' in prop:
                    key, value = prop.split(':', 1)
                    existing_props[key.strip()] = value.strip()
        
        # 合并属性（新属性覆盖旧属性）
        merged_props = {**existing_props, **new_properties}
        
        # 转换为样式字符串
        style_parts = [f"{key}: {value}" for key, value in merged_props.items()]
        return '; '.join(style_parts)

    def get_local_version(self):
        """
        获取本地代码的git commit sha和最新tag
        """
        import subprocess
        try:
            # 跨网络共享盘时 git 会报 dubious ownership，先设置 safe.directory
            try:
                import os
                repo_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                subprocess.run(
                    ['git', 'config', '--global', '--add', 'safe.directory', repo_path],
                    capture_output=True, timeout=5
                )
            except Exception:
                pass

            sha = subprocess.check_output(
                ['git', 'rev-parse', 'HEAD'], timeout=5
            ).decode('utf-8').strip()
            try:
                tag = subprocess.check_output(
                    ['git', 'describe', '--tags', '--abbrev=0'], timeout=5
                ).decode('utf-8').strip()
            except Exception:
                tag = ''
            return {'success': True, 'sha': sha, 'tag': tag}
        except Exception as e:
            logger.warning(f"获取本地版本失败（非致命）: {e}")
            return {'success': True, 'sha': 'unknown', 'tag': ''}

    def update_from_github(self):
        """
        自动拉取GitHub主分支最新代码，并返回本地最新tag
        """
        import subprocess
        try:
            # 检查本地是否有未提交或未推送的更改
            status_output = subprocess.check_output(['git', 'status', '--porcelain']).decode('utf-8').strip()
            if status_output:
                return {'success': False, 'message': '检测到本地有未提交的更改，请先处理后再更新。', 'needs_confirm': True}
            # 拉取最新代码
            pull = subprocess.check_output(['git', 'pull', 'origin', 'main']).decode('utf-8').strip()
            # 获取本地最新tag
            try:
                tag = subprocess.check_output(['git', 'describe', '--tags', '--abbrev=0']).decode('utf-8').strip()
            except Exception:
                tag = ''
            return {'success': True, 'message': pull, 'tag': tag}
        except Exception as e:
            logger.error(f"自动更新失败: {e}")
            return {'success': False, 'message': str(e)}