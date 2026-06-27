import os
import shutil
import sys

def export_clean():
    src_dir = os.path.dirname(os.path.abspath(__file__))
    dest_dir = os.path.abspath(os.path.join(src_dir, "..", "CodeStash-OpenSource"))
    
    print(f"=== CodeStash 开源清理导出工具 ===")
    print(f"源路径: {src_dir}")
    print(f"目标路径: {dest_dir}\n")
    
    # 确认是否继续
    confirm = input("确定要导出无敏感信息的开源项目到上述目标路径吗？(y/n): ").strip().lower()
    if confirm != 'y':
        print("已取消导出。")
        return

    # 如果目标文件夹存在，先清理
    if os.path.exists(dest_dir):
        print(f"清理已存在的目标文件夹: {dest_dir}...")
        try:
            shutil.rmtree(dest_dir)
        except Exception as e:
            print(f"清理失败: {e}，请手动删除目标文件夹后重试。")
            return
            
    os.makedirs(dest_dir, exist_ok=True)

    # 定义允许复制的文件夹
    allow_dirs = {
        "config",
        "controllers",
        "services",
        "static",
        "templates",
        "launcher_ui",
        "skills",
        "chrome_extension",
    }

    # 定义允许复制的单个文件
    allow_files = {
        "app_new.py",
        "main.py",
        "pyproject.toml",
        "requirements.txt",
        "uv.lock",
        "config.json.example",
        "README.md",
        "LICENSE",
        "LICENSE-CN.md",
        "OPEN_SOURCE_GUIDE.md",
        "launcher.py",
        "build_exe.py",
        ".gitignore",
        "微信草稿上传与标题截断修复方案.md"
    }

    print("\n[1] 开始复制文件和文件夹...")
    
    # 1. 复制顶层文件
    for file in os.listdir(src_dir):
        src_file = os.path.join(src_dir, file)
        
        # 复制文件
        if os.path.isfile(src_file) and file in allow_files:
            dest_file = os.path.join(dest_dir, file)
            shutil.copy2(src_file, dest_file)
            print(f"  复制文件: {file}")
            
        # 复制文件夹
        elif os.path.isdir(src_file) and file in allow_dirs:
            dest_subdir = os.path.join(dest_dir, file)
            # 复制文件夹且忽略 pycache
            shutil.copytree(src_file, dest_subdir, ignore=shutil.ignore_patterns('__pycache__', '*.pyc', '.DS_Store'))
            print(f"  复制目录: {file}/")

    # 2. 创建运行时必需的空文件夹，并写入 .gitkeep 防止 git 忽略空文件夹
    print("\n[2] 创建空文件夹结构...")
    empty_dirs = ["cache", "data", "logs"]
    for d in empty_dirs:
        target_path = os.path.join(dest_dir, d)
        os.makedirs(target_path, exist_ok=True)
        # 写入 .gitkeep
        with open(os.path.join(target_path, ".gitkeep"), "w") as f:
            f.write("")
        print(f"  创建并保持空目录: {d}/")

    print("\n[3] 导出完成！")
    print(f"无敏感信息的开源代码已成功导出至: {dest_dir}")
    print("\n后续上传 GitHub 步骤说明:")
    print(f"1. 进入命令行并切换到目标目录: cd \"{dest_dir}\"")
    print("2. 初始化一个新的 Git 仓库 (无历史敏感数据提交): git init")
    print("3. 添加所有文件到暂存区: git add .")
    print("4. 提交代码: git commit -m \"initial open source release\"")
    print("5. 关联您开源仓库的远程地址: git remote add origin <您的开源项目GitHub仓库地址>")
    print("6. 推送至主分支: git push -u origin main")
    print("\n提示: 开发者在下载并运行您开源的系统时，需要复制 config.json.example 为 config.json 并填写他们自己的微信与 AI API 密钥。")

if __name__ == "__main__":
    export_clean()
