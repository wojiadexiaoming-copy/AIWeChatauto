import os
import sys
import json
import subprocess
import threading
import webbrowser
import webview
import signal
from datetime import datetime

def get_resource_path(relative_path):
    """ 获取资源路径：优先使用当前工作目录（支持热更新/版本切换），不存在才使用打包临时目录 """
    local_path = os.path.abspath(relative_path)
    if os.path.exists(local_path):
        return local_path
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return local_path

class LauncherApi:
    def __init__(self):
        self.process = None
        self.log_history = ""
        self.config_file = "config.json"
        from services.config_service import ConfigService
        self.config_service = ConfigService(self.config_file)
        self.port = 5000
        self.lan_access = False
        self.is_maximized = False
        self.normal_x = 100
        self.normal_y = 100
        self.normal_width = 1280
        self.normal_height = 800
        self._load_port_settings()

    def _load_port_settings(self):
        """从 config.json 读端口和监听配置，以便后台使用"""
        try:
            cfg = self.config_service.load_config()
            self.port = int(cfg.get("server_port", 5000))
            self.lan_access = bool(cfg.get("lan_access", False))
        except Exception as e:
            print(f"读端口配置异常: {e}")

    # ── 窗口管理接口 ──────────────────────────────────────────────────
    def minimize_window(self):
        webview.windows[0].minimize()

    def _get_windows_work_area(self):
        import ctypes
        from ctypes import wintypes

        class RECT(ctypes.Structure):
            _fields_ = [
                ('left', ctypes.c_long),
                ('top', ctypes.c_long),
                ('right', ctypes.c_long),
                ('bottom', ctypes.c_long)
            ]

        class MONITORINFO(ctypes.Structure):
            _fields_ = [
                ('cbSize', wintypes.DWORD),
                ('rcMonitor', RECT),
                ('rcWork', RECT),
                ('dwFlags', wintypes.DWORD)
            ]

        try:
            hwnd = ctypes.windll.user32.FindWindowW(None, "引载树 v1.0.0 - 数据资产启动器")
            if hwnd:
                monitor = ctypes.windll.user32.MonitorFromWindow(hwnd, 2)  # MONITOR_DEFAULTTONEAREST
                info = MONITORINFO()
                info.cbSize = ctypes.sizeof(MONITORINFO)
                if ctypes.windll.user32.GetMonitorInfoW(monitor, ctypes.byref(info)):
                    w = info.rcWork
                    return (w.left, w.top, w.right - w.left, w.bottom - w.top)
        except Exception as e:
            print(f"获取 Monitor 失败: {e}")

        try:
            rect = RECT()
            SPI_GETWORKAREA = 48
            if ctypes.windll.user32.SystemParametersInfoW(SPI_GETWORKAREA, 0, ctypes.byref(rect), 0):
                return (rect.left, rect.top, rect.right - rect.left, rect.bottom - rect.top)
        except Exception as e:
            print(f"获取 SystemParametersInfo 失败: {e}")
            
        return (0, 0, 1024, 680)

    def toggle_maximize_window(self):
        window = webview.windows[0]
        if self.is_maximized:
            if sys.platform == "win32":
                try:
                    # Restore to normal size and position
                    window.move(self.normal_x, self.normal_y)
                    window.resize(self.normal_width, self.normal_height)
                except Exception as e:
                    print(f"手动恢复窗口失败: {e}")
                    window.restore()
            else:
                window.restore()
            self.is_maximized = False
        else:
            if sys.platform == "win32":
                try:
                    # Save current size and position
                    self.normal_x = window.x
                    self.normal_y = window.y
                    self.normal_width = window.width
                    self.normal_height = window.height
                    
                    # Resize and move to work area (above taskbar)
                    left, top, width, height = self._get_windows_work_area()
                    window.move(left, top)
                    window.resize(width, height)
                except Exception as e:
                    print(f"手动最大化窗口失败: {e}")
                    window.maximize()
            else:
                window.maximize()
            self.is_maximized = True
        return self.is_maximized


    def close_window(self):
        # 退出前确保 Flask 服务被销毁
        self.stop_server()
        webview.windows[0].destroy()
        sys.exit(0)

    def get_page_html(self, page_name):
        """读取指定页面的 HTML 内容并返回给 JS"""
        try:
            page_name = os.path.basename(page_name)
            if not page_name.endswith(".html"):
                return ""
            
            ui_path = get_resource_path(os.path.join("launcher_ui", page_name))
            if os.path.exists(ui_path):
                with open(ui_path, "r", encoding="utf-8") as f:
                    return f.read()
            else:
                print(f"错误: 找不到页面文件 {ui_path}")
                return ""
        except Exception as e:
            print(f"读取页面 {page_name} 发生异常: {e}")
            return ""

    def get_public_ip(self):
        """获取公网IP地址"""
        import requests
        # 使用仅支持 IPv4 的公网 IP 查询服务，防止返回 IPv6 地址
        for url in ["https://api4.ipify.org?format=json", "https://ipv4.icanhazip.com", "https://ipv4.ident.me"]:
            try:
                resp = requests.get(url, timeout=3)
                if resp.status_code == 200:
                    if "json" in url or "format=json" in url:
                        d = resp.json()
                        ip = d.get("origin") or d.get("ip")
                        if ip:
                            return ip.split(',')[0].strip()
                    else:
                        return resp.text.strip()
            except Exception:
                pass
        return "获取失败"

    def open_wechat_window(self):
        """打开微信公众号管理平台的内置浏览器窗口"""
        for w in webview.windows:
            if w.title == "微信公众号平台":
                w.focus()
                return
        
        # 打开独立窗口加载微信后台，支持后续通过自动化脚本注入和操作
        webview.create_window(
            title="微信公众号平台",
            url="https://mp.weixin.qq.com/",
            width=1280,
            height=850,
            resizable=True
        )

    # ── 启动器配置逻辑 ────────────────────────────────────────────────
    def get_config(self):
        """获取 config.json 逻辑选项"""
        try:
            return self.config_service.load_config()
        except Exception as e:
            print(f"读取配置失败: {e}")
            return {}

    def save_config(self, data):
        """写入配置到 config.json 及人设文件夹"""
        try:
            success = self.config_service.save_config(data)
            if success:
                # 同步本地状态
                self.port = int(data.get("server_port", self.port))
                self.lan_access = bool(data.get("lan_access", self.lan_access))
            print("保存配置结果:", success)
            return success
        except Exception as e:
            print(f"保存配置异常: {e}")
            return False

    # ── 环境检测与依赖安装 ──────────────────────────────────────────────
    def check_environment(self):
        """检查运行环境和 requirements.txt 中的依赖项"""
        import importlib.metadata
        
        # 1. 获取 python 和 pip 版本
        python_ver = sys.version.split()[0]
        python_path = sys.executable
        
        # 2. 读取 requirements.txt 中的依赖
        requirements_path = "requirements.txt"
        dependencies = []
        all_ok = True
        
        # 检查 packaging 模块是否可用
        has_packaging = False
        try:
            from packaging.specifiers import SpecifierSet
            from packaging.version import Version
            has_packaging = True
        except ImportError:
            pass
            
        if os.path.exists(requirements_path):
            try:
                with open(requirements_path, "r", encoding="utf-8") as f:
                    lines = f.readlines()
            except Exception as e:
                print(f"读取 requirements.txt 失败: {e}")
                lines = []
                
            for line in lines:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                
                import re
                match = re.match(r'^([a-zA-Z0-9_\-]+)\s*(.*)$', line)
                if match:
                    pkg_name = match.group(1)
                    version_spec = match.group(2).strip()
                    
                    installed_ver = None
                    status = "missing"
                    
                    # 尝试用原始包名和全小写等多种格式查询
                    names_to_try = [pkg_name, pkg_name.lower(), pkg_name.replace('_', '-'), pkg_name.replace('-', '_')]
                    for name in names_to_try:
                        try:
                            installed_ver = importlib.metadata.version(name)
                            status = "ok"
                            break
                        except importlib.metadata.PackageNotFoundError:
                            continue
                            
                    if status == "ok" and installed_ver:
                        if version_spec:
                            if has_packaging:
                                try:
                                    spec = SpecifierSet(version_spec)
                                    if Version(installed_ver) not in spec:
                                        status = "mismatch"
                                        all_ok = False
                                except Exception:
                                    pass
                            else:
                                # 简易比较逻辑
                                try:
                                    req_ver_match = re.search(r'([0-9\.]+)', version_spec)
                                    if req_ver_match:
                                        req_ver = req_ver_match.group(1)
                                        req_parts = [int(x) for x in req_ver.split('.') if x.isdigit()]
                                        inst_parts = [int(x) for x in installed_ver.split('.') if x.isdigit()]
                                        max_len = max(len(req_parts), len(inst_parts))
                                        req_parts += [0] * (max_len - len(req_parts))
                                        inst_parts += [0] * (max_len - len(inst_parts))
                                        
                                        if inst_parts < req_parts:
                                            status = "mismatch"
                                            all_ok = False
                                except Exception:
                                    pass
                    else:
                        status = "missing"
                        all_ok = False
                    
                    dependencies.append({
                        "name": pkg_name,
                        "required": version_spec if version_spec else "无限制",
                        "installed": installed_ver if installed_ver else "未安装",
                        "status": status
                    })
        
        return {
            "python_version": python_ver,
            "python_path": python_path,
            "dependencies": dependencies,
            "all_ok": all_ok
        }

    def install_dependencies(self):
        """执行 pip install -r requirements.txt 并回传安装日志"""
        if hasattr(self, 'install_process') and self.install_process and self.install_process.poll() is None:
            return False
            
        self.install_log = "=== 开始安装 Python 依赖项 ===\n"
        
        # 使用当前 python 的 pip，并指定国内清华镜像源加速
        cmd = [sys.executable, "-m", "pip", "install", "-r", "requirements.txt", "-i", "https://pypi.tuna.tsinghua.edu.cn/simple"]
        
        try:
            self.install_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
            )
            
            # 异步线程读取安装日志并传回前端
            threading.Thread(target=self._read_install_logs, daemon=True).start()
            return True
        except Exception as e:
            self.install_log += f"执行 pip 安装命令失败: {e}\n"
            print(f"执行 pip 异常: {e}")
            return False

    def _read_install_logs(self):
        while hasattr(self, 'install_process') and self.install_process and self.install_process.poll() is None:
            line = self.install_process.stdout.readline()
            if not line:
                break
            line_str = line.rstrip("\r\n")
            self.install_log += line_str + "\n"
            
            # 动态回传给 webview 进度显示
            try:
                js_code = f"if (window.addInstallLogLine) window.addInstallLogLine({json.dumps(line_str)});"
                webview.windows[0].evaluate_js(js_code)
            except Exception:
                pass
                
        # 执行完毕回调
        try:
            status = self.install_process.poll()
            success = (status == 0)
            js_code = f"if (window.onInstallComplete) window.onInstallComplete({json.dumps(success)});"
            webview.windows[0].evaluate_js(js_code)
        except Exception:
            pass

    def get_install_logs(self):
        """获取已积累的安装日志"""
        return getattr(self, 'install_log', "")
        
    def is_installing(self):
        """是否正在安装中"""
        if hasattr(self, 'install_process') and self.install_process is not None:
            return self.install_process.poll() is None
        return False

    # ── Git 版本控制与更新管理 ──────────────────────────────────────────
    def _run_git_cmd(self, args):
        """运行 git 命令并获取输出，禁用凭据管理器弹窗"""
        try:
            # 禁用交互式提示，避免在拉取公开仓库时弹出登录框
            env = os.environ.copy()
            env["GIT_TERMINAL_PROMPT"] = "0"
            env["GCM_INTERACTIVE"] = "never"
            
            # 使用 -c credential.helper= 临时绕过 Git 凭据助手
            cmd = ["git", "-c", "credential.helper="] + args
            
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                env=env,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
            )
            if result.returncode == 0:
                return result.stdout.strip(), True
            return result.stderr.strip(), False
        except Exception as e:
            return str(e), False

    def get_git_version_info(self):
        """获取本地 Git 仓库版本信息"""
        if not os.path.exists(".git"):
            return {
                "is_git": False,
                "remote_url": "当前运行目录不属于 Git 仓库",
                "branch": "无",
                "current_version": "无法获取（请在 Git 目录下运行）"
            }
            
        remote_url, ok = self._run_git_cmd(["remote", "get-url", "origin"])
        if not ok:
            remote_url = "未关联远程仓库"
            
        branch, ok = self._run_git_cmd(["branch", "--show-current"])
        if not ok:
            branch = "未知"
            
        log_info, ok = self._run_git_cmd(["log", "-1", "--format=%h (%ad)", "--date=format:%Y-%m-%d %H:%M:%S"])
        if not ok:
            log_info = "无提交历史"
            
        return {
            "is_git": True,
            "remote_url": remote_url,
            "branch": branch,
            "current_version": log_info
        }

    def get_git_version_list(self):
        """获取所有远端版本分支并进行 SemVer 排序"""
        if not os.path.exists(".git"):
            return [
                {"id": "v1.10.1", "commit": "82a973c", "desc": "示例稳定版 (未关联 Git 仓库)", "date": "2024-07-27 20:49:39", "current": True},
                {"id": "v1.10.0", "commit": "c19d044", "desc": "示例历史版本 (未关联 Git 仓库)", "date": "2024-07-27 11:53:05", "current": False}
            ]
            
        # 1. 尝试同步远端全部分支
        self._run_git_cmd(["fetch", "--all", "--prune"])
        
        # 2. 获取远端分支列表
        branches_out, ok = self._run_git_cmd(["branch", "-r"])
        if not ok or not branches_out:
            return []
            
        import re
        versions = []
        
        # 获取当前所在的分支
        current_branch, _ = self._run_git_cmd(["branch", "--show-current"])
        current_branch = current_branch.strip() if current_branch else ""
        
        lines = branches_out.split("\n")
        seen_versions = set()
        
        for line in lines:
            line = line.strip()
            if not line or "->" in line:
                continue
            
            # 提取分支名称，去掉 origin/ 前缀
            if line.startswith("origin/"):
                branch_name = line[len("origin/"):]
            else:
                continue
                
            if branch_name in seen_versions:
                continue
                
            # 过滤出版本号类型的分支（形如 1.0.1, v0.0.2 等）或主分支 main
            is_version = re.match(r'^(?:v)?\d+(?:\.\d+)+$', branch_name, re.IGNORECASE)
            is_main = branch_name == "main"
            
            if not (is_version or is_main):
                continue
                
            seen_versions.add(branch_name)
            
            # 获取该分支最新提交信息
            log_info, log_ok = self._run_git_cmd([
                "log", "-1", f"origin/{branch_name}",
                "--pretty=format:%h|%ad|%s",
                "--date=format:%Y-%m-%d %H:%M:%S"
            ])
            
            commit_hash = "未知"
            commit_date = "未知"
            commit_msg = branch_name
            
            if log_ok and log_info:
                parts = log_info.split("|")
                if len(parts) >= 3:
                    commit_hash = parts[0].strip()
                    commit_date = parts[1].strip()
                    commit_msg = parts[2].strip()
            
            is_current = (current_branch == branch_name)
            
            versions.append({
                "id": branch_name,
                "commit": commit_hash,
                "desc": commit_msg if commit_msg else branch_name,
                "date": commit_date,
                "current": is_current
            })
            
        # 根据 SemVer 对分支名称排序
        def parse_version(ver_str):
            ver = ver_str.lower().strip()
            if ver == "main":
                # 将 main 排在最后作为底版
                return (-1, -1, -1)
            if ver.startswith('v'):
                ver = ver[1:]
            match = re.match(r'^(\d+)(?:\.(\d+))?(?:\.(\d+))?.*$', ver)
            if match:
                major = int(match.group(1))
                minor = int(match.group(2)) if match.group(2) else 0
                patch = int(match.group(3)) if match.group(3) else 0
                return (major, minor, patch)
            return (-2, -2, -2)
            
        versions.sort(key=lambda x: parse_version(x["id"]), reverse=True)
        return versions

    def switch_git_version(self, version_id):
        """切换到指定的 Git 分支版本"""
        # 1. 检查本地是否有同名分支
        local_branches, ok = self._run_git_cmd(["branch"])
        has_local = False
        if ok and local_branches:
            for b in local_branches.split("\n"):
                if b.strip().replace("*", "").strip() == version_id:
                    has_local = True
                    break
        
        # 2. 强制切换以丢弃潜在的代码文件变更冲突
        if has_local:
            out, ok = self._run_git_cmd(["checkout", "-f", version_id])
        else:
            out, ok = self._run_git_cmd(["checkout", "-f", "-b", version_id, f"origin/{version_id}"])
            
        if ok:
            # 保证拉取远端该分支的最新 commit
            self._run_git_cmd(["pull", "origin", version_id])
            return {"success": True, "msg": f"已成功切换到版本分支 {version_id}。"}
        return {"success": False, "msg": f"切换版本分支失败: {out}"}

    def update_git_to_latest(self):
        """一键更新到版本号最高的最新远程分支"""
        versions = self.get_git_version_list()
        if not versions:
            return {"success": False, "msg": "未找到任何版本分支。"}
            
        # 最新版本排序在最前
        latest_version = versions[0]["id"]
        res = self.switch_git_version(latest_version)
        if res["success"]:
            return {"success": True, "msg": f"一键更新成功！当前已更新到最新分支 [{latest_version}]。"}
        return {"success": False, "msg": f"一键更新失败: {res['msg']}"}

    def open_folder(self, folder_name):
        """在系统资源管理器中打开指定文件夹"""
        try:
            # 保证路径安全，将相对路径转为绝对路径
            base_dir = os.path.abspath(".")
            # 支持传入空字符或点表示根目录
            if folder_name == "." or not folder_name:
                folder_path = base_dir
            else:
                folder_path = os.path.abspath(os.path.join(base_dir, folder_name))
            
            # 防止路径越界（安全防范，确保打开的文件夹在项目根目录下）
            if not folder_path.startswith(base_dir):
                print(f"安全警报: 试图打开项目外的目录 {folder_path}")
                return False
                
            # 如果不存在，则自动创建
            os.makedirs(folder_path, exist_ok=True)
            
            if sys.platform == "win32":
                os.startfile(folder_path)
            else:
                subprocess.Popen(["xdg-open" if sys.platform == "linux" else "open", folder_path])
            return True
        except Exception as e:
            print(f"打开文件夹 {folder_name} 失败: {e}")
            return False

    # ── 进程启动与控制 ────────────────────────────────────────────────
    def is_server_running(self):
        """检查 Flask 是否在后台运行中"""
        if self.process is not None:
            # poll() 为 None 代表子进程依然存活运行中
            return self.process.poll() is None
        return False

    def start_server(self):
        """拉起 Flask 子进程"""
        if self.is_server_running():
            return True

        # 重置日志缓存
        self.log_history = "=== 微信公众号自动发布系统 正在启动... ===\n"
        
        # 刷新端口设置
        self._load_port_settings()
        
        host = "0.0.0.0" if self.lan_access else "127.0.0.1"
        
        # 在子进程中执行 python main.py，用命令行传参覆盖或直接通过环境变量重载
        env = os.environ.copy()
        env["FLASK_RUN_PORT"] = str(self.port)
        env["FLASK_RUN_HOST"] = host
        
        try:
            # 启动子进程，重定向标准输出与错误
            self.process = subprocess.Popen(
                [sys.executable, "main.py"],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                env=env,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
            )
            
            # 开启异步读取日志的线程
            threading.Thread(target=self._read_logs, daemon=True).start()
            return True
        except Exception as e:
            err_msg = f"启动子进程失败: {e}\n"
            self.log_history += err_msg
            print(err_msg)
            return False

    def stop_server(self):
        """停止/终止 Flask 子进程"""
        if not self.is_server_running():
            return True

        try:
            self.log_history += "\n=== 正在终止 Flask 后台进程... ===\n"
            if sys.platform == "win32":
                # Windows 下直接 kill
                self.process.terminate()
            else:
                self.process.send_signal(signal.SIGTERM)
                
            self.process.wait(timeout=5)
            self.log_history += "=== Flask 后台进程已安全终止 ===\n"
            self.process = None
            return True
        except Exception as e:
            self.log_history += f"终止进程异常: {e}\n"
            self.process = None
            return False

    def get_active_logs(self):
        """供前端获取已积累的历史日志"""
        return self.log_history

    def clear_logs(self):
        """清空本地积累的历史日志"""
        self.log_history = ""
        return True

    def open_browser(self):
        """打开默认浏览器访问系统网页"""
        url = f"http://127.0.0.1:{self.port}"
        webbrowser.open(url)

    # ── 内部日志流读取 ────────────────────────────────────────────────
    def _read_logs(self):
        while self.process and self.process.poll() is None:
            line = self.process.stdout.readline()
            if not line:
                break
            
            # 过滤换行
            line_str = line.rstrip("\r\n")
            self.log_history += line_str + "\n"
            
            # 限制历史日志最大长度，防止内存泄漏
            if len(self.log_history) > 100000:
                self.log_history = self.log_history[-50000:]

            # 动态回传给 WebView 页面（如果前端处于 Console 页）
            try:
                js_code = f"if (window.addLogLine) window.addLogLine({json.dumps(line_str)});"
                webview.windows[0].evaluate_js(js_code)
            except Exception:
                pass

def main():
    import os
    os.environ['WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS'] = '--disable-web-security'
    api = LauncherApi()
    ui_path = get_resource_path(os.path.join("launcher_ui", "page_1.html"))
    
    if not os.path.exists(ui_path):
        print(f"错误: 找不到启动器 UI 文件 {ui_path}")
        sys.exit(1)

    url = "file:///" + ui_path.replace("\\", "/")
    
    # 创建窗口，隐藏边框，宽度对齐引载树设计尺寸
    window = webview.create_window(
        title="引载树 v1.0.0 - 数据资产启动器",
        url=url,
        js_api=api,
        width=1280,
        height=800,
        resizable=True,
        min_size=(800, 600),
        frameless=True
    )
    
    # 启动应用，并伪装为标准桌面版 Chrome 浏览器 User-Agent，规避微信/Cloudflare等安全拦截
    webview.start(
        debug=False,
        user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
    )

if __name__ == "__main__":
    # 检查是否为打包后的 Flask 服务子进程启动指令
    if len(sys.argv) > 1 and sys.argv[1] == "main.py":
        # 强制将当前运行目录置于搜索路径首位，以在切换版本后优先导入外部最新 Python 代码文件
        sys.path.insert(0, os.path.abspath("."))
        
        try:
            from app_new import app
            from main import get_server_config
            host, port = get_server_config()
            print(f"正在启动 Flask 服务 (EXE 子进程模式): http://{host}:{port}")
            app.run(host=host, port=port, debug=False)
        except Exception as e:
            print(f"启动 Flask 服务异常: {e}")
            import traceback
            traceback.print_exc()
        sys.exit(0)
    else:
        main()
