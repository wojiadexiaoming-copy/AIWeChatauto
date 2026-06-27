# -*- coding: utf-8 -*-
"""
添加视频生成板块：
1. article_controller.py - 收集视频参数，第四步后加第四点五步视频插入
2. templates/index.html  - 加视频配置 UI（视频数量、FPS、开关）
3. static/js/app.js      - 收集并传递视频参数
"""
import os, ast

ROOT = os.path.dirname(os.path.abspath(__file__))

# ══════════════════════════════════════════════════════════════
# 1. article_controller.py
#    a) 第四步后加"第四点六步：生成视频并插入"
#    b) response_data 里加 video_count
# ══════════════════════════════════════════════════════════════
ctrl_path = os.path.join(ROOT, 'controllers', 'article_controller.py')
ctrl = open(ctrl_path, encoding='utf-8').read()
lines = ctrl.split('\n')

# 找"第四点五步"那行
step45_idx = None
for i, l in enumerate(lines):
    if '第四点五步' in l and 'cache' in l:
        step45_idx = i
        break

print(f"第四点五步 在第 {step45_idx+1} 行")

# 找 content_with_images = self._process_images_in_content( 那块的结束（282行附近）
# 在 content_with_images 赋值之后、第四点五步之前插入视频处理
# 先找 dashscope_params=dashscope_params... 那行结束的下一行
img_call_end = None
for i, l in enumerate(lines):
    if 'dashscope_image_model_code=dashscope_image_model' in l:
        img_call_end = i + 1  # 下一行（关闭括号后）
        break

# 实际插入位置：step45_idx 之前 (即在"第四点五步"行前面加视频逻辑)
video_insert_idx = step45_idx

VIDEO_BLOCK = """\
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

"""

for j, ln in enumerate(VIDEO_BLOCK.split('\n')):
    lines.insert(video_insert_idx + j, ln)
print(f"✓ 插入视频处理块（原第 {video_insert_idx+1} 行前）")

ctrl = '\n'.join(lines)

# 在 response_data 里加 video_count
ctrl = ctrl.replace(
    "'image_count': image_count,",
    "'image_count': image_count,\n                'video_count': video_count if 'video_count' in dir() else 0,",
    1
)

# 在 _process_images_in_content 方法后面加 _process_videos_in_content 方法
# 找 get_article_preview 方法作为插入点
VIDEO_PROCESS_METHOD = '''
    def _process_videos_in_content(self, content: str, title: str, description: str,
                                    video_count: int, video_model: str = "inodetree",
                                    video_fps: int = 24, ai_model: str = "gemini") -> str:
        """
        在文章内容中均匀插入视频片段
        视频时长规则（官方建议不超过15s，否则失败概率升高）：
          24FPS → num_frames 最大 361（≈15s），推荐 ≤ 361
          30FPS → num_frames 最大 241（≈8s），推荐 ≤ 241
          60FPS → num_frames 最大 121（≈2s），推荐 ≤ 121
        num_frames 必须满足 8n+1 规则
        """
        try:
            # FPS → num_frames 映射（不超过15s且满足8n+1）
            FPS_FRAMES = {
                24: 361,   # 15.04s ≈ 15s
                30: 241,   # 8.03s
                60: 121,   # 2.02s
            }
            num_frames = FPS_FRAMES.get(video_fps, 361)

            logger.info(f"开始处理文章视频，计划生成{video_count}个视频 FPS={video_fps} frames={num_frames}")

            paragraphs = content.split('</p>')
            total_paragraphs = len(paragraphs)
            if total_paragraphs < 2 or video_count < 1:
                logger.warning("文章段落过少或视频数量小于1，跳过视频插入")
                return content

            if video_count >= total_paragraphs:
                insert_positions = list(range(1, total_paragraphs))[:video_count]
            else:
                insert_positions = [round((i + 1) * total_paragraphs / (video_count + 1))
                                    for i in range(video_count)]
            logger.info(f"计划在第{insert_positions}段后插入视频")

            generated_videos = []
            for idx, position in enumerate(insert_positions):
                try:
                    logger.info(f"生成第{idx+1}个视频，模型: {video_model}")

                    # 提取插入位置附近的段落内容作为视频提示词
                    import re
                    para_idx = max(0, position - 1)
                    para_text = paragraphs[para_idx] if para_idx < len(paragraphs) else ''
                    para_text = re.sub(r'<[^>]+>', '', para_text).strip()[:200]

                    # 构建视频提示词
                    base_prompt = (
                        f"cinematic video about {title}, "
                        f"{para_text[:100] if para_text else description}, "
                        "smooth motion, high quality, realistic"
                    )

                    video_path = None
                    if video_model == 'inodetree':
                        from services.inodetree_service import InodeTreeService
                        from services.config_service import ConfigService
                        cs = ConfigService()
                        inodetree_cfg = cs.get_inodetree_config()
                        if not inodetree_cfg.get('api_key'):
                            logger.error("InodeTree API Key 未配置，跳过视频生成")
                            continue
                        inodetree = InodeTreeService(inodetree_cfg['api_key'])
                        task = inodetree.create_video_task(
                            prompt=base_prompt,
                            width=1152, height=768,
                            num_frames=num_frames,
                            frame_rate=video_fps
                        )
                        if task and task.get('video_id'):
                            logger.info(f"视频任务已提交: {task['video_id']}，等待完成...")
                            video_path = inodetree.get_video_result(task['video_id'], max_wait=300)
                        else:
                            logger.error(f"视频任务创建失败: {task}")
                    else:
                        logger.warning(f"不支持的视频模型: {video_model}")
                        continue

                    if video_path:
                        # 生成 video 标签 HTML（微信支持 mp4）
                        video_html = (
                            f'<video src="{video_path}" controls style="max-width:100%;height:auto;" '
                            f'preload="metadata"></video>'
                        )
                        logger.info(f"第{idx+1}个视频生成成功: {video_path}")
                        generated_videos.append({
                            'local_path': video_path,
                            'video_html': video_html,
                            'position': position
                        })
                    else:
                        logger.warning(f"第{idx+1}个视频生成失败，跳过")

                except Exception as e:
                    logger.error(f"生成第{idx+1}个视频时出错: {str(e)}")

            # 按位置从后往前插入，避免位置偏移
            processed_content = content
            for vid_info in sorted(generated_videos, key=lambda x: -x['position']):
                position = vid_info['position']
                video_html = f'<p style="text-align:center;">{vid_info["video_html"]}</p>'
                parts = processed_content.split('</p>')
                if position < len(parts):
                    parts.insert(position, video_html)
                    processed_content = '</p>'.join(parts)
                    logger.info(f"在第{position}段后插入视频")

            logger.info(f"视频处理完成，共插入{len(generated_videos)}个视频")
            return processed_content

        except Exception as e:
            logger.error(f"处理视频时发生错误: {str(e)}")
            return content

'''

ctrl = ctrl.replace(
    '    def get_article_preview(self) -> Dict[str, Any]:',
    VIDEO_PROCESS_METHOD + '    def get_article_preview(self) -> Dict[str, Any]:',
    1
)

open(ctrl_path, 'w', encoding='utf-8').write(ctrl)
try:
    ast.parse(ctrl)
    print("✓ article_controller.py 语法通过")
except SyntaxError as e:
    print(f"✗ 语法错误: {e}")

# ══════════════════════════════════════════════════════════════
# 2. templates/index.html  — 加视频配置 UI
# ══════════════════════════════════════════════════════════════
html_path = os.path.join(ROOT, 'templates', 'index.html')
html = open(html_path, encoding='utf-8').read()

VIDEO_UI = '''
                        <!-- 视频生成配置 -->
                        <div class="row mb-3" id="video-config-section">
                            <div class="col-12 mb-2">
                                <div class="form-check form-switch">
                                    <input class="form-check-input" type="checkbox" id="enable-video" role="switch">
                                    <label class="form-check-label" for="enable-video">
                                        <i class="bi bi-camera-video"></i> <strong>插入视频</strong>
                                        <small class="text-muted ms-1">（InodeTree Video V2.0，异步生成）</small>
                                    </label>
                                </div>
                            </div>
                            <div id="video-params" style="display:none;">
                                <div class="row">
                                    <div class="col-4">
                                        <label for="video-count" class="form-label">视频数量</label>
                                        <input type="number" class="form-control form-control-sm" id="video-count" min="1" max="5" value="1">
                                    </div>
                                    <div class="col-4">
                                        <label for="video-fps" class="form-label">帧率 (FPS)</label>
                                        <select class="form-select form-select-sm" id="video-fps">
                                            <option value="24">24 FPS — ≤15s 推荐</option>
                                            <option value="30">30 FPS — ≤10s</option>
                                            <option value="60">60 FPS — ≤5s</option>
                                        </select>
                                    </div>
                                    <div class="col-4">
                                        <label class="form-label">预计时长</label>
                                        <div class="form-control form-control-sm bg-light text-muted" id="video-duration-hint" style="font-size:12px;">≈ 15s</div>
                                    </div>
                                </div>
                                <div class="form-text mt-1">
                                    <i class="bi bi-info-circle text-warning"></i>
                                    视频异步生成，需等待约 2-5 分钟。24FPS ≤15s / 30FPS ≤10s / 60FPS ≤5s 内成功率最高。
                                </div>
                            </div>
                        </div>
'''

# 插在"生成按钮"前
html = html.replace(
    '                        <div class="d-grid">\n                            <button type="button" class="btn btn-success" id="generate-article">',
    VIDEO_UI + '                        <div class="d-grid">\n                            <button type="button" class="btn btn-success" id="generate-article">',
    1
)

open(html_path, 'w', encoding='utf-8').write(html)
print("✓ templates/index.html 视频 UI 插入完成")

# ══════════════════════════════════════════════════════════════
# 3. static/js/app.js
#    a) generateArticle 收集 video_model/video_count/video_fps
#    b) 加开关联动 JS（放在 DOMContentLoaded 里）
# ══════════════════════════════════════════════════════════════
js_path = os.path.join(ROOT, 'static', 'js', 'app.js')
js = open(js_path, encoding='utf-8').read()

# 3a. 在 dashscope_params 收集后，try 块前，加视频参数收集
OLD_TRY = """        try {
            this.showGenerationProgress();
            Utils.addLog(`开始生成文章: ${title}，使用AI模型: ${ai_model}`);"""

NEW_TRY = """        // 收集视频参数
        const enableVideo = document.getElementById('enable-video')?.checked || false;
        const video_model = enableVideo ? 'inodetree' : '';
        const video_count = enableVideo ? (parseInt(document.getElementById('video-count')?.value || '1')) : 0;
        const video_fps = enableVideo ? (parseInt(document.getElementById('video-fps')?.value || '24')) : 24;

        try {
            this.showGenerationProgress();
            Utils.addLog(`开始生成文章: ${title}，使用AI模型: ${ai_model}`);"""

js = js.replace(OLD_TRY, NEW_TRY, 1)

# 3b. 在 API 请求体加 video 参数
OLD_REQ = """                industry, // 新增
                platform // 新增
            });"""
NEW_REQ = """                industry, // 新增
                platform, // 新增
                video_model,
                video_count,
                video_fps
            });"""
js = js.replace(OLD_REQ, NEW_REQ, 1)

# 3c. 在页面初始化 DOMContentLoaded 加视频开关联动和时长提示
OLD_INIT = """        // 文章生成事件
        const generateBtn = document.getElementById('generate-article');"""
NEW_INIT = """        // 视频开关联动
        const enableVideoChk = document.getElementById('enable-video');
        const videoParams = document.getElementById('video-params');
        const videoFpsSelect = document.getElementById('video-fps');
        const videoDurationHint = document.getElementById('video-duration-hint');

        const FPS_DURATION = { '24': '≈ 15s', '30': '≈ 10s', '60': '≈ 5s' };
        function updateVideoDurationHint() {
            if (videoDurationHint && videoFpsSelect) {
                videoDurationHint.textContent = FPS_DURATION[videoFpsSelect.value] || '≈ 15s';
            }
        }
        if (enableVideoChk && videoParams) {
            enableVideoChk.addEventListener('change', function() {
                videoParams.style.display = this.checked ? '' : 'none';
            });
        }
        if (videoFpsSelect) {
            videoFpsSelect.addEventListener('change', updateVideoDurationHint);
        }

        // 文章生成事件
        const generateBtn = document.getElementById('generate-article');"""
js = js.replace(OLD_INIT, NEW_INIT, 1)

open(js_path, 'w', encoding='utf-8').write(js)
print("✓ static/js/app.js 视频参数收集完成")

# ══════════════════════════════════════════════════════════════
# 最终语法检查
# ══════════════════════════════════════════════════════════════
print()
for f in ['controllers/article_controller.py', 'services/inodetree_service.py']:
    try:
        ast.parse(open(os.path.join(ROOT, f), encoding='utf-8').read())
        print(f"OK  {f}")
    except SyntaxError as e:
        print(f"ERR {f}: {e}")

print("\n全部完成！")
