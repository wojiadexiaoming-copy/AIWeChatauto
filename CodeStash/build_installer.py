import os
import sys
import shutil
import subprocess

def find_iscc():
    """查找 Windows 系统中的 Inno Setup 编译器 (ISCC.exe)"""
    iscc = shutil.which("ISCC")
    if iscc:
        return iscc

    candidates = [
        r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
        r"C:\Program Files\Inno Setup 6\ISCC.exe",
        r"C:\Program Files (x86)\Inno Setup 5\ISCC.exe",
        r"C:\Program Files\Inno Setup 5\ISCC.exe",
    ]
    for p in candidates:
        if os.path.exists(p):
            return p
    return None

def build_all():
    print("==========================================================")
    print("  引载树 InodeTree 一键自动化打包 (PyInstaller + Inno Setup)")
    print("==========================================================")

    # 1. 运行 PyInstaller 生成双端二进制可执行文件
    print("\n[Step 1/2] 正在运行 PyInstaller 打包程序核心...")
    from build_exe import build as run_pyinstaller
    run_pyinstaller()

    # 2. 检查生成的二进制
    gui_exe = os.path.join("dist", "InodeTree.exe")
    cli_exe = os.path.join("dist", "inodetree-cli.exe")

    if not os.path.exists(gui_exe) or not os.path.exists(cli_exe):
        print("❌ 错误：PyInstaller 未能成功生成完整的客户端文件，无法继续安装包打包。")
        return

    # 3. 运行 Inno Setup 生成中文安装向导 installer
    print("\n[Step 2/2] 正在调用 Inno Setup 生成中文安装程序向导...")
    iscc_path = find_iscc()

    if not iscc_path:
        print("\n⚠️ 提示：未在当前系统环境检测到 Inno Setup 编译器 (ISCC.exe)。")
        print("请在电脑上安装 Inno Setup 6（https://jrsoftware.org/isdl.php），安装后再次运行此脚本即可自动编译成 .exe 安装包。")
        print(f"生成的可独立运行文件仍已保存在当前目录下的 InodeTree.exe 及 inodetree-cli.exe ！")
        return

    iss_script = "setup_installer.iss"
    if not os.path.exists(iss_script):
        print(f"❌ 错误：未找到安装包脚本 {iss_script}")
        return

    print(f"找到 Inno Setup 编译器: {iscc_path}")
    print(f"正在编译安装脚本 {iss_script} ...")

    cmd = [iscc_path, iss_script]
    try:
        res = subprocess.run(cmd)
        if res.returncode == 0:
            output_dir = "installer_output"
            print("\n🎉【成功生成中文安装包程序！】")
            print(f"安装程序保存在: {os.path.abspath(output_dir)}")
            for f in os.listdir(output_dir):
                if f.endswith(".exe"):
                    print(f"  ➜ {os.path.join(output_dir, f)}")
        else:
            print(f"\n❌ Inno Setup 编译失败，错误代码: {res.returncode}")
    except Exception as e:
        print(f"\n❌ 编译安装包时发生异常: {e}")

if __name__ == "__main__":
    build_all()
