# -*- coding: utf-8 -*-
"""第二批改动：app_new.py 路由 + config_controller + app.js"""
import os

ROOT = os.path.dirname(os.path.abspath(__file__))

# ─────────────────────────────────────────────
# 1. app_new.py — 加 /api/test-inodetree 路由
# ─────────────────────────────────────────────
app_path = os.path.join(ROOT, 'app_new.py')
app = open(app_path, encoding='utf-8').read()

OLD_ROUTE = '''@app.route('/api/test-firecrawl', methods=['POST'])
def test_firecrawl():
    """测试Firecrawl连接"""
    logger.info("测试Firecrawl连接")
    result = config_controller.test_firecrawl_connection()
    return jsonify(result)'''

NEW_ROUTE = '''@app.route('/api/test-firecrawl', methods=['POST'])
def test_firecrawl():
    """测试Firecrawl连接"""
    logger.info("测试Firecrawl连接")
    result = config_controller.test_firecrawl_connection()
    return jsonify(result)

@app.route('/api/test-inodetree', methods=['POST'])
def test_inodetree():
    """测试 InodeTree 连接"""
    logger.info("测试 InodeTree 连接")
    result = config_controller.test_inodetree_connection()
    return jsonify(result)'''

app = app.replace(OLD_ROUTE, NEW_ROUTE, 1)
open(app_path, 'w', encoding='utf-8').write(app)
print("✓ app_new.py")

# ─────────────────────────────────────────────
# 2. config_controller.py — 加 test_inodetree_connection
# ─────────────────────────────────────────────
ctrl_path = os.path.join(ROOT, 'controllers', 'config_controller.py')
ctrl = open(ctrl_path, encoding='utf-8').read()

# 加 import
if 'inodetree_service' not in ctrl:
    ctrl = ctrl.replace(
        'from services.dashscope_service import DashScopeService',
        'from services.dashscope_service import DashScopeService\nfrom services.inodetree_service import InodeTreeService',
        1
    )

# 加 test_inodetree_connection 方法（在 test_firecrawl_connection 之后，最后一个 def 前）
# 找 test_firecrawl 的结束位置 —— 在其最后 except 块的 return 之后插入
OLD_LAST = '''    def get_config_status(self) -> Dict[str, Any]:
        """获取配置状态"""'''

NEW_LAST = '''    def test_inodetree_connection(self) -> Dict[str, Any]:
        """测试 InodeTree 连接"""
        try:
            logger.info("开始测试 InodeTree 连接")
            inodetree_config = self.config_service.get_inodetree_config()
            api_key = inodetree_config.get('api_key', '')
            if not api_key:
                return {'success': False, 'message': '请先配置 InodeTree API Key'}
            from services.inodetree_service import InodeTreeService
            inodetree = InodeTreeService(api_key)
            result = inodetree.test_connection()
            status_el = 'inodetree-status'
            if result.get('success'):
                logger.info("InodeTree 连接测试成功")
                return {
                    'success': True,
                    'message': result.get('message', 'InodeTree 连接成功'),
                    'data': {'api_key_set': True, 'model': inodetree.model}
                }
            else:
                logger.error(f"InodeTree 连接测试失败: {result.get('message')}")
                return {'success': False, 'message': result.get('message', 'InodeTree 连接失败')}
        except Exception as e:
            logger.error(f"测试 InodeTree 连接时发生异常: {e}")
            return {'success': False, 'message': str(e)}

    def get_config_status(self) -> Dict[str, Any]:
        """获取配置状态"""'''

ctrl = ctrl.replace(OLD_LAST, NEW_LAST, 1)
open(ctrl_path, 'w', encoding='utf-8').write(ctrl)
print("✓ controllers/config_controller.py")

# ─────────────────────────────────────────────
# 3. static/js/app.js — 加 inodetree 到 save/load/test
# ─────────────────────────────────────────────
js_path = os.path.join(ROOT, 'static', 'js', 'app.js')
js = open(js_path, encoding='utf-8').read()

# 3a. getConfigFormData 加 inodetree 字段
OLD_GET = '''        const firecrawl_api_key = document.getElementById('firecrawl-api-key')?.value || '';
        const coze_token = document.getElementById('coze_token')?.value || '';'''
NEW_GET = '''        const firecrawl_api_key = document.getElementById('firecrawl-api-key')?.value || '';
        const inodetree_api_key = document.getElementById('inodetree-api-key')?.value || '';
        const inodetree_model = document.getElementById('inodetree-model')?.value || 'inodetree-2.0-flash';
        const coze_token = document.getElementById('coze_token')?.value || '';'''
js = js.replace(OLD_GET, NEW_GET, 1)

# 3b. return 对象加 inodetree
OLD_RET = '''            firecrawl_api_key,
            coze_token,'''
NEW_RET = '''            firecrawl_api_key,
            inodetree_api_key,
            inodetree_model,
            coze_token,'''
js = js.replace(OLD_RET, NEW_RET, 1)

# 3c. fillConfigForm 加 inodetree
OLD_FILL = '''        if (document.getElementById('firecrawl-api-key')) {
            document.getElementById('firecrawl-api-key').value = config.firecrawl_api_key || '';
        }
        if (document.getElementById('coze_token')) {'''
NEW_FILL = '''        if (document.getElementById('firecrawl-api-key')) {
            document.getElementById('firecrawl-api-key').value = config.firecrawl_api_key || '';
        }
        if (document.getElementById('inodetree-api-key')) {
            document.getElementById('inodetree-api-key').value = config.inodetree_api_key || '';
        }
        if (document.getElementById('inodetree-model')) {
            document.getElementById('inodetree-model').value = config.inodetree_model || 'inodetree-2.0-flash';
        }
        if (document.getElementById('coze_token')) {'''
js = js.replace(OLD_FILL, NEW_FILL, 1)

# 3d. 加 test-inodetree 按钮绑定（在 test-firecrawl 后）
OLD_BTN = '''        const testFirecrawlBtn = document.getElementById('test-firecrawl');
        if (testFirecrawlBtn) {
            testFirecrawlBtn.addEventListener('click', async () => {
                Utils.addLog('开始测试Firecrawl连接');
                const response = await ApiClient.post('/api/test-firecrawl', {});
                console.log('Firecrawl测试响应:', response);
                Utils.addLog(`Firecrawl测试响应: ${JSON.stringify(response)}`);
                const statusElement = document.getElementById('firecrawl-status');
                if (response.success) {
                    Utils.showToast('Firecrawl连接测试成功', 'success');
                    if (statusElement) {
                        statusElement.textContent = '连接正常';
                        statusElement.className = 'badge bg-success';
                    }
                } else {
                    Utils.showToast('Firecrawl连接测试失败: ' + response.message, 'error');
                    if (statusElement) {
                        statusElement.textContent = '连接失败';
                        statusElement.className = 'badge bg-danger';
                    }
                }
            });
        }

        // 文章生成事件'''
NEW_BTN = '''        const testFirecrawlBtn = document.getElementById('test-firecrawl');
        if (testFirecrawlBtn) {
            testFirecrawlBtn.addEventListener('click', async () => {
                Utils.addLog('开始测试Firecrawl连接');
                const response = await ApiClient.post('/api/test-firecrawl', {});
                console.log('Firecrawl测试响应:', response);
                Utils.addLog(`Firecrawl测试响应: ${JSON.stringify(response)}`);
                const statusElement = document.getElementById('firecrawl-status');
                if (response.success) {
                    Utils.showToast('Firecrawl连接测试成功', 'success');
                    if (statusElement) {
                        statusElement.textContent = '连接正常';
                        statusElement.className = 'badge bg-success';
                    }
                } else {
                    Utils.showToast('Firecrawl连接测试失败: ' + response.message, 'error');
                    if (statusElement) {
                        statusElement.textContent = '连接失败';
                        statusElement.className = 'badge bg-danger';
                    }
                }
            });
        }

        const testInodeTreeBtn = document.getElementById('test-inodetree');
        if (testInodeTreeBtn) {
            testInodeTreeBtn.addEventListener('click', async () => {
                Utils.addLog('开始测试 InodeTree 连接');
                const response = await ApiClient.post('/api/test-inodetree', {});
                console.log('InodeTree测试响应:', response);
                Utils.addLog(`InodeTree测试响应: ${JSON.stringify(response)}`);
                const statusElement = document.getElementById('inodetree-status');
                if (response.success) {
                    Utils.showToast('InodeTree 连接测试成功', 'success');
                    if (statusElement) {
                        statusElement.textContent = '连接正常';
                        statusElement.className = 'badge bg-success';
                    }
                } else {
                    Utils.showToast('InodeTree 连接测试失败: ' + response.message, 'error');
                    if (statusElement) {
                        statusElement.textContent = '连接失败';
                        statusElement.className = 'badge bg-danger';
                    }
                }
            });
        }

        // 文章生成事件'''
js = js.replace(OLD_BTN, NEW_BTN, 1)

open(js_path, 'w', encoding='utf-8').write(js)
print("✓ static/js/app.js")

print("\n全部完成！")
