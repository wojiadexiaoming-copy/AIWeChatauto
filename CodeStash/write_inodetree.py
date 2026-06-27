# -*- coding: utf-8 -*-
"""临时脚本：写入 InodeTree 相关代码改动"""
import os, json

ROOT = os.path.dirname(os.path.abspath(__file__))

# ─────────────────────────────────────────────
# 1. services/inodetree_service.py
# ─────────────────────────────────────────────
inodetree_service = '''\
"""
InodeTree 2.0 Flash 服务模块
兼容 OpenAI Chat Completions API
端点: https://api.inodetree.com/v1/chat/completions
"""

import requests
import logging
import os
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

INODETREE_BASE_URL = "https://api.inodetree.com/v1"
INODETREE_DEFAULT_MODEL = "inodetree-2.0-flash"


class InodeTreeService:
    """InodeTree 2.0 Flash 服务类（OpenAI 兼容接口）"""

    def __init__(self, api_key: str = ""):
        self.api_key = api_key or os.environ.get("INODETREE_API_KEY", "")
        self.model = INODETREE_DEFAULT_MODEL
        self.timeout = 120
        logger.info("InodeTreeService 初始化完成")

    def set_api_key(self, api_key: str):
        self.api_key = api_key

    def _headers(self):
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    def _chat(self, messages: list, max_tokens: int = 4096,
              temperature: float = 0.7) -> Optional[str]:
        """底层调用，返回文本内容"""
        if not self.api_key:
            logger.error("InodeTree API Key 未配置")
            return None
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        try:
            resp = requests.post(
                f"{INODETREE_BASE_URL}/chat/completions",
                headers=self._headers(),
                json=payload,
                timeout=self.timeout
            )
            resp.raise_for_status()
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            return content.strip() if content else None
        except requests.exceptions.RequestException as e:
            logger.error(f"InodeTree 网络请求失败: {e}")
            return None
        except (KeyError, IndexError) as e:
            logger.error(f"InodeTree 响应解析失败: {e}")
            return None
        except Exception as e:
            logger.error(f"InodeTree 调用异常: {e}")
            return None

    # ── 与其他 service 对齐的接口 ──────────────────────────────

    def generate_content(self, prompt: str, model: str = None,
                         max_tokens: int = 4096) -> Optional[str]:
        """通用文本生成"""
        if model:
            self.model = model
        messages = [
            {"role": "system",
             "content": "你是一个专业的新媒体内容创作助手，擅长撰写高质量的微信公众号文章。"},
            {"role": "user", "content": prompt}
        ]
        return self._chat(messages, max_tokens=max_tokens)

    def generate_article_content(self, title: str, model: str = None,
                                  word_count: int = None,
                                  format_template: str = "") -> Optional[str]:
        """生成完整文章 HTML"""
        from services.prompt_manager import PromptManager
        if model:
            self.model = model
        prompt = PromptManager.article_prompt(title, word_count, format_template)
        logger.info(f"[InodeTree] 开始生成文章，标题: {title}")
        result = self._chat(
            [
                {"role": "system",
                 "content": "你是一个专业的新媒体内容创作助手，输出严格符合要求的 HTML 格式内容。"},
                {"role": "user", "content": prompt}
            ],
            max_tokens=8192,
            temperature=0.75
        )
        if result:
            logger.info(f"[InodeTree] 文章生成成功，长度: {len(result)}")
        else:
            logger.error("[InodeTree] 文章生成失败")
        return result

    def generate_digest(self, title: str, content: str,
                        model: str = None) -> str:
        """生成文章摘要"""
        from services.prompt_manager import PromptManager
        if model:
            self.model = model
        prompt = PromptManager.digest_prompt(title, content)
        result = self._chat(
            [{"role": "user", "content": prompt}],
            max_tokens=256, temperature=0.5
        )
        return result or f"探索{title}的深度解析，获取独特见解和实用价值。"

    def generate_pexels_search_query(self, analysis_text: str,
                                      image_index: int = 1,
                                      total_images: int = 1) -> Optional[str]:
        """生成 Pexels 搜索关键词"""
        from services.prompt_manager import PromptManager
        prompt = PromptManager.pexels_search_prompt(
            analysis_text, image_index, total_images)
        return self._chat(
            [{"role": "user", "content": prompt}],
            max_tokens=100, temperature=0.3
        )

    def analyze_image_for_prompt(self, image_url: str,
                                   article_title: str = "") -> Optional[str]:
        """
        图片理解：分析图片内容，返回英文生图提示词
        image_url 须为公网可访问的 URL
        """
        if not image_url:
            return None
        messages = [{
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": (
                        f"这是一篇关于《{article_title}》的文章配图，"
                        "请分析图片内容，用英文输出一段简洁的图片生成提示词"
                        "（20词以内），描述图片主体、风格、色调，"
                        "不要包含人名或版权内容。"
                    )
                },
                {
                    "type": "image_url",
                    "image_url": {"url": image_url}
                }
            ]
        }]
        return self._chat(messages, max_tokens=200, temperature=0.4)

    def test_connection(self) -> Dict[str, Any]:
        """测试连接"""
        result = self._chat(
            [{"role": "user", "content": "reply with: ok"}],
            max_tokens=10
        )
        if result:
            return {"success": True,
                    "message": f"InodeTree 连接成功，模型: {self.model}"}
        return {"success": False,
                "message": "InodeTree 连接失败，请检查 API Key"}
'''

with open(os.path.join(ROOT, 'services', 'inodetree_service.py'), 'w', encoding='utf-8') as f:
    f.write(inodetree_service)
print("✓ services/inodetree_service.py")

# ─────────────────────────────────────────────
# 2. config_service.py — 加 inodetree 配置字段
# ─────────────────────────────────────────────
cfg_path = os.path.join(ROOT, 'services', 'config_service.py')
cfg = open(cfg_path, encoding='utf-8').read()

# 2a. default_config 里加 inodetree 字段（在 coze_token 后面）
OLD = '"coze_token": "",  # 新增coze令牌'
NEW = '''"coze_token": "",  # 新增coze令牌
            "inodetree_api_key": "",
            "inodetree_model": "inodetree-2.0-flash",'''
cfg = cfg.replace(OLD, NEW, 1)

# 2b. 加 get_inodetree_config / is_inodetree_configured 方法（在 get_coze_config 后）
OLD2 = '    def get_author_config(self) -> Dict[str, str]:'
NEW2 = '''    def get_inodetree_config(self) -> Dict[str, str]:
        """获取 InodeTree 配置"""
        config = self.load_config()
        return {
            'api_key': config.get('inodetree_api_key', ''),
            'model': config.get('inodetree_model', 'inodetree-2.0-flash')
        }

    def is_inodetree_configured(self) -> bool:
        """检查 InodeTree 是否已配置"""
        return bool(self.get_inodetree_config().get('api_key'))

    def get_author_config(self) -> Dict[str, str]:'''
cfg = cfg.replace(OLD2, NEW2, 1)

# 2c. get_config_status 加 inodetree 状态
OLD3 = "            'pexels_configured': self.is_pexels_configured(),"
NEW3 = """            'pexels_configured': self.is_pexels_configured(),
            'inodetree_configured': self.is_inodetree_configured(),"""
cfg = cfg.replace(OLD3, NEW3, 1)

with open(cfg_path, 'w', encoding='utf-8') as f:
    f.write(cfg)
print("✓ services/config_service.py")

# ─────────────────────────────────────────────
# 3. image_service.py — 加 inodetree 分支
# ─────────────────────────────────────────────
img_path = os.path.join(ROOT, 'services', 'image_service.py')
img = open(img_path, encoding='utf-8').read()

# 3a. generate_article_image 里加 inodetree 分支（在 pexels 之后）
OLD_IMG = '''            elif image_model == "pexels":
                return self._search_with_pexels(title, description, article_content, ai_model,
                                              image_index=image_index, total_images=total_images)'''
NEW_IMG = '''            elif image_model == "pexels":
                return self._search_with_pexels(title, description, article_content, ai_model,
                                              image_index=image_index, total_images=total_images)
            elif image_model == "inodetree":
                # InodeTree 不生图，走 Pexels 搜索 + InodeTree 生成搜索词
                return self._search_with_pexels(title, description, article_content, "inodetree",
                                              image_index=image_index, total_images=total_images)'''
img = img.replace(OLD_IMG, NEW_IMG, 1)

# 3b. _generate_pexels_search_query_with_ai 加 inodetree 分支
OLD_AI = '''            else:
                logger.warning(f"不支持的AI模型: {ai_model}，使用Gemini作为默认")
                search_query = self._generate_with_gemini_ai(prompt)'''
NEW_AI = '''            elif ai_model == "inodetree":
                search_query = self._generate_with_inodetree_ai(prompt)
            else:
                logger.warning(f"不支持的AI模型: {ai_model}，使用Gemini作为默认")
                search_query = self._generate_with_gemini_ai(prompt)'''
img = img.replace(OLD_AI, NEW_AI, 1)

# 3c. 加 _generate_with_inodetree_ai 方法（在 _generate_with_dashscope_ai 后，_clean_search_query 前）
OLD_CLEAN = '''    def _clean_search_query(self, search_query: str) -> str:'''
NEW_CLEAN = '''    def _generate_with_inodetree_ai(self, prompt: str) -> Optional[str]:
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

    def _clean_search_query(self, search_query: str) -> str:'''
img = img.replace(OLD_CLEAN, NEW_CLEAN, 1)

# 3d. _generate_prompt_with_ai 加 inodetree 分支
OLD_PAI = '''            # 可扩展更多模型
            else:
                return prompt'''
NEW_PAI = '''            elif ai_model == 'inodetree':
                return self._generate_prompt_with_inodetree(prompt)
            else:
                return prompt'''
img = img.replace(OLD_PAI, NEW_PAI, 1)

with open(img_path, 'w', encoding='utf-8') as f:
    f.write(img)
print("✓ services/image_service.py")

# ─────────────────────────────────────────────
# 4. wechat_service.py — 换稳定版 token 接口
# ─────────────────────────────────────────────
wx_path = os.path.join(ROOT, 'services', 'wechat_service.py')
wx = open(wx_path, encoding='utf-8').read()

OLD_TOKEN = '''        url = f"{self.base_url}/cgi-bin/token"
        params = {
            'grant_type': 'client_credential',
            'appid': appid,
            'secret': appsecret
        }

        try:
            logger.info(f"开始获取access_token，AppID: {appid}")
            response = requests.get(url, params=params, timeout=self.timeout)'''

NEW_TOKEN = '''        url = f"{self.base_url}/cgi-bin/stable_token"
        payload = {
            "grant_type": "client_credential",
            "appid": appid,
            "secret": appsecret,
            "force_refresh": False
        }

        try:
            logger.info(f"开始获取access_token（稳定版），AppID: {appid}")
            response = requests.post(url, json=payload, timeout=self.timeout)'''

wx = wx.replace(OLD_TOKEN, NEW_TOKEN, 1)

# 加图片预检验函数和 get_publish_status（在 test_connection 前插入）
OLD_TEST = '''    def test_connection(self, appid: str, appsecret: str) -> Dict[str, Any]:'''
NEW_TEST = '''    def _check_image_file(self, image_path: str, allowed_exts: set,
                          max_size: int, label: str):
        """上传前校验图片格式和大小，通过返回 None，失败返回错误字符串"""
        ext = os.path.splitext(image_path)[1].lower()
        if ext not in allowed_exts:
            return f"{label}格式不支持：{ext}，仅支持 {allowed_exts}"
        try:
            size = os.path.getsize(image_path)
        except OSError:
            return f"{label}文件不存在: {image_path}"
        if size > max_size:
            return f"{label}文件过大：{size/1024/1024:.2f}MB，上限 {max_size/1024/1024:.0f}MB"
        return None

    def get_publish_status(self, access_token: str, publish_id: str):
        """
        查询发布任务状态
        GET /cgi-bin/freepublish/get
        publish_status: 0=成功 1=发布中 2=原创失败 3=常规失败 4=审核不通过
        """
        url = f"{self.base_url}/cgi-bin/freepublish/get"
        params = {"access_token": access_token, "publish_id": publish_id}
        try:
            resp = requests.get(url, params=params, timeout=self.timeout)
            resp.raise_for_status()
            result = resp.json()
            logger.info(f"发布状态: {result}")
            return result
        except Exception as e:
            logger.error(f"查询发布状态失败: {e}")
            return None

    def test_connection(self, appid: str, appsecret: str) -> Dict[str, Any]:'''
wx = wx.replace(OLD_TEST, NEW_TEST, 1)

# 加 import os（如果没有）
if 'import os' not in wx:
    wx = wx.replace('import requests', 'import os\nimport requests', 1)

with open(wx_path, 'w', encoding='utf-8') as f:
    f.write(wx)
print("✓ services/wechat_service.py")

# ─────────────────────────────────────────────
# 5. services/draft_service.py — 加 article_type + 1MB 校验
# ─────────────────────────────────────────────
draft_path = os.path.join(ROOT, 'services', 'draft_service.py')
draft = open(draft_path, encoding='utf-8').read()

OLD_DRAFT = '''                "need_open_comment": 0,
                "only_fans_can_comment": 0
            }]'''
NEW_DRAFT = '''                "article_type": "news",
                "need_open_comment": 0,
                "only_fans_can_comment": 0
            }]'''
draft = draft.replace(OLD_DRAFT, NEW_DRAFT, 1)

OLD_VAL = '''                # 检查内容长度
                if len(article['content']) > 20000:
                    logger.error(f"文章{i+1}内容过长，超过20000字符")
                    return False'''
NEW_VAL = '''                # 检查内容字符数（官方限制 2万字符）
                if len(article['content']) > 20000:
                    logger.error(f"文章{i+1}内容过长，超过20000字符")
                    return False
                # 检查内容字节大小（官方限制 1MB）
                if len(article['content'].encode('utf-8')) > 1024 * 1024:
                    logger.error(f"文章{i+1}内容超过1MB字节限制")
                    return False'''
draft = draft.replace(OLD_VAL, NEW_VAL, 1)

with open(draft_path, 'w', encoding='utf-8') as f:
    f.write(draft)
print("✓ services/draft_service.py")

# ─────────────────────────────────────────────
# 6. controllers/article_controller.py — 加 inodetree 分支
# ─────────────────────────────────────────────
ctrl_path = os.path.join(ROOT, 'controllers', 'article_controller.py')
ctrl = open(ctrl_path, encoding='utf-8').read()

# 6a. import 区加 InodeTreeService
if 'inodetree_service' not in ctrl:
    ctrl = ctrl.replace(
        'from services.wechat_service import WeChatService',
        'from services.wechat_service import WeChatService\nfrom services.inodetree_service import InodeTreeService',
        1
    )

# 6b. __init__ 加 self.inodetree_service
OLD_INIT = '        self.history_service = HistoryService()\n        logger.info("文章控制器初始化完成")'
NEW_INIT = '        self.history_service = HistoryService()\n        self.inodetree_service = InodeTreeService()\n        logger.info("文章控制器初始化完成")'
ctrl = ctrl.replace(OLD_INIT, NEW_INIT, 1)

# 6c. generate_article: ai_model 检查加 inodetree 分支（在 dashscope elif 后）
OLD_CHECK = '''            else:
                return {
                    'success': False,
                    'message': f'不支持的AI模型: {ai_model}'
                }

            # 新增：接收前端传递的字数'''
NEW_CHECK = '''            elif ai_model == 'inodetree':
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

            # 新增：接收前端传递的字数'''
ctrl = ctrl.replace(OLD_CHECK, NEW_CHECK, 1)

# 6d. generate_article_content 调用加 inodetree 分支
OLD_GEN = '''            elif ai_model == 'dashscope':
                content = self.dashscope_service.generate_article_content(title,
 model_name, word_count, format_template=format_template)
            else:
                return {
                    'success': False,
                    'message': f'不支持的AI模型: {ai_model}'
                }'''
NEW_GEN = '''            elif ai_model == 'dashscope':
                content = self.dashscope_service.generate_article_content(title,
 model_name, word_count, format_template=format_template)
            elif ai_model == 'inodetree':
                content = self.inodetree_service.generate_article_content(title, model_name, word_count, format_template=format_template)
            else:
                return {
                    'success': False,
                    'message': f'不支持的AI模型: {ai_model}'
                }'''
ctrl = ctrl.replace(OLD_GEN, NEW_GEN, 1)

# 6e. generate_digest 调用加 inodetree
OLD_DIG = '''            else:
                digest = f"探索{title}的深度解析，获取独特见解和实用价值。"'''
NEW_DIG = '''            elif ai_model == 'inodetree':
                digest = self.inodetree_service.generate_digest(title, content, model_name)
            else:
                digest = f"探索{title}的深度解析，获取独特见解和实用价值。"'''
ctrl = ctrl.replace(OLD_DIG, NEW_DIG, 1)

with open(ctrl_path, 'w', encoding='utf-8') as f:
    f.write(ctrl)
print("✓ controllers/article_controller.py")

# ─────────────────────────────────────────────
# 7. templates/index.html — 加 InodeTree 配置区 + 模型选项
# ─────────────────────────────────────────────
html_path = os.path.join(ROOT, 'templates', 'index.html')
html = open(html_path, encoding='utf-8').read()

# 7a. 在 Pexels 配置区前插入 InodeTree 配置区
INODETREE_CONFIG_HTML = '''
                    <!-- InodeTree 配置 -->
                    <div class="config-section">
                        <h6><i class="bi bi-lightning-charge"></i> InodeTree 2.0 Flash 配置</h6>
                        <div class="mb-3">
                            <label for="inodetree-api-key" class="form-label">API密钥</label>
                            <input type="password" class="form-control" id="inodetree-api-key" placeholder="请输入 InodeTree API Key">
                            <div class="form-text">
                                InodeTree 2.0 Flash，256K 上下文，支持图片理解，兼容 OpenAI 接口。
                                <a href="https://inodetree-ai.com" target="_blank" class="text-decoration-none">
                                    <i class="bi bi-link-45deg"></i> 获取 API Key
                                </a>
                            </div>
                        </div>
                        <div class="mb-3">
                            <label for="inodetree-model" class="form-label">模型选择</label>
                            <select class="form-select" id="inodetree-model">
                                <option value="inodetree-2.0-flash">InodeTree 2.0 Flash</option>
                            </select>
                        </div>
                        <div class="d-flex gap-2">
                            <button type="button" class="btn btn-outline-primary btn-sm" id="test-inodetree">
                                <i class="bi bi-plug"></i> 测试连接
                            </button>
                            <span class="badge bg-secondary" id="inodetree-status">未配置</span>
                        </div>
                    </div>
'''

OLD_PEXELS = '                    <!-- Pexels配置 -->'
html = html.replace(OLD_PEXELS, INODETREE_CONFIG_HTML + '                    <!-- Pexels配置 -->', 1)

# 7b. AI模型选择下拉加 InodeTree
OLD_AI_OPT = '                                <option value="dashscope">阿里云百炼</option>\n                            </select>'
NEW_AI_OPT = '                                <option value="dashscope">阿里云百炼</option>\n                                <option value="inodetree">InodeTree 2.0 Flash</option>\n                            </select>'
html = html.replace(OLD_AI_OPT, NEW_AI_OPT, 1)

# 7c. 生图模型选择也加 InodeTree（pexels 前）
OLD_IMG_OPT = '                                    <option value="pexels">Pexels</option>'
NEW_IMG_OPT = '                                    <option value="inodetree">InodeTree+Pexels</option>\n                                    <option value="pexels">Pexels</option>'
html = html.replace(OLD_IMG_OPT, NEW_IMG_OPT, 1)

with open(html_path, 'w', encoding='utf-8') as f:
    f.write(html)
print("✓ templates/index.html")

print("\n全部完成！")
