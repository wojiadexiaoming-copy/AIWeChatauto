import urllib.request, re

html = urllib.request.urlopen('http://127.0.0.1:5000/').read().decode('utf-8')

# dashscope 下拉
items = re.findall(r'data-value=["\']([^"\']+)["\']', html)
print("dashscope dropdown items:", items)

# JS 文件
for s in ['tab_create.js', 'tab_config.js', 'tab_topup.js', 'app.js']:
    print("  " + s + ":", s in html)

# 关键功能 ID 全量检查
must_have = [
    'article-title', 'ai-model-select', 'image-model-select',
    'generate-article', 'save-draft', 'publish-article',
    'article-preview', 'history-list',
    'enable-video', 'video-count', 'video-fps',
    'dashscope-extra-fields', 'dashscope-image-model-value',
    'wechat-appid', 'gemini-api-key', 'deepseek-api-key',
    'dashscope-api-key', 'inodetree-api-key', 'pexels-api-key',
    'firecrawl-api-key', 'coze_token', 'save-config',
    'publish-history', 'model-status-list', 'total-articles',
    'main-tabs', 'toast-container',
]
missing = [i for i in must_have if ('id="' + i + '"') not in html and ("id='" + i + "'") not in html]
print("\n缺少的 ID:", missing if missing else "全部存在 ✓")
print("HTML 总长度:", len(html), "字节")
