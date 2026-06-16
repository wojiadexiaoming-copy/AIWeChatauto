# CodeStash 安全开源与发布指南

本指南用于指导如何安全地将 CodeStash 项目打包、清理并上传至 GitHub 等开源平台，防止本地 API 密钥、微信 AppSecret、历史 Git 提交记录以及云函数源码泄露。

---

## 1. 自动清理导出机制

为了防止手动挑选文件出错导致敏感信息泄露，根目录下已配置自动化脚本：**[export_clean_project.py](file:///\\desktop-iup990f/uniapp-x/%E5%BE%AE%E4%BF%A1%E5%85%AC%E4%BC%97%E5%8F%B7/CodeStash%20-%E6%89%93%E5%8C%85%E5%B0%81%E8%A3%85exe%E8%84%9A%E6%9C%AC/CodeStash/export_clean_project.py)**。

### 导出时自动排除的文件/文件夹
- **`.git/`**：排除本地 Git 历史版本库（防止历史提交中硬编码的密钥被回溯发现）。
- **`uniCloud-alipay/`**：排除支付宝云函数代码（保护您的云端中转代理服务源码不开源）。
- **`config.json`**：排除包含您真实 API Key 和微信公众号密钥的本地配置文件。
- **`cache/`、`logs/`、`data/`**：排除运行日志、缓存图片/视频以及运行历史数据库。
- **各类调试脚本**：排除 `verify_ui.py`、`test_inodetree_proxy.py`、`write_inodetree*.py` 等开发期间使用的临时脚本。

### 导出时自动保留/创建的结构
- **核心业务代码**：保留 `app_new.py`、`main.py`、`pyproject.toml` 等核心运行文件。
- **公共资源文件夹**：保留 `config/`、`controllers/`、`services/`、`static/`、`templates/` 目录。
- **配置示例文件**：附带 [config.json.example](file:///\\desktop-iup990f/uniapp-x/%E5%BE%AE%E4%BF%A1%E5%85%AC%E4%BC%97%E5%8F%B7/CodeStash%20-%E6%89%93%E5%8C%85%E5%B0%81%E8%A3%85exe%E8%84%9A%E6%9C%AC/CodeStash/config.json.example) 作为配置模板。
- **运行必需文件夹**：自动在目标路径创建空的 `cache/`、`logs/`、`data/` 文件夹并置入 `.gitkeep`，防止被 Git 忽略而导致下载后运行报错。

---

## 2. 导出与发布步骤

### 第一步：一键清理导出
在当前项目根目录下，使用命令行运行以下命令：
```bash
python export_clean_project.py
```
终端会提示确认，输入 `y` 并回车。脚本会自动清理上级目录中的旧代码，并在 `../CodeStash-OpenSource` 下生成一套全新的干净代码。

### 第二步：首次发布至 GitHub
1. 打开终端并进入导出的干净代码目录：
   ```bash
   cd ../CodeStash-OpenSource
   ```
2. 初始化全新的 Git 仓库（此时提交历史是 100% 干净的）：
   ```bash
   git init
   ```
3. 添加所有文件：
   ```bash
   git add .
   ```
4. 提交本地修改：
   ```bash
   git commit -m "initial open source release"
   ```
5. 关联您的 GitHub 开源仓库地址：
   ```bash
   git remote add origin <您的开源项目 GitHub 仓库地址>
   ```
6. 推送至主分支：
   ```bash
   git push -u origin main
   ```

---

## 3. 后续代码更新迭代步骤

当您后续在本地开发环境修改了代码并想同步到开源仓库时，**请按以下步骤操作**：

1. **在开发环境开发完毕**后，确保本地测试通过。
2. 运行导出脚本：
   ```bash
   python export_clean_project.py
   ```
   *（输入 `y` 确认覆盖 `../CodeStash-OpenSource` 目录）*
3. 打开命令行，进入该目录：
   ```bash
   cd ../CodeStash-OpenSource
   ```
4. 直接添加、提交并推送到开源仓库即可（此时依然没有任何敏感历史）：
   ```bash
   git add .
   git commit -m "update: 描述您的更新内容"
   git push origin main
   ```

---

## 4. 安全注意事项 ⚠️
1. **不要在 `CodeStash-OpenSource` 目录里直接修改代码**。请始终在您的开发环境修改，然后运行 `export_clean_project.py` 导出。
2. 开源版使用者下载代码后，需要将 `config.json.example` 重命名为 `config.json` 并填写自己的密钥即可运行。
