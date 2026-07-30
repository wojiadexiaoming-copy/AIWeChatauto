#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
InodeTree CLI - 微信公众号 AI 创作与自动化群发命令行工具
支持命令行调用与外部 AI Agent (如 OpenClaw, AGY, Claude Code, Cursor) 交互
"""

import sys
import os
import json
import argparse
import logging
from datetime import datetime

# 设置运行日志级别
logging.basicConfig(level=logging.WARNING, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 确保当前目录位于 sys.path 首位
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.config_service import ConfigService
from services.wechat_service import WeChatService
from services.draft_service import DraftService
from controllers.article_controller import ArticleController


def print_result(success: bool, code: int, message: str, data: dict = None, is_json: bool = False):
    """格式化标准输出结果"""
    res = {
        "success": success,
        "code": code,
        "message": message,
        "data": data or {}
    }
    if is_json:
        print(json.dumps(res, ensure_ascii=False, indent=2))
    else:
        status_str = "✅ [SUCCESS]" if success else "❌ [FAILED]"
        print(f"{status_str} {message}")
        if data:
            for k, v in data.items():
                if isinstance(v, (dict, list)):
                    print(f"  • {k}: {json.dumps(v, ensure_ascii=False)}")
                else:
                    print(f"  • {k}: {v}")
    if not success and code != 0:
        sys.exit(code)


def handle_status(args):
    """检查系统与 API 配置状态"""
    config_service = ConfigService()
    config = config_service.load_config()

    wechat_ok = bool(config.get("wechat_appid") and config.get("wechat_appsecret"))
    gemini_ok = bool(config.get("gemini_api_key"))
    deepseek_ok = bool(config.get("deepseek_api_key"))
    dashscope_ok = bool(config.get("dashscope_api_key"))
    pexels_ok = bool(config.get("pexels_api_key"))
    inodetree_ok = bool(config.get("inodetree_api_key"))
    custom_count = len(config.get("custom_providers", []))

    data = {
        "wechat_configured": wechat_ok,
        "gemini_configured": gemini_ok,
        "deepseek_configured": deepseek_ok,
        "dashscope_configured": dashscope_ok,
        "pexels_configured": pexels_ok,
        "inodetree_configured": inodetree_ok,
        "custom_providers_count": custom_count,
        "author_default": config.get("author", "默认作者"),
        "inodetree_model_default": config.get("inodetree_model", "inodetree-pro")
    }
    print_result(True, 200, "系统状态及 API 配置检测完成", data, args.json)


def handle_config(args):
    """管理或获取系统配置"""
    config_service = ConfigService()
    
    if args.set:
        config = config_service.load_config()
        for item in args.set:
            if '=' in item:
                k, v = item.split('=', 1)
                config[k.strip()] = v.strip()
        success = config_service.save_config(config)
        if success:
            print_result(True, 200, "配置修改已更新成功", {"updated_keys": [x.split('=')[0] for x in args.set if '=' in x]}, args.json)
        else:
            print_result(False, 500, "写入配置到 config.json 失败", {}, args.json)
        return

    # 显示配置
    config = config_service.load_config()
    masked_config = {}
    for k, v in config.items():
        if isinstance(v, str) and ("key" in k or "secret" in k) and v and not args.raw:
            masked_config[k] = v[:4] + "****" + v[-4:] if len(v) > 8 else "****"
        else:
            masked_config[k] = v
            
    print_result(True, 200, "读取系统配置成功", masked_config, args.json)


def handle_models(args):
    """列出可用文本与生图模型"""
    config_service = ConfigService()
    config = config_service.load_config()

    text_models = [
        {"id": "inodetree", "name": "InodeTree 模型", "type": "text"},
        {"id": "gemini", "name": "Gemini 1.5 Pro/Flash", "type": "text"},
        {"id": "deepseek", "name": "DeepSeek V3 / R1", "type": "text"},
        {"id": "dashscope", "name": "阿里云百炼 (Qwen)", "type": "text"}
    ]

    image_models = [
        {"id": "gemini", "name": "Gemini 生图", "type": "image"},
        {"id": "pexels", "name": "Pexels 高清图库", "type": "image"}
    ]

    # 自定义中转网关模型
    custom_providers = config.get("custom_providers", [])
    for p in custom_providers:
        p_name = p.get("name", p.get("id"))
        p_id = p.get("id")
        for m in p.get("models", []):
            full_id = f"custom:{p_id}:{m.get('id')}"
            m_item = {
                "id": full_id,
                "name": f"{p_name} - {m.get('name', m.get('id'))}",
                "type": m.get("type", "text"),
                "provider": p_name
            }
            if m.get("type") == "image":
                image_models.append(m_item)
            else:
                text_models.append(m_item)

    data = {
        "text_models": text_models,
        "image_models": image_models
    }
    print_result(True, 200, "获取模型列表成功", data, args.json)


def handle_scrape(args):
    """抓取微信公众号/网页文章全文"""
    url = args.url.strip()
    if not url:
        print_result(False, 400, "必须输入有效的网页 URL 链接", {}, args.json)
        return

    controller = ArticleController()
    result = controller._scrape_wechat_article(url)

    if not result:
        print_result(False, 500, f"抓取目标网页文章失败: {url}", {}, args.json)
        return

    print_result(True, 200, "文章抓取成功", result, args.json)


def handle_generate(args):
    """文章生成与二创重构"""
    controller = ArticleController()
    
    mode = args.mode
    ai_model = args.model or "inodetree"
    image_model = args.image_model or "pexels"
    
    payload = {
        "ai_model": ai_model,
        "image_model": image_model,
        "author": args.author or "",
        "word_count": str(args.word_count or 2000),
        "recreate_strength": args.strength,
        "use_original_images": args.use_ref_images
    }

    if mode == "reconstruct":
        if not args.url:
            print_result(False, 400, "二创重构模式下必须提供参考 URL (--url)", {}, args.json)
            return
        payload["recreate_urls"] = [args.url]
        payload["prompt"] = args.prompt or "请对参考文章进行深度二创重构"
    else:
        if not args.prompt and not args.title:
            print_result(False, 400, "自由创作模式下必须提供文章标题 (--title) 或 Prompt (--prompt)", {}, args.json)
            return
        payload["title"] = args.title or args.prompt
        payload["prompt"] = args.prompt or args.title

    try:
        from flask import Flask
        app = Flask(__name__)
        with app.test_request_context(json=payload):
            res = controller.generate_article()
            
        if isinstance(res, tuple):
            res_data = res[0].get_json() if hasattr(res[0], 'get_json') else res[0]
        elif hasattr(res, 'get_json'):
            res_data = res.get_json()
        else:
            res_data = res

        if res_data.get("success"):
            print_result(True, 200, "文章生成成功", res_data.get("article", res_data), args.json)
        else:
            print_result(False, 500, res_data.get("message", "文章生成失败"), res_data, args.json)
    except Exception as e:
        print_result(False, 500, f"生成过程发生未捕获异常: {str(e)}", {}, args.json)


def _process_content_images(content: str, access_token: str, wechat_service: WeChatService) -> tuple:
    """
    处理文章内容中的本地图片，上传到微信素材库并替换为微信 URL
    :param content: 原始 HTML 内容
    :param access_token: 微信 access_token
    :param wechat_service: 微信服务实例
    :return: (替换后的 HTML 内容, 第一张图片的 thumb_media_id)
    """
    import re
    
    # 匹配 cache\ 或 cache/ 开头的本地图片路径
    local_image_pattern = r'<img[^>]*src=["\']([cC]ache[\\/][^"\']+)["\'][^>]*>'
    matches = re.findall(local_image_pattern, content)
    
    processed_content = content
    uploaded_count = 0
    first_thumb_media_id = ""
    
    for idx, local_path in enumerate(matches):
        # 统一路径分隔符
        normalized_path = local_path.replace('\\', os.sep).replace('/', os.sep)
        
        # 检查文件是否存在
        if not os.path.exists(normalized_path):
            logger.warning(f"本地图片文件不存在: {normalized_path}")
            continue
        
        # 上传图片到微信素材库（用于文章正文）
        image_url = wechat_service.upload_article_image(access_token, normalized_path)
        
        if image_url:
            # 替换为微信 URL
            img_pattern = rf'<img[^>]*src=["\']{re.escape(local_path)}["\'][^>]*>'
            url_replacement = f'<img src="{image_url}" alt="文章配图" style="max-width: 100%; height: auto;">'
            processed_content = re.sub(img_pattern, url_replacement, processed_content)
            uploaded_count += 1
            logger.info(f"图片上传成功: {normalized_path} -> {image_url}")
            
            # 第一张图片同时上传为永久素材，获取 thumb_media_id 用于封面
            if idx == 0:
                res_mat = wechat_service.upload_permanent_material(access_token, normalized_path, "thumb")
                if res_mat and "media_id" in res_mat:
                    first_thumb_media_id = res_mat["media_id"]
                    logger.info(f"封面图 media_id: {first_thumb_media_id}")
        else:
            logger.warning(f"图片上传失败: {normalized_path}")
    
    if uploaded_count > 0:
        print(f"已上传 {uploaded_count} 张配图到微信素材库")
    
    return processed_content, first_thumb_media_id


def handle_draft(args):
    """上传并保存草稿至微信公众号"""
    config_service = ConfigService()
    config = config_service.load_config()

    appid = config.get("wechat_appid")
    appsecret = config.get("wechat_appsecret")

    if not appid or not appsecret:
        print_result(False, 400, "保存微信草稿失败：请先配置 wechat_appid 和 wechat_appsecret", {}, args.json)
        return

    wechat_service = WeChatService()
    token_info = wechat_service.get_access_token(appid, appsecret)
    if not token_info or not token_info.get("access_token"):
        print_result(False, 401, "获取微信 access_token 失败，请检查微信 AppID 和 Secret", {}, args.json)
        return

    access_token = token_info["access_token"]
    
    title = args.title
    content = ""

    if args.content_file:
        if not os.path.exists(args.content_file):
            print_result(False, 404, f"内容文件不存在: {args.content_file}", {}, args.json)
            return
        with open(args.content_file, "r", encoding="utf-8") as f:
            content = f.read()
    elif args.content:
        content = args.content
    else:
        print_result(False, 400, "必须指定文章正文内容 (--content 或 --content-file)", {}, args.json)
        return

    if not title:
        print_result(False, 400, "必须指定文章标题 (--title)", {}, args.json)
        return

    # 上传正文中的本地图片到微信素材库，并替换为微信 URL
    processed_content, auto_thumb_media_id = _process_content_images(content, access_token, wechat_service)
    
    thumb_media_id = ""
    # 优先使用指定的封面图，否则使用正文中第一张图片作为封面
    if args.thumb:
        if os.path.exists(args.thumb):
            res_mat = wechat_service.upload_permanent_material(access_token, args.thumb, "thumb")
            if res_mat and "media_id" in res_mat:
                thumb_media_id = res_mat["media_id"]
            else:
                print_result(False, 400, f"上传封面图素材失败: {args.thumb}", {}, args.json)
                return
        else:
            thumb_media_id = args.thumb
    elif auto_thumb_media_id:
        # 使用正文中的第一张图片作为封面
        thumb_media_id = auto_thumb_media_id
        print(f"使用正文第一张图片作为封面，media_id: {thumb_media_id}")

    # 标题截断校验 (避免 45003 错误)
    title_bytes = title.encode('utf-8')
    if len(title_bytes) > 64:
        truncated_title = ""
        for i in range(len(title)):
            if len((truncated_title + title[i]).encode('utf-8')) <= 64:
                truncated_title += title[i]
            else:
                break
        title = truncated_title
        logger.warning(f"标题超出 64 字节，已自动安全截断为: {title}")

    if not thumb_media_id:
        print_result(False, 400, "草稿需要封面图，请通过 --thumb 指定封面图文件路径，或在正文中包含至少一张本地图片", {}, args.json)
        return

    draft_data = {
        "articles": [
            {
                "title": title,
                "author": args.author or config.get("author", "AI写作助手"),
                "digest": args.digest or title,
                "content": processed_content,
                "thumb_media_id": thumb_media_id,
                "need_open_comment": 1 if args.open_comment else 0,
                "only_fans_can_comment": 0
            }
        ]
    }

    draft_service = DraftService()
    res_draft = draft_service.create_draft(access_token, draft_data)

    if res_draft and "media_id" in res_draft:
        data = {
            "media_id": res_draft["media_id"],
            "title": title,
            "author": draft_data["articles"][0]["author"]
        }
        print_result(True, 200, "微信草稿保存成功", data, args.json)
    else:
        err_msg = res_draft.get("errmsg", "创建草稿未知失败") if isinstance(res_draft, dict) else "创建草稿失败"
        print_result(False, 500, f"微信保存草稿失败: {err_msg}", res_draft or {}, args.json)


def handle_publish(args):
    """即时群发/发布微信草稿箱内容"""
    config_service = ConfigService()
    config = config_service.load_config()

    appid = config.get("wechat_appid")
    appsecret = config.get("wechat_appsecret")

    if not appid or not appsecret:
        print_result(False, 400, "发布失败：请先配置 wechat_appid 和 wechat_appsecret", {}, args.json)
        return

    wechat_service = WeChatService()
    token_info = wechat_service.get_access_token(appid, appsecret)
    if not token_info or not token_info.get("access_token"):
        print_result(False, 401, "获取微信 access_token 失败", {}, args.json)
        return

    access_token = token_info["access_token"]
    draft_service = DraftService()
    res_pub = draft_service.publish_draft(access_token, args.media_id)

    if res_pub and "publish_id" in res_pub:
        data = {
            "publish_id": res_pub["publish_id"],
            "media_id": args.media_id,
            "msg_data_id": res_pub.get("msg_data_id")
        }
        print_result(True, 200, "微信草稿发布提交成功", data, args.json)
    else:
        err_msg = res_pub.get("errmsg", "发布未知失败") if isinstance(res_pub, dict) else "发布失败"
        print_result(False, 500, f"微信草稿发布提交失败: {err_msg}", res_pub or {}, args.json)


def handle_auto(args):
    """一键流水线 (抓取 -> 重构 -> 保存草稿)"""
    url = args.url.strip()
    if not url:
        print_result(False, 400, "一键流水线必须提供目标网页 URL (--url)", {}, args.json)
        return

    if not args.json:
        print("🚀 [Step 1/3] 开始抓取微信参考文章...")
    controller = ArticleController()
    scraped = controller._scrape_wechat_article(url)

    if not scraped:
        print_result(False, 500, f"自动流水线中断：抓取文章失败 {url}", {}, args.json)
        return

    if not args.json:
        print(f"📖 [Step 2/3] 开始深度重构生成 (强度: {args.strength}%)...")
    payload = {
        "ai_model": args.model or "inodetree",
        "image_model": args.image_model or "pexels",
        "recreate_urls": [url],
        "prompt": f"根据原文进行深度重构: {scraped.get('title', '')}",
        "recreate_strength": args.strength,
        "use_original_images": args.use_ref_images
    }

    from flask import Flask
    app = Flask(__name__)
    with app.test_request_context(json=payload):
        res = controller.generate_article()
        
    if isinstance(res, tuple):
        res_data = res[0].get_json() if hasattr(res[0], 'get_json') else res[0]
    elif hasattr(res, 'get_json'):
        res_data = res.get_json()
    else:
        res_data = res

    if not res_data.get("success"):
        print_result(False, 500, f"自动流水线中断：生成失败 ({res_data.get('message')})", res_data, args.json)
        return

    article_info = res_data.get("article", res_data)
    title = article_info.get("title") or scraped.get("title")
    content = article_info.get("content") or article_info.get("html")

    if not args.json:
        print("📤 [Step 3/3] 开始保存草稿至微信公众号...")

    args.title = title
    args.content = content
    args.content_file = None
    args.thumb = None
    args.author = args.author or ""
    args.digest = title
    args.open_comment = False

    handle_draft(args)


def main():
    parser = argparse.ArgumentParser(
        description="InodeTree CLI - 微信公众号 AI 创作与自动化群发工具",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    subparsers = parser.add_subparsers(dest="command", help="可选子命令")

    # 1. status
    p_status = subparsers.add_parser("status", help="检查系统与 API 配置状态")
    p_status.add_argument("--json", action="store_true", help="输出 JSON 结构化数据")

    # 2. config
    p_config = subparsers.add_parser("config", help="查看或修改系统配置")
    p_config.add_argument("--show", action="store_true", help="查看当前配置")
    p_config.add_argument("--set", nargs="+", help="修改配置, 格式: key=value")
    p_config.add_argument("--raw", action="store_true", help="不遮蔽敏感密钥")
    p_config.add_argument("--json", action="store_true", help="输出 JSON 结构化数据")

    # 3. models
    p_models = subparsers.add_parser("models", help="列出可用文本与生图模型")
    p_models.add_argument("--json", action="store_true", help="输出 JSON 结构化数据")

    # 4. scrape
    p_scrape = subparsers.add_parser("scrape", help="抓取微信公众号文章内容")
    p_scrape.add_argument("--url", required=True, help="微信公众号/网页文章 URL")
    p_scrape.add_argument("--json", action="store_true", help="输出 JSON 结构化数据")

    # 5. generate
    p_gen = subparsers.add_parser("generate", help="创作或重构微信文章")
    p_gen.add_argument("--mode", choices=["create", "reconstruct"], default="create", help="创作模式")
    p_gen.add_argument("--title", help="文章标题")
    p_gen.add_argument("--prompt", help="提示词或主题描述")
    p_gen.add_argument("--url", help="参考文章 URL (重构模式必填)")
    p_gen.add_argument("--strength", type=int, default=70, help="重构强度 (0-100)")
    p_gen.add_argument("--use-ref-images", action="store_true", help="保留使用原参考图")
    p_gen.add_argument("--model", default="inodetree", help="使用的 AI 文本模型 ID")
    p_gen.add_argument("--image-model", default="pexels", help="使用的 AI 配图模型 ID")
    p_gen.add_argument("--word-count", type=int, default=2000, help="期望字数")
    p_gen.add_argument("--author", help="作者名称")
    p_gen.add_argument("--json", action="store_true", help="输出 JSON 结构化数据")

    # 6. draft
    p_draft = subparsers.add_parser("draft", help="上传素材并保存草稿至微信公众号")
    p_draft.add_argument("--title", help="草稿标题")
    p_draft.add_argument("--content", help="文章 HTML/文本正文")
    p_draft.add_argument("--content-file", help="正文文件路径 (HTML/Markdown)")
    p_draft.add_argument("--thumb", help="封面图文件路径或已有的 thumb_media_id")
    p_draft.add_argument("--author", help="作者名")
    p_draft.add_argument("--digest", help="摘要描述")
    p_draft.add_argument("--open-comment", action="store_true", help="开启评论")
    p_draft.add_argument("--json", action="store_true", help="输出 JSON 结构化数据")

    # 7. publish
    p_pub = subparsers.add_parser("publish", help="群发/发布指定微信草稿")
    p_pub.add_argument("--media-id", required=True, help="草稿箱 media_id")
    p_pub.add_argument("--json", action="store_true", help="输出 JSON 结构化数据")

    # 8. auto
    p_auto = subparsers.add_parser("auto", help="一键自动化流水线 (抓取 -> 重构 -> 存草稿)")
    p_auto.add_argument("--url", required=True, help="参考文章 URL")
    p_auto.add_argument("--strength", type=int, default=70, help="重构强度 (0-100)")
    p_auto.add_argument("--use-ref-images", action="store_true", help="保留使用原参考图")
    p_auto.add_argument("--model", default="inodetree", help="AI 文本模型")
    p_auto.add_argument("--image-model", default="pexels", help="AI 生图模型")
    p_auto.add_argument("--author", help="作者名称")
    p_auto.add_argument("--json", action="store_true", help="输出 JSON 结构化数据")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(0)

    dispatch_table = {
        "status": handle_status,
        "config": handle_config,
        "models": handle_models,
        "scrape": handle_scrape,
        "generate": handle_generate,
        "draft": handle_draft,
        "publish": handle_publish,
        "auto": handle_auto
    }

    handler = dispatch_table.get(args.command)
    if handler:
        handler(args)


if __name__ == "__main__":
    main()
