import os
import subprocess
import sys
import shutil

def build():
    print("=== 开始使用 PyInstaller 编译 CodeStash 启动器 ===")
    
    # 检查当前目录
    if not os.path.exists("launcher.py"):
        print("错误: 请在项目根目录下运行此脚本。")
        sys.exit(1)
        
    # 定义 PyInstaller 打包命令
    cmd = [
        "pyinstaller",
        "--clean",
        "--noconfirm",
        "--onefile",        # 编译为独立单文件 EXE
        "--windowed",       # 无 CMD 黑窗运行
        "--name=InodeTree",
        "--icon=static/logo-red.ico", # 使用生成的 logo-red.ico 作为 EXE 图标
        "--add-data=launcher_ui;launcher_ui", # 包含动态路由的 UI HTML 页面
        "--add-data=templates;templates",     # 包含 Flask 的模板文件
        "--add-data=static;static",           # 包含 Flask 的静态资源文件
        "launcher.py"       # 启动器主入口
    ]
    
    print(f"执行打包命令: {' '.join(cmd)}")
    
    try:
        # 执行 PyInstaller
        result = subprocess.run(cmd)
        if result.returncode == 0:
            print("\n=== 编译成功！ ===")
            src_path = os.path.join("dist", "InodeTree.exe")
            dest_path = "InodeTree.exe"
            
            # 自动复制生成的 EXE 到项目根目录下，方便用户直接双击启动
            if os.path.exists(src_path):
                print(f"正在将可执行文件复制到项目根目录: {dest_path}")
                shutil.copy2(src_path, dest_path)
                print("\n【打包成功】您现在可以直接在当前目录下双击运行 InodeTree.exe 启动系统！")
            else:
                print("警告: 未在 dist 目录下找到生成的 EXE 文件。")
        else:
            print(f"\n编译失败，退出代码: {result.returncode}")
    except Exception as e:
        print(f"\n编译打包时发生异常: {e}")

if __name__ == "__main__":
    build()
