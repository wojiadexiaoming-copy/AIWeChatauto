"""
inodetree 云函数代理测试脚本
DCloud 阿里云 HTTP 触发器返回结构：
  { statusCode, headers, body: "JSON字符串" }
需要二次解析 body 才能拿到真实数据
"""

import requests
import json
import time

# ── 配置 ──────────────────────────────────────────────────────
PROXY_URL     = "https://env-00jxtxx9y58k.dev-hz.cloudbasefunction.cn/GPT_inodetree-proxy"
INODETREE_KEY = input("请输入 inodetree API Key (inodetree-xxx): ").strip()

HEADERS_BASE = {
    "Authorization": f"Bearer {INODETREE_KEY}",
    "Content-Type":  "application/json",
}

PASS = "✅ PASS"
FAIL = "❌ FAIL"
INFO = "ℹ️ "

def divider(title):
    print(f"\n{'='*55}")
    print(f"  {title}")
    print('='*55)

def parse_response(resp):
    """
    解析 DCloud HTTP 触发器响应。
    外层 HTTP 永远是 200，真实 statusCode 和数据在 body 里。
    返回 (real_status_code, real_data_dict)
    """
    outer = resp.json()
    real_status = outer.get("statusCode", resp.status_code)
    body = outer.get("body", "{}")
    if isinstance(body, str):
        try:
            real_data = json.loads(body)
        except Exception:
            real_data = {"raw": body}
    else:
        real_data = body
    return real_status, real_data

def check_no_inodetree(data):
    raw = json.dumps(data, ensure_ascii=False)
    if "inodetree" in raw.lower():
        print("  ⚠️  WARNING: 响应中包含 'inodetree' 字样，品牌屏蔽未生效！")
    else:
        print("  ✅ 品牌屏蔽正常，响应无 'inodetree' 字样")

# ── 1. 文本生成 ───────────────────────────────────────────────
def test_chat():
    divider("1. 文本生成 (X-Action: chat)")
    headers = {**HEADERS_BASE, "X-Action": "chat"}
    payload = {
        "model": "inodetree-pro",
        "messages": [{"role": "user", "content": "用一句话介绍微信公众号"}],
        "max_tokens": 100,
        "temperature": 0.7,
    }
    try:
        t0 = time.time()
        resp = requests.post(PROXY_URL, headers=headers, json=payload, timeout=30)
        elapsed = round(time.time() - t0, 2)
        status, data = parse_response(resp)

        print(f"HTTP 200 / 业务状态码: {status}  耗时: {elapsed}s")

        if status == 200 and data.get("choices"):
            content = data["choices"][0]["message"]["content"]
            model   = data.get("model", "?")
            tokens  = data.get("usage", {}).get("total_tokens", "?")
            print(f"{PASS}  模型: {model}  tokens: {tokens}")
            print(f"  回复: {content[:150]}")
            check_no_inodetree(data)
        else:
            print(f"{FAIL}")
            print(json.dumps(data, ensure_ascii=False, indent=2)[:600])
    except Exception as e:
        print(f"{FAIL}  异常: {e}")

# ── 2. 图片生成 ───────────────────────────────────────────────
def test_image():
    divider("2. 图片生成 + base64 落盘 (X-Action: image)")
    headers = {**HEADERS_BASE, "X-Action": "image"}
    payload = {
        "model": "inodetree-image",
        "prompt": "a beautiful sunset over mountain, cinematic, high quality",
        "size": "1024x768",
    }
    try:
        t0 = time.time()
        resp = requests.post(PROXY_URL, headers=headers, json=payload, timeout=120)
        elapsed = round(time.time() - t0, 2)
        status, data = parse_response(resp)

        print(f"HTTP 200 / 业务状态码: {status}  耗时: {elapsed}s")

        if status == 200 and data.get("data"):
            item  = data["data"][0]
            url   = item.get("url", "")
            b64   = item.get("b64_json", "")

            print(f"  图片 URL : {url[:100] if url else '（无）'}")
            print(f"  b64_json : {'存在，长度=' + str(len(b64)) if b64 else '❌ 不存在（云函数未部署新版）'}")

            if b64:
                import base64, os
                os.makedirs("cache", exist_ok=True)
                save_path = os.path.join("cache", f"test_cloud_img_{int(time.time())}.png")
                with open(save_path, "wb") as f:
                    f.write(base64.b64decode(b64))
                file_kb = os.path.getsize(save_path) // 1024
                print(f"{PASS}  base64 解码成功，已保存: {save_path}  ({file_kb} KB)")
            else:
                print(f"⚠️  b64_json 为空，降级走 URL 下载（SSL 可能报错）")

            check_no_inodetree(data)
        else:
            print(f"{FAIL}")
            print(json.dumps(data, ensure_ascii=False, indent=2)[:600])
    except Exception as e:
        print(f"{FAIL}  异常: {e}")

# ── 3. 视频任务提交 ───────────────────────────────────────────
def test_video_submit():
    divider("3. 视频任务提交 (X-Action: video，最多等 90s)")
    headers = {**HEADERS_BASE, "X-Action": "video"}
    payload = {
        "model": "inodetree-video",
        "prompt": "a cat walking in a sunny garden, smooth motion, high quality",
        "width":      1152,
        "height":     768,
        "num_frames": 121,   # 60fps ≈ 2s，最短视频，最快出 task
        "frame_rate": 60,
    }
    try:
        t0 = time.time()
        # InodeTree 视频提交接口本身响应较慢，给 90s
        resp = requests.post(PROXY_URL, headers=headers, json=payload, timeout=90)
        elapsed = round(time.time() - t0, 2)
        status, data = parse_response(resp)

        print(f"HTTP 200 / 业务状态码: {status}  耗时: {elapsed}s")

        if status == 200 and not data.get("error"):
            video_id = (data.get("video_id") or data.get("id")
                        or data.get("task_id") or data.get("taskId"))
            print(f"{PASS}  video_id: {video_id}")
            print(f"  完整响应: {json.dumps(data, ensure_ascii=False)[:300]}")
            check_no_inodetree(data)
            return video_id
        else:
            print(f"{FAIL}")
            print(json.dumps(data, ensure_ascii=False, indent=2)[:600])
            return None
    except requests.exceptions.Timeout:
        print(f"{FAIL}  超时（>90s），InodeTree 视频提交接口响应过慢")
        return None
    except Exception as e:
        print(f"{FAIL}  异常: {e}")
        return None

# ── 4. 视频轮询 ───────────────────────────────────────────────
def test_video_poll(video_id):
    divider(f"4. 视频轮询 (X-Action: video_result)")
    if not video_id:
        print(f"{INFO} 跳过（无 video_id）")
        return

    print(f"{INFO} video_id = {video_id}")
    print(f"{INFO} 等待 60 秒后开始轮询...")
    for i in range(60, 0, -10):
        print(f"  倒计时 {i}s...", end="\r")
        time.sleep(10)
    print()

    headers = {**HEADERS_BASE, "X-Action": "video_result"}
    MAX_ATTEMPTS = 24
    INTERVAL     = 10

    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            t0 = time.time()
            resp = requests.get(
                PROXY_URL,
                headers=headers,
                params={"action": "video_result", "video_id": video_id},
                timeout=20
            )
            elapsed = round(time.time() - t0, 2)
            status, data = parse_response(resp)

            biz_status = data.get("status", "unknown")
            progress   = data.get("progress", 0)
            print(f"[{attempt:02d}/24] 业务码:{status} 视频状态:{biz_status:12s} "
                  f"进度:{progress}%  耗时:{elapsed}s")

            if biz_status == "completed":
                video_url = (data.get("video_url") or
                             data.get("remixed_from_video_id") or  # InodeTree 实际字段
                             data.get("url") or
                             data.get("video", {}).get("url", ""))
                print(f"{PASS}  视频生成完成！")
                print(f"  URL: {video_url[:100] if video_url else '（未取到URL，打印完整响应）'}")
                if not video_url:
                    print(json.dumps(data, ensure_ascii=False, indent=2)[:800])
                check_no_inodetree(data)
                return

            if biz_status == "failed":
                print(f"{FAIL}  视频生成失败: {data.get('error') or data.get('message')}")
                return

        except Exception as e:
            print(f"[{attempt:02d}/24] 轮询异常: {e}")

        if attempt < MAX_ATTEMPTS:
            time.sleep(INTERVAL)

    print(f"⏱  24 次轮询（约4分钟）结束仍未完成，任务可能仍在进行")

# ── 5. 无效 Key 测试 ──────────────────────────────────────────
def test_invalid_key():
    divider("5. 无效密钥拦截测试")
    headers = {
        "Authorization": "Bearer inodetree-invalid-key-000",
        "Content-Type":  "application/json",
        "X-Action":      "chat",
    }
    payload = {
        "model": "inodetree-pro",
        "messages": [{"role": "user", "content": "hi"}],
        "max_tokens": 10
    }
    try:
        resp = requests.post(PROXY_URL, headers=headers, json=payload, timeout=10)
        # DCloud 外层永远 200，真实状态码在 body 里
        status, data = parse_response(resp)
        print(f"HTTP 层: {resp.status_code} / 业务状态码: {status}")
        if status == 401:
            print(f"{PASS}  无效密钥被正确拦截")
            print(f"  错误信息: {data.get('error', {}).get('message', '')}")
        else:
            print(f"{FAIL}  预期业务码 401，实际 {status}")
            print(json.dumps(data, ensure_ascii=False, indent=2)[:400])
    except Exception as e:
        print(f"{FAIL}  异常: {e}")

# ── 主流程 ────────────────────────────────────────────────────
if __name__ == "__main__":
    print(f"\n🚀 inodetree 云函数代理测试")
    print(f"   URL: {PROXY_URL}")
    print(f"   Key: {INODETREE_KEY[:20]}{'...' if len(INODETREE_KEY) > 20 else ''}")

    test_chat()
    test_image()
    video_id = test_video_submit()
    test_invalid_key()

    run_poll = input("\n是否等待视频轮询测试？(y/n，约4分钟): ").strip().lower()
    if run_poll == 'y':
        test_video_poll(video_id)
    else:
        print(f"{INFO} 跳过视频轮询，video_id = {video_id}")

    print(f"\n{'='*55}")
    print("  测试完成")
    print('='*55)
