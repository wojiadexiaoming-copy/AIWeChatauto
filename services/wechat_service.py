"""
微信服务模块
处理微信公众号API相关操作
"""

import os
import requests
import json
import logging
import time
from datetime import datetime
from typing import Dict, Any, Optional
from config.app_config import AppConfig

logger = logging.getLogger(__name__)

# 正文图片：仅支持 jpg/png，1MB
ARTICLE_IMAGE_ALLOWED_EXTS = {'.jpg', '.jpeg', '.png'}
ARTICLE_IMAGE_MAX_SIZE = 1 * 1024 * 1024  # 1MB

# 永久素材图片：支持 bmp/png/jpeg/jpg/gif，10MB
MATERIAL_IMAGE_ALLOWED_EXTS = {'.bmp', '.png', '.jpeg', '.jpg', '.gif'}
MATERIAL_IMAGE_MAX_SIZE = 10 * 1024 * 1024  # 10MB


class WeChatService:
    """微信服务类"""

    def __init__(self):
        self.base_url = AppConfig.WECHAT_BASE_URL
        self.timeout = AppConfig.API_TIMEOUT
        logger.info("微信服务初始化完成")

    def get_access_token(self, appid: str, appsecret: str) -> Optional[Dict[str, Any]]:
        """
        获取微信 access_token（稳定版接口，推荐）
        POST https://api.weixin.qq.com/cgi-bin/stable_token
        普通模式下平台会提前5分钟自动续期，无需主动刷新
        """
        url = f"{self.base_url}/cgi-bin/stable_token"
        payload = {
            "grant_type": "client_credential",
            "appid": appid,
            "secret": appsecret,
            "force_refresh": False
        }

        try:
            logger.info(f"开始获取access_token（稳定版），AppID: {appid}")
            response = requests.post(url, json=payload, timeout=self.timeout)
            response.raise_for_status()
            result = response.json()

            if 'access_token' in result:
                expires_in = result['expires_in']
                expire_time = int(time.time()) + expires_in

                token_info = {
                    'access_token': result['access_token'],
                    'expires_in': expires_in,
                    'expire_time': expire_time,
                    'expire_time_str': datetime.fromtimestamp(expire_time).strftime('%Y-%m-%d %H:%M:%S'),
                    'appid': appid,
                    'update_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }

                logger.info(f"access_token获取成功（稳定版），有效期: {expires_in}秒")
                return token_info
            else:
                error_code = result.get('errcode', 'unknown')
                error_msg = result.get('errmsg', 'unknown error')
                logger.error(f"获取access_token失败，错误码: {error_code}, 错误信息: {error_msg}")
                return None

        except requests.exceptions.RequestException as e:
            logger.error(f"获取access_token网络请求失败: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"获取access_token时发生异常: {str(e)}")
            return None

    def _check_image_file(self, image_path: str, allowed_exts: set, max_size: int, label: str) -> Optional[str]:
        """
        上传前校验图片文件格式和大小
        :return: 错误信息字符串，校验通过返回 None
        """
        ext = os.path.splitext(image_path)[1].lower()
        if ext not in allowed_exts:
            return f"{label}格式不支持：{ext}，仅支持 {allowed_exts}"
        try:
            size = os.path.getsize(image_path)
        except OSError:
            return f"{label}文件不存在或无法读取: {image_path}"
        if size > max_size:
            return f"{label}文件过大：{size / 1024 / 1024:.2f}MB，上限 {max_size / 1024 / 1024:.0f}MB"
        return None

    def _compress_image(self, image_path: str, max_bytes: int) -> Optional[str]:
        """
        压缩图片到指定字节上限，返回压缩后的临时文件路径
        使用 Pillow；若未安装则跳过返回 None
        """
        try:
            from PIL import Image
            import io, tempfile, os

            current_size = os.path.getsize(image_path)
            logger.info(f"图片压缩开始: {image_path}  原始大小={current_size/1024:.0f}KB  目标上限={max_bytes/1024:.0f}KB")

            img = Image.open(image_path).convert('RGB')

            # 先尝试缩放：按比例缩小直到文件小于目标
            quality = 85
            scale = 1.0
            tmp_path = None

            for attempt in range(8):
                if scale < 1.0:
                    w, h = img.size
                    new_w, new_h = int(w * scale), int(h * scale)
                    resized = img.resize((new_w, new_h), Image.LANCZOS)
                else:
                    resized = img

                buf = io.BytesIO()
                resized.save(buf, format='JPEG', quality=quality, optimize=True)
                size = buf.tell()

                if size <= max_bytes:
                    # 写到 cache 临时文件
                    base = os.path.splitext(image_path)[0]
                    tmp_path = base + '_compressed.jpg'
                    with open(tmp_path, 'wb') as f:
                        f.write(buf.getvalue())
                    logger.info(f"图片压缩完成: {tmp_path}  压缩后={size/1024:.0f}KB")
                    return tmp_path

                # 继续缩小
                quality = max(quality - 10, 40)
                scale *= 0.8

            logger.error(f"图片压缩后仍超限，放弃: {image_path}")
            return None

        except ImportError:
            logger.error("Pillow 未安装，无法压缩图片。请运行: pip install Pillow")
            return None
        except Exception as e:
            logger.error(f"图片压缩异常: {e}")
            return None

    def upload_article_image(self, access_token: str, image_path: str) -> Optional[str]:
        """
        上传图文消息内的图片获取URL（正文图片专用）
        限制：jpg/png，1MB，不占用素材库
        超过 1MB 时自动压缩后上传
        """
        err = self._check_image_file(image_path, ARTICLE_IMAGE_ALLOWED_EXTS, ARTICLE_IMAGE_MAX_SIZE, "正文图片")
        if err:
            # 尝试压缩后重传
            if '过大' in err:
                image_path = self._compress_image(image_path, ARTICLE_IMAGE_MAX_SIZE)
                if not image_path:
                    logger.error("图片压缩失败，跳过上传")
                    return None
            else:
                logger.error(err)
                return None

        url = f"{self.base_url}/cgi-bin/media/uploadimg"
        params = {'access_token': access_token}

        try:
            logger.info(f"开始上传图文消息图片: {image_path}")

            with open(image_path, 'rb') as f:
                files = {'media': f}
                response = requests.post(url, params=params, files=files, timeout=self.timeout)
                response.raise_for_status()
                result = response.json()

                if 'url' in result:
                    image_url = result['url']
                    logger.info(f"图片上传成功，URL: {image_url}")
                    return image_url
                else:
                    error_code = result.get('errcode', 'unknown')
                    error_msg = result.get('errmsg', 'unknown error')
                    logger.error(f"上传图文消息图片失败，错误码: {error_code}, 错误信息: {error_msg}")
                    return None

        except FileNotFoundError:
            logger.error(f"图片文件不存在: {image_path}")
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"上传图片网络请求失败: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"上传图文消息图片时发生异常: {str(e)}")
            return None

    def upload_permanent_material(self, access_token: str, file_path: str,
                                  material_type: str, description: Optional[Dict] = None) -> Optional[Dict[str, Any]]:
        """
        新增永久素材（封面图/视频/语音）
        图片限制：bmp/png/jpeg/jpg/gif，10MB
        """
        if material_type in ('image', 'thumb'):
            err = self._check_image_file(file_path, MATERIAL_IMAGE_ALLOWED_EXTS, MATERIAL_IMAGE_MAX_SIZE, "封面/永久素材图片")
            if err:
                if '过大' in err:
                    file_path = self._compress_image(file_path, MATERIAL_IMAGE_MAX_SIZE)
                    if not file_path:
                        logger.error("封面图压缩失败，跳过上传")
                        return None
                else:
                    logger.error(err)
                    return None

        url = f"{self.base_url}/cgi-bin/material/add_material"
        params = {
            'access_token': access_token,
            'type': material_type
        }

        try:
            logger.info(f"开始上传永久素材: {file_path}, 类型: {material_type}")

            with open(file_path, 'rb') as f:
                files = {'media': f}
                data = None

                if material_type == 'video' and description:
                    description_json = json.dumps(description, ensure_ascii=False)
                    files['description'] = (None, description_json)

                response = requests.post(url, params=params, files=files, data=data, timeout=self.timeout)
                response.raise_for_status()
                result = response.json()

                if 'media_id' in result:
                    logger.info(f"永久素材上传成功，media_id: {result['media_id']}")
                    return result
                else:
                    error_code = result.get('errcode', 'unknown')
                    error_msg = result.get('errmsg', 'unknown error')
                    logger.error(f"上传永久素材失败，错误码: {error_code}, 错误信息: {error_msg}")
                    return None

        except FileNotFoundError:
            logger.error(f"素材文件不存在: {file_path}")
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"上传素材网络请求失败: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"上传永久素材时发生异常: {str(e)}")
            return None

    def get_publish_status(self, access_token: str, publish_id: str) -> Optional[Dict[str, Any]]:
        """
        查询发布任务状态（轮询用）
        GET https://api.weixin.qq.com/cgi-bin/freepublish/get
        publish_status: 0=成功, 1=发布中, 2=原创声明失败, 3=常规失败, 4=审核不通过, 5=用户删除, 6=系统封禁
        """
        url = f"{self.base_url}/cgi-bin/freepublish/get"
        params = {
            'access_token': access_token,
            'publish_id': publish_id
        }

        try:
            logger.info(f"查询发布状态，publish_id: {publish_id}")
            response = requests.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            result = response.json()
            logger.info(f"发布状态查询结果: {result}")
            return result
        except requests.exceptions.RequestException as e:
            logger.error(f"查询发布状态网络请求失败: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"查询发布状态时发生异常: {str(e)}")
            return None

    def _check_image_file(self, image_path: str, allowed_exts: set,
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

    def test_connection(self, appid: str, appsecret: str) -> Dict[str, Any]:
        """
        测试微信API连接
        """
        logger.info("开始测试微信API连接")

        token_info = self.get_access_token(appid, appsecret)

        if token_info and token_info.get('access_token'):
            logger.info("微信API连接测试成功")
            return {
                'success': True,
                'message': '微信API连接成功（稳定版token）',
                'data': {
                    'access_token': token_info['access_token'][:20] + '...',
                    'expires_in': token_info['expires_in']
                }
            }
        else:
            logger.error("微信API连接测试失败")
            return {
                'success': False,
                'message': '微信API连接失败，请检查AppID和AppSecret是否正确'
            }