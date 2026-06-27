from app_new import app
import os
import json

def get_server_config():
    host = '127.0.0.1'
    port = 5000
    try:
        if os.path.exists('config.json'):
            with open('config.json', 'r', encoding='utf-8') as f:
                cfg = json.load(f)
                port = int(cfg.get('server_port', 5000))
                host = '0.0.0.0' if cfg.get('lan_access', False) else '127.0.0.1'
    except Exception:
        pass
    
    # Allow environment variable overrides
    host = os.environ.get('FLASK_RUN_HOST', host)
    port = int(os.environ.get('FLASK_RUN_PORT', port))
    return host, port

if __name__ == '__main__':
    host, port = get_server_config()
    print(f"正在启动 Flask 服务: http://{host}:{port}")
    app.run(host=host, port=port, debug=False)
