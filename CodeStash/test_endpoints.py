"""端到端接口验证"""
import urllib.request, json, sys

BASE = 'http://127.0.0.1:5000'
OK = 0; FAIL = 0

def req(method, path, body=None):
    url = BASE + path
    data = json.dumps(body).encode() if body else None
    headers = {'Content-Type': 'application/json'} if data else {}
    r = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(r, timeout=10) as resp:
            return json.loads(resp.read())
    except Exception as e:
        return {'_error': str(e)}

def chk(label, result, key='success'):
    global OK, FAIL
    ok = result.get(key) is True or (key == '_no_error' and '_error' not in result)
    sym = '✓' if ok else '✗'
    print(f"  {sym} {label}")
    if not ok:
        FAIL += 1
        if '_error' in result: print(f"    └ {result['_error']}")
        elif 'message' in result: print(f"    └ {result['message']}")
    else:
        OK += 1

print("=== API 端点验证 ===\n")

print("[GET]")
chk("GET /",               req('GET', '/'), '_no_error')
chk("GET /api/config",     req('GET', '/api/config'))
chk("GET /api/config-status", req('GET', '/api/config-status'))
chk("GET /api/generation-history", req('GET', '/api/generation-history'))
chk("GET /api/publish-history",    req('GET', '/api/publish-history'))
chk("GET /api/style-templates",    req('GET', '/api/style-templates'))
chk("GET /api/local_version",      req('GET', '/api/local_version'), '_no_error')
chk("GET /api/get_ip",             req('GET', '/api/get_ip'), '_no_error')

print("\n[POST config]")
cfg = req('GET', '/api/config').get('data', {})
save_r = req('POST', '/api/config', {
    'wechat_appid':   cfg.get('wechat_appid',''),
    'wechat_appsecret': cfg.get('wechat_appsecret',''),
    'gemini_api_key': cfg.get('gemini_api_key',''),
    'gemini_model':   cfg.get('gemini_model','gemini-2.5-flash'),
    'deepseek_api_key': cfg.get('deepseek_api_key',''),
    'deepseek_model': cfg.get('deepseek_model','deepseek-chat'),
    'dashscope_api_key': cfg.get('dashscope_api_key',''),
    'dashscope_model': cfg.get('dashscope_model','qwen-turbo'),
    'pexels_api_key': cfg.get('pexels_api_key',''),
    'firecrawl_api_key': cfg.get('firecrawl_api_key',''),
    'inodetree_api_key':  cfg.get('inodetree_api_key',''),
    'coze_token':     cfg.get('coze_token',''),
    'coze_workflow_id': cfg.get('coze_workflow_id',''),
    'author':         cfg.get('author','AI笔记'),
    'content_source_url': cfg.get('content_source_url',''),
})
chk("POST /api/config (保存配置)", save_r)

print("\n[POST generate-article (InodeTree，最重要的流程)]")
gen_r = req('POST', '/api/generate-article', {
    'title': '测试文章标题',
    'word_count': 500,
    'image_count': 0,
    'ai_model': 'inodetree',
    'image_model': 'pexels',
    'video_model': '',
    'video_count': 0,
    'video_fps': 24,
    'format_template': '',
    'industry': '',
    'platform': '',
})
chk("POST /api/generate-article", gen_r)
media_id = None
if gen_r.get('success'):
    data = gen_r.get('data', {})
    print(f"    └ 标题: {data.get('title','')}")
    print(f"    └ 内容长度: {data.get('content_length',0)} 字符")
    print(f"    └ 配图数量: {data.get('image_count',0)}")

print(f"\n{'='*40}")
print(f"通过: {OK}  失败: {FAIL}")
sys.exit(0 if FAIL == 0 else 1)
