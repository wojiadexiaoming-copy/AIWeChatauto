# -*- coding: utf-8 -*-
"""第三批改动：
1. article_controller.py - 补上抖音流程 inodetree 分支 + image_model inodetree 分支
2. inodetree_service.py - 加图片生成(inodetree-image-2.1-flash) 和视频生成(inodetree-video-v2.0)
3. image_service.py - 连接 inodetree 图片生成方法
4. index.html - 生图模型选项改为 InodeTree Image + InodeTree+Pexels 两个，去掉旧的 inodetree 选项
"""
import os, re

ROOT = os.path.dirname(os.path.abspath(__file__))

# ─────────────────────────────────────────────
# 1. inodetree_service.py  — 加图片生成 & 视频生成
# ─────────────────────────────────────────────
inodetree_path = os.path.join(ROOT, 'services', 'inodetree_service.py')
inodetree = open(inodetree_path, encoding='utf-8').read()

IMAGE_VIDEO_CODE = '''
    # ── 图片生成 (inodetree-image-2.1-flash) ─────────────────────────────

    def generate_image(self, prompt: str, size: str = "1024x768",
                        save_dir: str = "cache") -> Optional[str]:
        """
        文生图，返回本地保存路径
        端点: POST /v1/images/generations
        模型: inodetree-image-2.1-flash
        """
        if not self.api_key:
            logger.error("InodeTree API Key 未配置")
            return None

        payload = {
            "model": "inodetree-image-2.1-flash",
            "prompt": prompt,
            "size": size,
            "extra_body": {"response_format": "url"}
        }
        try:
            resp = requests.post(
                f"{INODETREE_BASE_URL}/images/generations",
                headers=self._headers(),
                json=payload,
                timeout=120
            )
            resp.raise_for_status()
            data = resp.json()
            image_url = data["data"][0].get("url")
            if not image_url:
                logger.error(f"InodeTree 图片生成无 URL 返回: {data}")
                return None
            # 下载到本地
            return self._download_to_cache(image_url, "inodetree_img", save_dir)
        except Exception as e:
            logger.error(f"InodeTree 图片生成失败: {e}")
            return None

    # ── 视频生成 (inodetree-video-v2.0) ──────────────────────────────────

    def create_video_task(self, prompt: str, image_url: str = None,
                           width: int = 1152, height: int = 768,
                           num_frames: int = 121, frame_rate: int = 24,
                           negative_prompt: str = None) -> Optional[dict]:
        """
        提交视频生成任务（异步），返回 {task_id, video_id}
        端点: POST /v1/videos
        """
        if not self.api_key:
            logger.error("InodeTree API Key 未配置")
            return None

        payload = {
            "model": "inodetree-video-v2.0",
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
                f"{INODETREE_BASE_URL}/videos",
                headers=self._headers(),
                json=payload,
                timeout=60
            )
            resp.raise_for_status()
            data = resp.json()
            logger.info(f"InodeTree 视频任务创建成功: {data}")
            return {
                "task_id": data.get("task_id") or data.get("id"),
                "video_id": data.get("video_id"),
                "status": data.get("status", "queued")
            }
        except Exception as e:
            logger.error(f"InodeTree 视频任务创建失败: {e}")
            return None

    def get_video_result(self, video_id: str, max_wait: int = 300) -> Optional[str]:
        """
        轮询视频结果，完成后下载到本地，返回本地路径
        推荐用 video_id 查询
        """
        import time
        headers = self._headers()
        url = f"https://api.inodetree.com/inodetreeapi"
        params = {"video_id": video_id}
        deadline = time.time() + max_wait
        while time.time() < deadline:
            try:
                resp = requests.get(url, headers=headers, params=params, timeout=30)
                resp.raise_for_status()
                data = resp.json()
                status = data.get("status", "")
                progress = data.get("progress", 0)
                logger.info(f"InodeTree 视频状态: {status} {progress}%")
                if status == "completed":
                    video_url = data.get("remixed_from_video_id")  # 最终视频 URL
                    if video_url:
                        return self._download_to_cache(video_url, "inodetree_vid", "cache", ext=".mp4")
                    logger.error("InodeTree 视频完成但无 URL")
                    return None
                elif status == "failed":
                    logger.error(f"InodeTree 视频生成失败: {data.get('error')}")
                    return None
            except Exception as e:
                logger.error(f"InodeTree 视频轮询异常: {e}")
            time.sleep(5)
        logger.error("InodeTree 视频生成超时")
        return None

    def generate_video(self, prompt: str, image_url: str = None,
                        save_dir: str = "cache", max_wait: int = 300) -> Optional[str]:
        """一键文生视频/图生视频，阻塞直到完成，返回本地路径"""
        task = self.create_video_task(prompt, image_url=image_url)
        if not task:
            return None
        video_id = task.get("video_id")
        if not video_id:
            logger.error("InodeTree 未返回 video_id")
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
            logger.info(f"InodeTree 文件已保存: {path}")
            return path
        except Exception as e:
            logger.error(f"InodeTree 下载失败 {url}: {e}")
            return None
'''

# 插到 test_connection 前
inodetree = inodetree.replace(
    '    def test_connection(self) -> Dict[str, Any]:',
    IMAGE_VIDEO_CODE + '\n    def test_connection(self) -> Dict[str, Any]:',
    1
)
open(inodetree_path, 'w', encoding='utf-8').write(inodetree)
print("✓ services/inodetree_service.py  (图片+视频方法)")

# ─────────────────────────────────────────────
# 2. image_service.py — 加 _generate_with_inodetree_image 方法
#    并在 generate_article_image 里接入
# ─────────────────────────────────────────────
img_path = os.path.join(ROOT, 'services', 'image_service.py')
img = open(img_path, encoding='utf-8').read()

# 2a. generate_article_image 里 inodetree 分支改为调用真实生图
OLD_INODETREE_BRANCH = '''            elif image_model == "inodetree":
                # InodeTree 不生图，走 Pexels 搜索 + InodeTree 生成搜索词
                return self._search_with_pexels(title, description, article_content, "inodetree",
                                              image_index=image_index, total_images=total_images)'''
NEW_INODETREE_BRANCH = '''            elif image_model == "inodetree":
                # InodeTree Image 2.1 Flash 直接生图
                return self._generate_with_inodetree_image(final_prompt)
            elif image_model == "inodetree_pexels":
                # InodeTree 生成搜索词 + Pexels 取图
                return self._search_with_pexels(title, description, article_content, "inodetree",
                                              image_index=image_index, total_images=total_images)'''
img = img.replace(OLD_INODETREE_BRANCH, NEW_INODETREE_BRANCH, 1)

# 2b. 加 _generate_with_inodetree_image 方法（在 _generate_with_inodetree_ai 前）
OLD_BEFORE = '''    def _generate_with_inodetree_ai(self, prompt: str) -> Optional[str]:'''
NEW_BEFORE = '''    def _generate_with_inodetree_image(self, prompt: str) -> Optional[str]:
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

    def _generate_with_inodetree_ai(self, prompt: str) -> Optional[str]:'''
img = img.replace(OLD_BEFORE, NEW_BEFORE, 1)

open(img_path, 'w', encoding='utf-8').write(img)
print("✓ services/image_service.py  (inodetree 图片生成)")

# ─────────────────────────────────────────────
# 3. article_controller.py
#    3a. 抖音流程 ai_model 分支补 inodetree
#    3b. image_model 选 inodetree 时不显示 dashscope 参数区（前端处理，后端 generate_article_image 已对接）
# ─────────────────────────────────────────────
ctrl_path = os.path.join(ROOT, 'controllers', 'article_controller.py')
ctrl = open(ctrl_path, encoding='utf-8').read()

# 3a. 抖音流程里 elif ai_model == 'dashscope' 后补 inodetree（紧接着 else 报错之前）
# 定位：抖音流程最后 else 之前
OLD_DOUYIN_ELSE = '''                else:
                    logger.error(f"不支持的AI模型: {ai_model}")
                    return {
                        'success': False,
                        'message': f'不支持的AI模型: {ai_model}'
                    }
                logger.info(f"大模型返回标题：{title}")'''
NEW_DOUYIN_ELSE = '''                elif ai_model == 'inodetree':
                    inodetree_config = self.config_service.get_inodetree_config()
                    if not inodetree_config['api_key']:
                        return {'success': False, 'message': '请先配置 InodeTree API Key'}
                    self.inodetree_service.set_api_key(inodetree_config['api_key'])
                    model_name = inodetree_config.get('model', 'inodetree-2.0-flash')
                    title = self.inodetree_service.generate_content(prompt, model_name)
                else:
                    logger.error(f"不支持的AI模型: {ai_model}")
                    return {
                        'success': False,
                        'message': f'不支持的AI模型: {ai_model}'
                    }
                logger.info(f"大模型返回标题：{title}")'''
if OLD_DOUYIN_ELSE in ctrl:
    ctrl = ctrl.replace(OLD_DOUYIN_ELSE, NEW_DOUYIN_ELSE, 1)
    print("✓ article_controller.py 抖音分支补 inodetree")
else:
    print("⚠ 抖音分支未找到，跳过")

open(ctrl_path, 'w', encoding='utf-8').write(ctrl)
print("✓ controllers/article_controller.py")

# ─────────────────────────────────────────────
# 4. templates/index.html
#    4a. 生图模型选项：inodetree → "InodeTree Image 2.1"，新增 "InodeTree+Pexels"
#    4b. AI模型选择中 inodetree 选项文字更新
#    4c. 配置区去掉 inodetree model 选择（只需填 API Key，三个子模型固定）
# ─────────────────────────────────────────────
html_path = os.path.join(ROOT, 'templates', 'index.html')
html = open(html_path, encoding='utf-8').read()

# 4a. 生图选项改名
html = html.replace(
    '<option value="inodetree">InodeTree+Pexels</option>',
    '<option value="inodetree">InodeTree Image 2.1 Flash</option>\n                                    <option value="inodetree_pexels">InodeTree+Pexels 搜图</option>',
    1
)

# 4b. 配置区简化——去掉模型下拉（三个模型固定，不需要选）
OLD_CFG_MODEL = '''                        <div class="mb-3">
                            <label for="inodetree-model" class="form-label">模型选择</label>
                            <select class="form-select" id="inodetree-model">
                                <option value="inodetree-2.0-flash">InodeTree 2.0 Flash</option>
                            </select>
                        </div>'''
NEW_CFG_MODEL = '''                        <div class="mb-3">
                            <div class="form-text text-muted" style="margin-top:4px;">
                                <i class="bi bi-info-circle"></i>
                                模型固定：文本 <code>inodetree-2.0-flash</code> &nbsp;|&nbsp;
                                图片 <code>inodetree-image-2.1-flash</code> &nbsp;|&nbsp;
                                视频 <code>inodetree-video-v2.0</code>
                            </div>
                        </div>'''
if OLD_CFG_MODEL in html:
    html = html.replace(OLD_CFG_MODEL, NEW_CFG_MODEL, 1)
    print("✓ index.html 配置区模型选择简化")
else:
    print("⚠ 配置区模型选择未找到，跳过")

open(html_path, 'w', encoding='utf-8').write(html)
print("✓ templates/index.html")

# ─────────────────────────────────────────────
# 5. app.js — getConfigFormData 去掉 inodetree_model（配置区已无此字段）
#             fillConfigForm 去掉 inodetree-model 赋值
# ─────────────────────────────────────────────
js_path = os.path.join(ROOT, 'static', 'js', 'app.js')
js = open(js_path, encoding='utf-8').read()

# 去掉 inodetree_model 从表单取值
js = js.replace(
    "        const inodetree_model = document.getElementById('inodetree-model')?.value || 'inodetree-2.0-flash';\n",
    "", 1
)
# 去掉 inodetree_model 在 return 对象里
js = js.replace(
    "            inodetree_api_key,\n            inodetree_model,\n            coze_token,",
    "            inodetree_api_key,\n            coze_token,",
    1
)
# 去掉 fillConfigForm 里的 inodetree-model 赋值
js = js.replace(
    """        if (document.getElementById('inodetree-model')) {
            document.getElementById('inodetree-model').value = config.inodetree_model || 'inodetree-2.0-flash';
        }
        if (document.getElementById('coze_token')) {""",
    "        if (document.getElementById('coze_token')) {",
    1
)

open(js_path, 'w', encoding='utf-8').write(js)
print("✓ static/js/app.js")

# ─────────────────────────────────────────────
# 语法检查
# ─────────────────────────────────────────────
import ast
files = [
    'services/inodetree_service.py',
    'services/image_service.py',
    'controllers/article_controller.py',
]
print()
for f in files:
    try:
        ast.parse(open(os.path.join(ROOT, f), encoding='utf-8').read())
        print(f"OK  {f}")
    except SyntaxError as e:
        print(f"ERR {f}: {e}")

print("\n全部完成！")
