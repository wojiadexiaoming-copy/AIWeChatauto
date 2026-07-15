"""
自定义中转网关服务模块
兼容 OpenAI Chat Completions 和 Image Generations API
"""

import requests
import json
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class CustomGatewayService:
    """通用 OpenAI 兼容网关服务类"""
    
    def __init__(self, api_base: str, api_key: str):
        self.api_base = api_base.rstrip('/')
        self.api_key = api_key
        self.timeout = 300  # 生文可能耗时较长
        logger.info(f"自定义网关服务初始化完成，Base URL: {self.api_base}")

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    def generate_content_with_usage(self, prompt: str, model: str, max_tokens: int = 4096) -> tuple:
        """
        生成文本内容并返回 (text, tokens_used)
        """
        if not self.api_key:
            logger.error("未配置 API Key")
            return None, 0
            
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": "你是一个专业的新媒体内容创作助手，输出严格符合要求的 HTML 格式内容。"},
                {"role": "user", "content": prompt}
            ],
            "max_tokens": max_tokens,
            "temperature": 0.7
        }
        
        try:
            url = f"{self.api_base}/chat/completions"
            logger.info(f"向自定义网关发起文本请求: {url}, 模型: {model}, max_tokens: {max_tokens}")
            resp = requests.post(
                url,
                headers=self._headers(),
                json=payload,
                timeout=self.timeout
            )
            
            if not resp.ok:
                logger.error(f"自定义网关响应非 2xx: {resp.status_code} body={resp.text[:300]}")
            resp.raise_for_status()
            
            data = resp.json()
            tokens_used = data.get('usage', {}).get('total_tokens', 0) or 0
            if data.get("choices") and len(data["choices"]) > 0:
                content = data["choices"][0]["message"]["content"]
                return content.strip(), tokens_used
            else:
                logger.error(f"自定义网关返回的数据格式不符合 OpenAI 规范: {data}")
                return None, 0
                
        except Exception as e:
            logger.error(f"自定义网关调用文本生成异常: {e}")
            return None, 0

    def generate_image(self, prompt: str, model: str, save_dir: str = "cache") -> Optional[str]:
        """
        生成图片，返回本地保存路径
        """
        if not self.api_key:
            logger.error("未配置 API Key")
            return None
            
        payload = {
            "model": model,
            "prompt": prompt,
            "n": 1,
            "size": "1024x1024",
            "response_format": "url"
        }
        
        try:
            url = f"{self.api_base}/images/generations"
            logger.info(f"向自定义网关发起图片生成请求: {url}, 模型: {model}")
            resp = requests.post(
                url,
                headers=self._headers(),
                json=payload,
                timeout=120
            )
            
            if not resp.ok:
                logger.error(f"自定义网关生图响应非 2xx: {resp.status_code} body={resp.text[:300]}")
            resp.raise_for_status()
            
            data = resp.json()
            if data.get("data") and len(data["data"]) > 0:
                item = data["data"][0]
                img_url = item.get("url")
                b64 = item.get("b64_json")
                
                import os, time
                os.makedirs(save_dir, exist_ok=True)
                
                if b64:
                    import base64
                    path = os.path.join(save_dir, f"custom_img_{int(time.time())}.png")
                    with open(path, "wb") as f:
                        f.write(base64.b64decode(b64))
                    logger.info(f"成功保存自定义网关返回的 Base64 图片: {path}")
                    return path
                elif img_url:
                    filename = f"custom_img_{int(time.time())}.png"
                    image_path = os.path.join(save_dir, filename)
                    img_resp = requests.get(img_url, timeout=30)
                    if img_resp.status_code == 200:
                        with open(image_path, "wb") as f:
                            f.write(img_resp.content)
                        logger.info(f"成功保存自定义网关下载的图片: {image_path}")
                        return image_path
                    else:
                        logger.error(f"下载自定义网关图片链接失败，状态码: {img_resp.status_code}")
                        return None
            
            logger.error(f"自定义网关生图返回数据无效: {data}")
            return None
            
        except Exception as e:
            logger.error(f"自定义网关图片生成异常: {e}")
            return None
