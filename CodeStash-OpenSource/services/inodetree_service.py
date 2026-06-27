"""
inodetree 模型服务模块
兼容 OpenAI Chat Completions API
"""

import requests
import json
import logging
import os
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

INODETREE_BASE_URL      = "https://env-00jxtxx9y58k.dev-hz.cloudbasefunction.cn/GPT_inodetree-proxy"
INODETREE_DEFAULT_MODEL = "inodetree-pro"


class InodeTreeService:
    """inodetree 模型服务类（OpenAI 兼容接口）"""

    def __init__(self, api_key: str = ""):
        self.api_key = api_key or os.environ.get("INODETREE_API_KEY", "")
        self.model = INODETREE_DEFAULT_MODEL
        self.timeout = 320   # 云函数超时 300s，Python 侧留 20s 余量
        logger.info("inodetree 服务初始化完成")

    def set_api_key(self, api_key: str):
        self.api_key = api_key

    def _headers(self):
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "X-Client-Signature": "inodetree-secured-v2.5"
        }

    def _chat(self, messages: list, max_tokens: int = 4096,
              temperature: float = 0.7) -> Optional[str]:
        """底层调用，返回文本内容"""
        text, _ = self._chat_with_usage(messages, max_tokens, temperature)
        return text

    def _chat_with_usage(self, messages: list, max_tokens: int = 4096,
                         temperature: float = 0.7) -> tuple:
        """底层调用，返回 (text, tokens_used)"""
        if not self.api_key:
            logger.error("inodetree API Key 未配置")
            return None, 0
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        try:
            resp = requests.post(
                INODETREE_BASE_URL,
                headers=self._headers(),
                json=payload,
                timeout=self.timeout   # self.timeout = 120，但文章生成可能超，用 320
            )
            if not resp.ok:
                logger.error(f"inodetree 响应非 2xx: {resp.status_code}  body={resp.text[:300]}")
            resp.raise_for_status()
            data = self._unwrap(resp)
            if data.get('error'):
                logger.error(f"inodetree 返回错误: {data['error']}")
                return None, 0
            tokens_used = data.get('usage', {}).get('total_tokens', 0) or 0
            content = data["choices"][0]["message"]["content"]
            return (content.strip() if content else None), tokens_used
        except requests.exceptions.RequestException as e:
            logger.error(f"inodetree 网络请求失败: {e}")
            return None, 0
        except (KeyError, IndexError) as e:
            logger.error(f"inodetree 响应解析失败: {e}")
            return None, 0
        except Exception as e:
            logger.error(f"inodetree 调用异常: {e}")
            return None, 0

    @staticmethod
    def _unwrap(resp) -> dict:
        """
        DCloud HTTP 触发器返回嵌套结构：
          { statusCode, headers, body: "JSON字符串" }
        先尝试解析 body，取不到则直接用整个 json
        """
        try:
            outer = resp.json()
            if isinstance(outer, dict) and 'body' in outer:
                body = outer['body']
                if isinstance(body, str):
                    return json.loads(body)
                return body
            return outer
        except Exception:
            return {}

    # ── 与其他 service 对齐的接口 ──────────────────────────────

    def generate_content(self, prompt: str, model: str = None,
                         max_tokens: int = 4096) -> Optional[str]:
        """通用文本生成"""
        text, _ = self.generate_with_usage(prompt, model, max_tokens)
        return text

    def generate_with_usage(self, prompt: str, model: str = None,
                            max_tokens: int = 4096) -> tuple:
        """通用文本生成，返回 (text, tokens_used)"""
        # 把外部传入的 inodetree 品牌名或 inodetree 真实名都统一成 inodetree-pro
        # 云函数 handleChat 里会做 MODEL_REVERSE 映射，只认 inodetree-* 前缀
        _CHAT_MODEL = 'inodetree-pro'
        if model:
            # 如果是旧的 inodetree 真实名，映射到对外名
            _MODEL_ALIAS = {
                'inodetree-2.0-flash': 'inodetree-pro',
                'inodetree-pro':   'inodetree-pro',
            }
            self.model = _MODEL_ALIAS.get(model, 'inodetree-pro')
        else:
            self.model = _CHAT_MODEL
        messages = [
            {"role": "system",
             "content": "你是一个专业的新媒体内容创作助手，擅长撰写高质量的微信公众号文章。"},
            {"role": "user", "content": prompt}
        ]
        return self._chat_with_usage(messages, max_tokens=max_tokens)

    def generate_article_content(self, title: str, model: str = None,
                                  word_count: int = None,
                                  format_template: str = "") -> Optional[str]:
        """生成完整文章 HTML"""
        from services.prompt_manager import PromptManager
        if model:
            self.model = model
        prompt = PromptManager.article_prompt(title, word_count, format_template)
        logger.info(f"[inodetree] 开始生成文章，标题: {title}")
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
            logger.info(f"[inodetree] 文章生成成功，长度: {len(result)}")
        else:
            logger.error("[inodetree] 文章生成失败")
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


    # ── 图片生成 (inodetree-image) ───────────────────────────

    def generate_image(self, prompt: str, size: str = "1024x768",
                        save_dir: str = "cache") -> Optional[str]:
        """
        文生图，返回本地保存路径
        通过云函数代理，action=image
        """
        if not self.api_key:
            logger.error("inodetree API Key 未配置")
            return None

        payload = {
            "model": "inodetree-image",
            "prompt": prompt,
            "size": size,
            "extra_body": {"response_format": "url"}
        }
        try:
            resp = requests.post(
                INODETREE_BASE_URL,
                headers={**self._headers(), "X-Action": "image"},
                json=payload,
                timeout=120
            )
            resp.raise_for_status()
            data = self._unwrap(resp)
            if data.get('error'):
                logger.error(f"inodetree 图片生成错误: {data['error']}")
                return None

            item = data.get("data", [{}])[0]
            b64  = item.get("b64_json")
            url  = item.get("url")

            if b64:
                # 云函数已帮下载转 base64，直接写文件
                import base64, os, time
                os.makedirs(save_dir, exist_ok=True)
                path = os.path.join(save_dir, f"inodetree_img_{int(time.time())}.png")
                with open(path, "wb") as f:
                    f.write(base64.b64decode(b64))
                logger.info(f"inodetree 图片已写入（base64）: {path}")
                return path
            elif url:
                # 降级：直接下载 URL
                return self._download_to_cache(url, "inodetree_img", save_dir)
            else:
                logger.error(f"inodetree 图片生成无 URL 或 base64: {data}")
                return None
        except Exception as e:
            logger.error(f"inodetree 图片生成失败: {e}")
            return None

    # ── 视频生成 (inodetree-video) ───────────────────────────

    def create_video_task(self, prompt: str, image_url: str = None,
                           width: int = 1152, height: int = 768,
                           num_frames: int = 121, frame_rate: int = 24,
                           negative_prompt: str = None) -> Optional[dict]:
        """
        提交视频生成任务（异步），通过云函数代理，action=video
        """
        if not self.api_key:
            logger.error("inodetree API Key 未配置")
            return None

        payload = {
            "model": "inodetree-video",
            "prompt": prompt,
            "width": width,
            "height": height,
            "num_frames": num_frames,
            "frame_rate": frame_rate
        }
        if image_url:
            payload["image"] = image_url
        if negative_prompt:
            payload["negative_prompt"] = negative_prompt

        try:
            resp = requests.post(
                INODETREE_BASE_URL,
                headers={**self._headers(), "X-Action": "video"},
                json=payload,
                timeout=90
            )
            resp.raise_for_status()
            data = self._unwrap(resp)
            if data.get('error'):
                logger.error(f"inodetree 视频任务错误: {data['error']}")
                return None
            logger.info(f"inodetree 视频任务创建成功: {data}")
            return {
                "task_id": data.get("task_id") or data.get("id"),
                "video_id": data.get("video_id"),
                "status": data.get("status", "queued")
            }
        except Exception as e:
            logger.error(f"inodetree 视频任务创建失败: {e}")
            return None

    def get_video_result(self, video_id: str, max_wait: int = 300) -> Optional[str]:
        """
        轮询视频结果，通过云函数代理，action=video_result
        """
        import time
        deadline = time.time() + max_wait
        while time.time() < deadline:
            try:
                resp = requests.get(
                    INODETREE_BASE_URL,
                    headers={**self._headers(), "X-Action": "video_result"},
                    params={"action": "video_result", "video_id": video_id},
                    timeout=30
                )
                resp.raise_for_status()
                data = self._unwrap(resp)
                if data.get('error'):
                    logger.error(f"inodetree 视频查询错误: {data['error']}")
                    return None
                status   = data.get("status", "")
                progress = data.get("progress", 0)
                logger.info(f"inodetree 视频状态: {status} {progress}%")
                if status == "completed":
                    video_url = (data.get("video_url") or
                                 data.get("remixed_from_video_id") or  # InodeTree 实际字段
                                 data.get("url") or
                                 data.get("video", {}).get("url"))
                    if video_url:
                        return self._download_to_cache(video_url, "inodetree_vid", "cache", ext=".mp4")
                    logger.error("inodetree 视频完成但无 URL")
                    return None
                elif status == "failed":
                    logger.error(f"inodetree 视频生成失败: {data.get('error')}")
                    return None
            except Exception as e:
                logger.error(f"inodetree 视频轮询异常: {e}")
            time.sleep(5)
        logger.error("inodetree 视频生成超时")
        return None

    def generate_video(self, prompt: str, image_url: str = None,
                        save_dir: str = "cache", max_wait: int = 300) -> Optional[str]:
        """一键文生视频/图生视频，阻塞直到完成，返回本地路径"""
        task = self.create_video_task(prompt, image_url=image_url)
        if not task:
            return None
        video_id = task.get("video_id")
        if not video_id:
            logger.error("inodetree 未返回 video_id")
            return None
        return self.get_video_result(video_id, max_wait=max_wait)

    # ── 工具方法 ─────────────────────────────────────────────────────

    def _download_to_cache(self, url: str, prefix: str,
                            save_dir: str, ext: str = ".jpg") -> Optional[str]:
        """从 URL 下载文件到本地 cache 目录"""
        import time, os
        os.makedirs(save_dir, exist_ok=True)
        ts = int(time.time())
        filename = f"{prefix}_{ts}{ext}"
        path = os.path.join(save_dir, filename)
        try:
            r = requests.get(url, timeout=120)
            r.raise_for_status()
            with open(path, "wb") as f:
                f.write(r.content)
            logger.info(f"inodetree 文件已保存: {path}")
            return path
        except Exception as e:
            logger.error(f"inodetree 下载失败 {url}: {e}")
            return None

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
