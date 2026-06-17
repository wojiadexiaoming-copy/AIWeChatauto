
# AIWeChatauto - 微信公众号AI内容创作与自动发布平台

> 🚀 一站式AI写作、智能配图、极致排版、自动发布，助力新媒体人高效运营公众号！

---

## 📈 更新进度

### [v1.0.0] - 2026-06-17
- **🛠️ 微信草稿保存与超长标题容灾修复**：修复了在 Windows 平台下因默认字符编码隐式转换导致的 `40007` (封面图 ID 无效) 微信报错；新增 64 字节（UTF-8 编码）高精度标题物理截断与校验逻辑，彻底解决了保存草稿时偶发 `45003` (标题长度超限) 的问题。**此修复版已同步发布在 GitHub 的 `1.0.0` 分支与 `1.0.0` Tag 中**。
- **✨ WorksSpec 多人设支持**：新增创作人设 Tab 页，支持预设人设加载、自定义人设添加、编辑与一键切换。
- **⭐ GitHub 星标多路缓存代理**：优化顶部 GitHub Stars 数量获取，通过多源 API 轮询与本地高可靠缓存，彻底解决网络环境导致的加载失败。
- **💬 个人交流群二维码 Modal**：支持在界面展示作者个人微信二维码，增加用户互动与商业咨询渠道。
- **💻 控制台终端日志增强**：日志终端支持全选、复制、剪切、清空等快捷编辑功能，方便排查和记录运行问题。
- **🧹 项目一键剥离工具**：新增 `export_clean_project.py`，支持自动剥离 `config.json` 密钥、日志及缓存数据，生成纯净的开源工程。

---

## ✨ 项目亮点

- **多模型支持**：Gemini、DeepSeek、阿里云百炼等主流大模型一键切换
- **智能配图**：Pexels图库/AI生图，自动适配微信防盗链
- **极致排版**：自动内联样式，完美适配微信，支持多主题模板
- **草稿/历史/一键发布**：全流程自动化，支持草稿管理与历史追溯
- **本地/云端/容器化部署**：支持Windows、Mac、Docker一键部署
- **开放API**：可对接uniapp等前端，支持二次开发

---

## 🛠️ 适用场景

- 自媒体人/内容创业者/企业新媒体团队
- 需要高频、批量、自动化生成和发布公众号内容的场景
- 需要AI辅助写作、智能配图、自动排版的内容生产者

---

## ⚡ 快速体验 (Windows 运行与部署方案)

### 方案 A：一键双击运行 (适合非技术用户)
1. **下载程序**：在 GitHub 的 **Releases** 页面下载最新版打包好的 Windows 执行文件 `InodeTree.exe`（内置红色主题 Logo 图标）。
2. **配置密钥**：
   - 首次运行前，请将根目录下的 `config.json.example` 文件重命名为 `config.json`。
   - 使用记事本或编辑器打开 `config.json`，修改其中的配置，填入您的微信公众号 AppID、AppSecret 以及各 AI 平台的 API Key。
3. **双击运行**：双击运行 `InodeTree.exe` 即可启动图形化客户端与后台服务。

### 方案 B：本地源码部署运行 (适合开发者)
1. **环境准备**：确保 Windows 系统上已安装 Python 3.11 或更高版本。
2. **克隆源码**：
   ```bash
   git clone https://github.com/wojiadexiaoming-copy/AIWeChatauto.git
   cd AIWeChatauto
   ```
3. **创建虚拟环境**：
   ```bash
   python -m venv venv
   venv\Scripts\activate
   ```
4. **安装依赖**：
   ```bash
   pip install -r requirements.txt
   ```
5. **配置密钥**：
   - 将 `config.json.example` 复制一份并命名为 `config.json`。
   - 打开 `config.json` 并填入您的微信 AppID/Secret 和 AI API Key 等敏感信息。
6. **启动项目**：
   ```bash
   python main.py
   ```
   启动后，项目将自动在本地拉起窗口界面，或您可通过浏览器访问 `http://127.0.0.1:5000`（需将您的公网 IP 加入微信公众号白名单中）。

### 2. 配置文件说明
- 敏感配置（如 API Key）均存放在 `config.json` 中，该文件已被 `.gitignore` 忽略，不会被提交到 GitHub，确保信息安全。
- 开发者发布或部署时，只需提供 `config.json.example` 供用户参考填写。

---

## 🧩 主要配置项说明

| 配置项                | 说明                         |
|----------------------|------------------------------|
| wechat_appid         | 公众号AppID                  |
| wechat_appsecret     | 公众号AppSecret              |
| gemini_api_key       | Gemini API Key               |
| deepseek_api_key     | DeepSeek API Key             |
| dashscope_api_key    | 阿里云百炼API Key            |
| pexels_api_key       | Pexels图库API Key            |
| author               | 文章作者名                   |
| image_model          | 配图模型（gemini/pexels等）  |
| ...                  | 更多详见 config.json         |

---

## 💡 常见问题

- **图片防盗链/不显示？**  
  已内置图片代理和微信图片上传，公众号内外均可正常显示。
- **AI接口报错？**  
  检查API Key、网络，或切换备用模型。
- **草稿/发布失败？**  
  检查公众号配置、图片素材、封面图片是否有效。
- **IP白名单/接口权限？**  
  需将服务器公网IP加入公众号后台白名单。

---

## 🏆 贡献与交流

- 欢迎提交 Issue、PR，或加入交流群共同完善项目！
- ![微信图片_2025-07-13_190348_328](https://github.com/user-attachments/assets/9bb6bd37-6be1-467d-923d-c464e43640a4)

- 商业授权/定制开发请联系：**[ming7466464@gmail.com/1576129288@qq.com]**

---

## 📜 License

MIT License

> 如需商业授权或盈利性服务，请参见 [LICENSE-CN.md](LICENSE-CN.md)

---

如需更详细的功能演示、模板预览、二次开发文档等，可随时联系作者！ 
![微信图片_2025-07-13_190348_328](https://github.com/user-attachments/assets/49ec38ff-2321-4c07-953f-59d685b2f682)


打赏支持：

<img width="335" height="457" alt="微信图片_2025-07-13_185602_630" src="https://github.com/user-attachments/assets/8cbe8d7b-a5ba-4d3c-bc3b-dd449743e22b" />

![微信图片_2025-07-13_185558_797](https://github.com/user-attachments/assets/fdb26494-4b49-4c01-b5cf-d415a2e5c8db)




