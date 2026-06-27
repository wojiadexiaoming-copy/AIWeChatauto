"""完整项目审计：找出所有残留问题"""
import re, os, json

ROOT = os.path.dirname(os.path.abspath(__file__))

def read(path):
    return open(os.path.join(ROOT, path), encoding='utf-8').read()

issues = []

# ── 1. 检查三个 JS 文件里引用了但 HTML 里不存在的 ID ──
html = (read('templates/tab_create.html') +
        read('templates/tab_config.html') +
        read('templates/tab_topup.html'))

html_ids = set(re.findall(r'id=["\']([^"\']+)["\']', html))

for js_file in ['tab_create.js', 'tab_config.js', 'tab_topup.js']:
    js = read(f'static/js/{js_file}')
    # getElementById 调用
    refs = re.findall(r'getElementById\(["\']([^"\']+)["\']', js)
    for ref in refs:
        if ref not in html_ids:
            issues.append(f"[{js_file}] getElementById('{ref}') → HTML 中不存在该 ID")

# ── 2. 检查 base.html 中 include 的文件是否存在 ──
base = read('templates/base.html')
includes = re.findall(r"{%\s*include\s*['\"]([^'\"]+)['\"]", base)
for inc in includes:
    path = os.path.join(ROOT, 'templates', inc)
    if not os.path.exists(path):
        issues.append(f"[base.html] include '{inc}' 文件不存在")

# ── 3. 检查 base.html 引用的 JS/CSS 静态文件是否存在 ──
static_refs = re.findall(r"url_for\('static',\s*filename='([^']+)'\)", base)
for ref in static_refs:
    path = os.path.join(ROOT, 'static', ref)
    if not os.path.exists(path):
        issues.append(f"[base.html] static/{ref} 文件不存在")

# ── 4. 检查 app_new.py 路由是否已指向 base.html ──
app = read('app_new.py')
if "render_template('index.html')" in app:
    issues.append("[app_new.py] 仍在使用 index.html，未切换到 base.html")
if "render_template('base.html')" in app:
    print("✓ 路由已切换到 base.html")

# ── 5. 检查临时脚本是否需要清理 ──
temp_scripts = [f for f in os.listdir(ROOT)
                if f.startswith(('fix_', 'write_', 'verify_', 'test_', 'extract_', 'audit', 'add_video'))
                and f.endswith('.py')]
if temp_scripts:
    print(f"  临时脚本（可清理）: {temp_scripts}")

# ── 6. 检查关键功能路由 ──
must_routes = ['/api/generate-article', '/api/save-draft', '/api/publish-draft',
               '/api/config', '/api/test-wechat', '/api/test-inodetree',
               '/api/generation-history', '/api/publish-history',
               '/api/config-status', '/api/style-templates']
for route in must_routes:
    if route not in app:
        issues.append(f"[app_new.py] 缺少路由 {route}")

# ── 7. 检查 tab_create.js 关键函数 ──
crt_js = read('static/js/tab_create.js')
must_fns = ['generateArticle', 'saveDraft', 'publishArticle', 'renderPreview',
            'loadHistory', 'initTitleModeToggle', 'initVideoToggle',
            'initImageModelToggle', 'initDashscopeDropdown', 'copyHTML']
for fn in must_fns:
    if fn not in crt_js:
        issues.append(f"[tab_create.js] 缺少函数 {fn}")

# ── 8. 检查 tab_config.js 关键函数 ──
cfg_js = read('static/js/tab_config.js')
must_cfg = ['loadConfig', 'saveConfig', 'loadUserIP']
for fn in must_cfg:
    if fn not in cfg_js:
        issues.append(f"[tab_config.js] 缺少函数 {fn}")

# ── 结果 ──
print(f"\n{'='*50}")
if issues:
    print(f"发现 {len(issues)} 个问题：")
    for i in issues:
        print(f"  ✗ {i}")
else:
    print("✓ 无问题，项目状态良好")
print('='*50)
