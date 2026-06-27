// 公众号智能美化助手 - 侧边栏逻辑

class WeChatAssistantSidePanel {
  constructor() {
    this.currentContent = '';
    this.currentStructuredContent = []; // 存储结构化内容（文本+图片）
    this.currentTab = 'editor';
    this.selectedTemplate = null; // 当前选中的模板
    this.lastContainerWidth = null; // 记录上一次容器宽度，用于防抖
    this.hidePreviewTimer = null; // 预览框延迟隐藏定时器
    this.currentPreviewTemplateId = null; // 当前预览的模板ID，用于防抖
    this.previewCache = new Map(); // 预览内容缓存
    this.config = {
      isEnabled: true
    };
    
    // 添加内容检测稳定性优化
    this.contentCheckDebounceTimer = null;
    this.lastContentHash = ''; // 内容哈希值缓存
    
    // 添加内容状态管理
    this.contentState = {
      hasContent: false,
      lastUpdateTime: 0,
      isStable: false
    };
    
    // 搜索和筛选相关
    this.allTemplates = []; // 存储所有模板数据
    this.filteredTemplates = []; // 存储筛选后的模板数据
    this.currentFilter = 'all'; // 当前筛选类型：all, free, vip
    this.searchQuery = ''; // 当前搜索关键词
    
    // [新增] 流式处理相关属性
    this.isStreaming = false;
    this.streamingContent = '';
    this.debouncedUpdateEditor = this.debounce(this.updateEditorInRealtime, 200); // 200ms防抖

    // 角色提示词（与后端保持一致）
    this.rolePrompt = `你是一位专业的微信公众号内容创作者和排版专家，拥有丰富的数字媒体经验，精通内容策划、用户心理分析和新媒体营销。你严谨且专业地将用户给到的内容在不更改任何文本的前提下，完美套用模板，确保内容符合微信官方要求。

你的核心能力和要求包括：
1. **内容填入专家**：专注于将用户内容准确填入到模板的相应位置，不修改任何样式代码
2. **模板结构严格保持**：严格保持模板的HTML结构和内联样式不变，绝不允许修改任何样式代码
3. **智能内容分配**：根据用户内容的数量，智能重复使用模板中的结构元素（如标题、正文段落等），创建多个相应的段落来容纳所有用户内容
4. **用户顺序绝对保持**：**严格按照用户的排版顺序进行智能填入，切勿打乱用户文章的原有顺序**，这是最重要的要求
5. **内容完整覆盖**：确保所有用户提供的内容都能被合理地填入到相应的模板结构中，不遗漏任何信息
6. **输出格式规范**：直接返回完整的内联式HTML代码，切勿输出与内联式代码无关的文本或字符
7. **灵活模板调整**：可以在必要的时候通过灵活调整模板顺序从而适配文章的排版顺序，确保最佳的内容呈现效果
8. **对齐控制规范**：**严禁使用空格字符来控制文本对齐**，必须使用正确的CSS对齐属性（如text-align: center、text-align: left、text-align: right）来实现居中或左右对齐效果，确保在不同设备和屏幕宽度下都能正确显示，避免因空格数量导致的对齐错乱问题
9. **模板板块智能增删**：**根据用户文章内容的实际需要，智能选择使用模板中的合适板块**，不必强制使用模板的所有样式板块。如果用户文章内容简短，可以删除多余的装饰性板块；如果用户文章内容丰富，可以重复使用相应的内容板块；如果用户文章缺少某些信息（如作者、日期等），可以省略相应的模板板块。确保最终生成的内容与用户文章的内容量和结构相匹配，避免出现空洞的装饰板块或信息不符的情况
10. **视频元素规范处理**：**对于用户内容中的视频元素，必须严格按照微信公众号视频规范进行模板替换**。视频元素包含完整的iframe结构和微信视频ID信息，在替换到模板时需要保持视频的完整功能性。确保视频元素的data-mpvid、src、width、height等关键属性完整保留，视频封面图片正确显示，视频播放控件正常工作。视频元素应当作为独立的内容块进行处理，不与其他元素混合，保证在微信公众号编辑器中能够正常播放和编辑`;

    this.init();
  }
  
  // [新增] 防抖工具函数
  debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
      const later = () => {
        clearTimeout(timeout);
        func.apply(this, args);
      };
      clearTimeout(timeout);
      timeout = setTimeout(later, wait);
    };
  }

  async init() {
    // 加载配置
    await this.loadConfig();

    // 绑定事件
    this.bindEvents();

    // 初始化界面
    this.initUI();

    // 检查编辑器状态
    this.checkEditorStatus();

    // 监听来自content script的消息
    chrome.runtime.onMessage.addListener(this.onMessage.bind(this));

    // 🆕 添加窗口大小变化监听器，解决侧边栏拉宽时模板不完整渲染的问题
    this.addResizeListener();
    
    // 添加实时链接监测功能
    this.startLinkMonitoring();
  }

  // 绑定搜索和筛选事件
  bindSearchAndFilterEvents() {
    // 搜索输入框
    const searchInput = document.getElementById('templateSearchInput');
    if (searchInput) {
      searchInput.addEventListener('input', (e) => {
        this.handleSearchInput(e.target.value);
      });
    }

    // 清除搜索按钮
    const searchClearBtn = document.getElementById('searchClearBtn');
    if (searchClearBtn) {
      searchClearBtn.addEventListener('click', () => {
        this.clearSearch();
      });
    }

    // 筛选标签
    const filterTabs = document.querySelectorAll('.filter-tab');
    filterTabs.forEach(tab => {
      tab.addEventListener('click', (e) => {
        this.handleFilterChange(e.target.dataset.filter);
      });
    });
  }

  // 绑定事件
  bindEvents() {
    // 标签切换
    document.querySelectorAll('.tab-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        this.switchTab(e.target.dataset.tab);
      });
    });

    // 模板选择事件将在模板加载后绑定

    // 生成按钮
    document.getElementById('generateBtn').addEventListener('click', () => {
      this.generateContent();
    });

    // 应用结果按钮
    document.getElementById('applyBtn').addEventListener('click', () => {
      this.applyOptimization();
    });

    // 复制结果按钮
    document.getElementById('copyBtn').addEventListener('click', () => {
      this.copyOptimization();
    });

    // 丢弃结果按钮
    document.getElementById('discardBtn').addEventListener('click', () => {
      this.discardOptimization();
    });

    // 保存配置按钮（简化版）
    document.getElementById('saveConfigBtn')?.addEventListener('click', () => {
      this.saveConfig();
    });


    // ============ 模板管理相关事件 ============

    // 刷新模板按钮
    const refreshTemplatesBtn = document.getElementById('refreshTemplatesBtn');
    if (refreshTemplatesBtn) {
      refreshTemplatesBtn.addEventListener('click', () => {
        this.refreshTemplates();
      });
    }



    // ============ API配置相关事件 ============

    // API Key输入
    const apiKeyInput = document.getElementById('apiKeyInput');
    if (apiKeyInput) {
      apiKeyInput.addEventListener('input', () => {
        this.validateApiKeyInput();
      });
    }

    // 切换API Key显示/隐藏
    const toggleApiKeyBtn = document.getElementById('toggleApiKeyBtn');
    if (toggleApiKeyBtn) {
      toggleApiKeyBtn.addEventListener('click', () => {
        this.toggleApiKeyVisibility();
      });
    }

    // 保存所有配置按钮（统一保存API和VIP配置）
    const saveAllConfigBtn = document.getElementById('saveAllConfigBtn');
    if (saveAllConfigBtn) {
      saveAllConfigBtn.addEventListener('click', () => {
        this.saveAllConfig();
      });
    }

    // 保存API配置（保留兼容性）
    const saveApiConfigBtn = document.getElementById('saveApiConfigBtn');
    if (saveApiConfigBtn) {
      saveApiConfigBtn.addEventListener('click', () => {
        this.saveApiConfig();
      });
    }

    // VIP密钥输入验证
    const vipKeyInput = document.getElementById('vipKeyInput');
    if (vipKeyInput) {
      vipKeyInput.addEventListener('input', () => {
        this.validateVipKeyInput();
      });
    }

    // 切换VIP密钥显示/隐藏
    const toggleVipKeyBtn = document.getElementById('toggleVipKeyBtn');
    if (toggleVipKeyBtn) {
      toggleVipKeyBtn.addEventListener('click', () => {
        this.toggleVipKeyVisibility();
      });
    }

    // 旧的VIP密钥保存按钮逻辑移除，统一用“保存配置”

    // 搜索和筛选事件绑定
    this.bindSearchAndFilterEvents();

    // 动态添加的事件监听器（用于动态生成的元素）
    this.bindDynamicEvents();

  }

  // 绑定动态事件（用于动态生成的元素）
  bindDynamicEvents() {
    // 使用事件委托来处理动态生成的元素
    document.addEventListener('click', (e) => {
      // 重试生成按钮
      if (e.target && e.target.id === 'retryGenerationBtn') {
        this.retryGeneration();
      }
      // 丢弃优化按钮
      else if (e.target && e.target.id === 'discardOptimizationBtn') {
        this.discardOptimization();
      }
      // 清除搜索和筛选按钮
      else if (e.target && e.target.id === 'clearSearchAndFilterBtn') {
        this.clearSearchAndFilter();
      }
      // 清除搜索按钮
      else if (e.target && e.target.id === 'clearSearchBtn') {
        this.clearSearch();
      }
      // 清除筛选按钮
      else if (e.target && e.target.id === 'clearFilterBtn') {
        this.clearFilter();
      }
    });
  }

  /**
   * 获取当前活动标签页（Firefox兼容）
   */
  async getCurrentTab() {
    try {
      const runtime = window.browser?.tabs || chrome.tabs;

      let tabs = await runtime.query({ active: true, currentWindow: true });

      if (!tabs || tabs.length === 0) {
        tabs = await runtime.query({});

        if (!tabs || tabs.length === 0) {
          return null;
        }
      }

      const tab = tabs[0];
      return tab;
    } catch (error) {
      return null;
    }
  }

  // 初始化界面
  initUI() {
    // 加载API配置
    this.loadApiConfig();

    // 更新状态（硬编码为启用）
    this.updateStatus(true);

    // 延迟加载模板列表，确保后台服务完全就绪
    setTimeout(() => {
      this.loadTemplatesDirect();
    }, 3000);

    // 启动VIP密钥监控，保持剩余天数与状态动态更新
    this.startVipKeyMonitoring();

  }


  // 检查编辑器状态
  async checkEditorStatus() {
    try {
      const tab = await this.getCurrentTab();

      if (!tab) {
        this.updateStatus(false);
        return;
      }

      const isWeChat = tab.url && tab.url.includes('mp.weixin.qq.com');

      const response = await chrome.tabs.sendMessage(tab.id, {
        type: 'GET_EDITOR_STATUS'
      }).catch(() => null);

      if (response && response.success && response.data.exists) {
        this.updateStatus(true);
        // 自动获取内容状态
        this.checkContentStatus();
      } else {
        this.updateStatus(false);
        // 在非微信公众号页面下，无需提示找不到编辑器，直接检查内容（如选中文本）
        if (isWeChat) {
          this.showNotification('未找到公众号编辑器', 'warning');
        } else {
          this.checkContentStatus();
        }
      }
    } catch (error) {
      this.updateStatus(false);
    }
  }

  // 添加内容哈希函数，提高内容比较的准确性
  getContentHash(content) {
    if (!content) return '';

    // 简单的哈希函数，用于比较内容是否真正发生变化
    let hash = 0;
    for (let i = 0; i < content.length; i++) {
      const char = content.charCodeAt(i);
      hash = ((hash << 5) - hash) + char;
      hash = hash & hash; // 转换为32位整数
    }
    return hash.toString();
  }

  // 优化内容检测稳定性
  async checkContentStatus() {
    try {
      const tab = await this.getCurrentTab();

      if (!tab) {
        // 只有在确实没有内容时才更新状态
        if (!this.currentContent || !this.currentContent.trim()) {
          this.updateContentStatus('', null, []);
        }
        return;
      }

      // 获取结构化内容（包含文本和图片）
      const response = await chrome.tabs.sendMessage(tab.id, {
        type: 'GET_STRUCTURED_CONTENT'
      });

      if (response && response.success) {
        const structuredData = response.data;
        const contentHash = this.getContentHash(structuredData.html);

        // 只有当内容真正发生变化时才更新状态
        if (contentHash !== this.lastContentHash) {
          this.currentContent = structuredData.html;
          this.currentStructuredContent = structuredData.structured; // 保存结构化内容
          this.lastContentHash = contentHash;

          // 并行获取字数
          let wordCount = null;
          try {
            const wcRes = await chrome.tabs.sendMessage(tab.id, { type: 'GET_WORD_COUNT' });
            if (wcRes && wcRes.success && wcRes.data) {
              wordCount = wcRes.data.count;
            }
          } catch (e) {
            // 静默处理错误
          }

          this.updateContentStatus(structuredData.text, wordCount, structuredData.structured);
        } else {
        }
        // 如果内容没有变化，不更新状态显示，保持当前状态
      } else {
        // 只有在确实没有内容时才更新状态
        if (!this.currentContent || !this.currentContent.trim()) {
          this.updateContentStatus('', null, []);
        }
      }
    } catch (error) {
      // 出现错误时保留当前状态，不强制更新为未检测
      if (!this.currentContent || !this.currentContent.trim()) {
        this.updateContentStatus('', null, []);
      }
    }
  }

  // 更新内容状态管理
  updateContentState(hasContent) {
    const now = Date.now();
    this.contentState.hasContent = hasContent;
    this.contentState.lastUpdateTime = now;

    // 如果有内容，标记为稳定状态
    if (hasContent) {
      this.contentState.isStable = true;
    }
    // 如果没有内容，但距离上次更新时间超过5秒，才标记为不稳定
    else if (now - this.contentState.lastUpdateTime > 5000) {
      this.contentState.isStable = false;
    }
  }

  // 更新内容状态显示
  updateContentStatus(text, wordCount = null, structured = []) {
    const statusIndicator = document.getElementById('contentStatusIndicator');
    const statusText = document.getElementById('contentStatusText');

    if (!statusIndicator || !statusText) {
      return;
    }

    const statusDot = statusIndicator.querySelector('.status-dot');

    // 更智能地判断是否有内容
    const hasContent = text && text.trim();

    // 更新内容状态管理
    this.updateContentState(hasContent);

    if (hasContent) {
      // 有内容时的状态
      statusDot.classList.add('connected');

      // 统计结构化内容信息
      const imageCount = structured.filter(item => item.type === 'image').length;
      const videoCount = structured.filter(item => item.type === 'video').length;
      const textCount = structured.filter(item => item.type === 'text').length;

      // 显示图片和视频数量

      let statusMessage = '';
      if (typeof wordCount === 'number' && wordCount >= 0) {
        statusMessage = `已检测到内容【正文字数${wordCount}`;
        if (imageCount > 0) {
          statusMessage += `，图片${imageCount}张`;
        }
        if (videoCount > 0) {
          statusMessage += `，视频${videoCount}个`;
        }
        statusMessage += '】';
      } else {
        statusMessage = '已检测到内容';
        if (imageCount > 0 || videoCount > 0) {
          statusMessage += '（包含';
          if (imageCount > 0) {
            statusMessage += `${imageCount}张图片`;
          }
          if (videoCount > 0) {
            if (imageCount > 0) statusMessage += '、';
            statusMessage += `${videoCount}个视频`;
          }
          statusMessage += '）';
        }
      }

      statusText.textContent = statusMessage;
    } else {
      // 只有在内容状态不稳定时才更新为未检测状态
      if (!this.contentState.isStable) {
        statusDot.classList.remove('connected');
        statusText.textContent = '未检测到内容';
      }
      // 如果内容状态稳定，保持当前显示状态
    }
  }

  // 实时链接监测功能 - 增强稳定性
  startLinkMonitoring() {

    // 每3秒检查一次链接状态（从2秒调整到3秒，减少资源消耗）
    this.linkMonitorInterval = setInterval(async () => {
      try {
        await this.checkLinkStatus();
      } catch (error) {
      }
    }, 3000);

    // 页面可见性变化时也检查链接状态
    document.addEventListener('visibilitychange', () => {
      if (!document.hidden) {
        // 页面变为可见时立即检查
        setTimeout(() => this.checkLinkStatus(), 100);
      }
    });

    // 添加窗口焦点变化监听
    window.addEventListener('focus', () => {
      // 窗口获得焦点时检查链接状态
      setTimeout(() => this.checkLinkStatus(), 200);
    });
  }

  // 增强Firefox兼容性的消息发送函数
  async sendMessageWithRetry(tabId, message, retries = 3, delay = 1000) {
    for (let i = 0; i < retries; i++) {
      try {
        // Firefox兼容性：优先使用browser API
        if (typeof browser !== 'undefined' && browser.tabs && browser.tabs.sendMessage) {
          const response = await browser.tabs.sendMessage(tabId, message);
          return response;
        } else if (typeof chrome !== 'undefined' && chrome.tabs && chrome.tabs.sendMessage) {
          const response = await chrome.tabs.sendMessage(tabId, message);
          return response;
        } else {
          throw new Error('浏览器API不可用');
        }
      } catch (error) {
        if (i < retries - 1) {
          // 等待后重试
          await new Promise(resolve => setTimeout(resolve, delay));
        } else {
          throw error;
        }
      }
    }
  }

  // 检查链接状态 - 增强Firefox兼容性
  async checkLinkStatus() {
    
    try {
      // 获取当前活动标签页
      
      // Firefox兼容性：优先使用browser API
      let tabs;
      if (typeof browser !== 'undefined' && browser.tabs && browser.tabs.query) {
        tabs = await browser.tabs.query({ active: true, currentWindow: true });
      } else if (typeof chrome !== 'undefined' && chrome.tabs && chrome.tabs.query) {
        tabs = await chrome.tabs.query({ active: true, currentWindow: true });
      } else {
        throw new Error('无法获取标签页信息');
      }
      
      if (tabs.length === 0) {
        this.updateLinkStatus('未找到活动标签页', 'error');
        return;
      }

      const tab = tabs[0];
      
      // 检查是否为微信公众号页面
      const isWeChat = tab.url && tab.url.includes('mp.weixin.qq.com');
      if (isWeChat) {
        this.updateLinkStatus('已连接到微信公众号', 'connected');

        // 如果是微信公众号页面，进一步检查编辑器状态
        try {
          
          // 首先测试content script是否在运行
          const testResponse = await this.sendMessageWithRetry(tab.id, {
            type: 'PING'
          }, 3, 500);
          
          const response = await this.sendMessageWithRetry(tab.id, {
            type: 'GET_EDITOR_STATUS'
          }, 3, 500);
          
          // 检查响应是否为undefined
          if (response === undefined) {
            // 尝试重新发送消息
            setTimeout(async () => {
              try {
                const retryResponse = await this.sendMessageWithRetry(tab.id, {
                  type: 'GET_EDITOR_STATUS'
                }, 3, 1000);
                
                if (retryResponse && retryResponse.success && retryResponse.data.exists) {
                  // 编辑器存在，检查内容状态
                  await this.checkContentStatus();
                } else {
                  // 只有在确实没有编辑器时才更新为未检测状态
                  if (!this.currentContent || !this.currentContent.trim()) {
                    this.updateContentStatus('', null, []);
                  }
                }
              } catch (retryError) {
              }
            }, 1000);
          } else if (response && response.success && response.data.exists) {
            // 编辑器存在，检查内容状态
            await this.checkContentStatus();
          } else {
            // 只有在确实没有编辑器时才更新为未检测状态
            if (!this.currentContent || !this.currentContent.trim()) {
              this.updateContentStatus('', null, []);
            }
          }
        } catch (error) {
          // 只在错误不是由于连接断开导致的情况下更新内容状态
          if (!error.message.includes('Could not establish connection')) {
            // 保留当前内容状态，不强制更新为未检测
            if (!this.currentContent || !this.currentContent.trim()) {
              this.updateContentStatus('', null, []);
            }
          }
        }
      } else {
        // 不是微信公众号页面 (通用模式)
        this.updateLinkStatus('已连接 (通用网页)', 'connected');
        // 尝试检查当前网页上的内容（如选中的文本）
        try {
          await this.checkContentStatus();
        } catch (error) {
          if (!this.currentContent || !this.currentContent.trim()) {
            this.updateContentStatus('', null, []);
          }
        }
      }
    } catch (error) {
      // 只在特定错误情况下更新链接状态，避免频繁更新
      if (error.message.includes('No tab') || error.message.includes('Cannot access')) {
        this.updateLinkStatus('连接检查失败', 'error');
      }
    }
  }

  // 更新链接状态显示
  updateLinkStatus(message, status) {
    const indicator = document.getElementById('statusIndicator');
    if (!indicator) return;

    const dot = indicator.querySelector('.status-dot');
    const text = indicator.querySelector('.status-text');

    if (!dot || !text) return;

    // 清除所有状态类
    dot.classList.remove('connected', 'disconnected', 'error', 'unknown');

    // 根据状态添加相应的类和文本
    switch (status) {
      case 'connected':
        dot.classList.add('connected');
        text.textContent = message;
        break;
      case 'disconnected':
        dot.classList.add('disconnected');
        text.textContent = message;
        break;
      case 'error':
        dot.classList.add('error');
        text.textContent = message;
        break;
      case 'unknown':
        dot.classList.add('unknown');
        text.textContent = message;
        break;
      default:
        text.textContent = message;
    }
  }

  // 生成内容（基于选定模板）
  // [修改] 整个函数被重构以支持流式处理
  async generateContent() {
    try { 
      
    } catch (e) {}
    // 生成前先关闭页面左侧预览面板（如已打开）
    await this.requestClosePagePreview();

    // 若选择的是VIP模板，则在生成前校验本地是否已通过验证
    if (this.selectedTemplate && this.selectedTemplate.isVip) {
      const hasVipAccess = await this.checkVipAccess();
      if (!hasVipAccess) {
        this.showNotification('此模板需要VIP权限，请先在启动器的设置中配置API Key或VIP密钥', 'warning');
        return;
      }
    }

    if (!this.currentContent || !this.currentContent.trim()) {
      
      this.showNotification('请先输入要生成的内容', 'warning');
      return;
    }

    if (!this.selectedTemplate) {
      
      this.showNotification('请先选择一个模板', 'warning');
      return;
    }

    try {
      // 删除日志：try {
      
      // 删除日志：    templateId: this.selectedTemplate?.id,
      // 删除日志：    templateName: this.selectedTemplate?.name,
      // 删除日志：    templateUrl: this.selectedTemplate?.url,
      // 删除日志：    currentContentLen: this.currentContent?.length
      // 删除日志：  });
      // 删除日志：} catch (e) {}

      // 获取结构化内容（包含文本和图片）
      const tab = await this.getCurrentTab();

      if (!tab) {
        throw new Error('无法获取当前标签页');
      }
      
      // 尝试在所有frame发送消息，优先返回首个成功的响应
      const structuredResponse = await this.sendMessageToAnyFrame(tab.id, { type: 'GET_STRUCTURED_CONTENT' });

      if (!structuredResponse || !structuredResponse.success) {
        throw new Error('获取内容结构失败');
      }

      const structuredContent = structuredResponse.data;
      // 删除日志：try {
      
      // 删除日志：    hasHtml: !!structuredContent?.html,
      // 删除日志：    htmlLen: structuredContent?.html?.length || 0,
      // 删除日志：    items: Array.isArray(structuredContent?.structured) ? structuredContent.structured.length : 0
      // 删除日志：  });
      // 删除日志：} catch (e) {}

      // 获取模板内容（使用实际模板URL，不是预览URL）
      const templateResponse = await this.sendRuntimeMessage({
        type: 'GET_TEMPLATE_CONTENT',
        data: { templateUrl: this.selectedTemplate.url } // 使用实际模板URL
      });

      if (!templateResponse || !templateResponse.success) {
        throw new Error('获取模板内容失败');
      }

      const templateContent = templateResponse.data.content;
      

      // 构建包含图片信息的要求提示词
      const structuredContentText = this.formatStructuredContent(structuredContent.structured);

      const requirementPrompt = `请将以下用户内容按照提供的HTML模板的格式和风格进行排版和美化，保持原始内容的意思不变，只进行排版优化和格式调整。请直接返回排版后的HTML内容，不要包含任何其他说明文字。

Template示例：
${templateContent}
用户内容（包含文本、图片和视频，请保持顺序）：
${structuredContentText}`;

      // 检查chrome.runtime是否可用
      if (!chrome || !chrome.runtime) {
        throw new Error('Chrome扩展API不可用');
      }

      const requestPayload = {
        type: 'PROCESS_CONTENT_STREAM',
        data: {
          content: structuredContent.html,
          prompt: requirementPrompt,
          rolePrompt: this.rolePrompt,
          templateInfo: {
            name: this.selectedTemplate.name,
            url: this.selectedTemplate.url,
            content: templateContent
          },
          structuredContent: structuredContent.structured
        }
      };
      
      

      // 发起流式请求
      const response = await this.processStreamingRequest(requestPayload);

      // 检查请求是否被后台成功接收并开始处理
      if (response && response.success && response.isStream) {
        // 设置流式状态，等待 onMessage 接收数据
        this.isStreaming = true;
        this.streamingContent = ''; // 清空之前的内容
        // 加载动画已经在 processStreamingRequest 中显示，这里无需额外操作
        // 后续的成功/失败处理将由 onMessage 中的 STREAM_COMPLETE 处理器完成
      } else {
        // 如果后台未能成功启动流式处理
        throw new Error(response?.error || '无法启动内容生成流');
      }
    } catch (error) {
      this.isStreaming = false; // 确保异常时重置状态
      
      this.hideStreamingIndicator();
      this.showErrorInResult(error.message || '生成失败，请稍后重试');
      this.showNotification(`生成失败: ${error.message}`, 'error');
    } finally {
      // [修改] 移除此处的 showLoading(false)，因为加载状态由 STREAM_COMPLETE 消息控制
      // this.showLoading(false);
    }
  }

  /**
   * 处理流式请求
   */
  async processStreamingRequest(requestData) {
    return new Promise((resolve, reject) => {
      // 10分钟超时
      const timeout = setTimeout(() => {
        this.stopTimer(); // 超时时停止计时器
        reject(new Error('请求超时 - Service Worker可能未响应（超时10分钟）'));
      }, 600000);

      // 显示初始加载状态
      this.showStreamingStart();

      // 延迟更新到步骤2，模拟参数发送完成
      setTimeout(() => {
        this.updateGenerationStep(2);
      }, 500);

      // 延迟更新到步骤3，模拟大模型调用成功
      setTimeout(() => {
        this.updateGenerationStep(3);
      }, 1500);

      // 发送消息到Service Worker
      chrome.runtime.sendMessage(requestData, (response) => {
        // 注意：这里的 response 只是一个启动确认，不是最终结果
        clearTimeout(timeout);
        
        // [修改] 只需 resolve 确认消息，不再在这里停止计时器
        resolve(response);
      });
    });
  }

  /**
   * 显示流式开始状态
   */
  showStreamingStart() {
    // 初始化计时器和步骤状态
    this.startTime = Date.now();
    this.currentStep = 1;
    this.stepInterval = null;
    
    // 显示全屏加载指示器
    const loadingOverlay = document.getElementById('loadingOverlay');
    if (loadingOverlay) {
      loadingOverlay.style.display = 'flex';
    }
    
    // 显示进度组件，隐藏简单加载文本
    const progressInfo = document.querySelector('.progress-info');
    const loadingProgress = document.querySelector('.loading-progress');
    const loadingText = document.getElementById('loadingText');
    
    if (progressInfo) progressInfo.style.display = 'flex';
    if (loadingProgress) loadingProgress.style.display = 'block';
    if (loadingText) loadingText.style.display = 'none';
    
    // 初始化进度显示
    const timerElement = document.getElementById('generationTimer');
    const stepElement = document.getElementById('currentStep');
    const progressBar = document.getElementById('progressBar');
    
    if (timerElement) timerElement.textContent = '00:00';
    if (stepElement) stepElement.textContent = '步骤1/3：正在发送参数...';
    if (progressBar) progressBar.style.width = '33%';
    
    // 启动计时器
    this.startTimer();
  }

  /**
   * 启动计时器
   */
  startTimer() {
    // 清除可能存在的旧计时器
    if (this.stepInterval) {
      clearInterval(this.stepInterval);
    }
    
    // 每秒更新一次计时器
    this.stepInterval = setInterval(() => {
      const elapsed = Date.now() - this.startTime;
      const seconds = Math.floor(elapsed / 1000);
      const minutes = Math.floor(seconds / 60);
      const remainingSeconds = seconds % 60;
      
      const timeString = `${minutes.toString().padStart(2, '0')}:${remainingSeconds.toString().padStart(2, '0')}`;
      
      const timerElement = document.getElementById('generationTimer');
      if (timerElement) {
        timerElement.textContent = timeString;
      }
    }, 1000);
  }

  /**
   * 停止计时器
   */
  stopTimer() {
    if (this.stepInterval) {
      clearInterval(this.stepInterval);
      this.stepInterval = null;
    }
  }

  /**
   * 更新生成步骤
   */
  updateGenerationStep(step) {
    this.currentStep = step;
    const stepElement = document.getElementById('currentStep');
    const progressBar = document.getElementById('progressBar');
    
    if (stepElement && progressBar) {
      let stepText = '';
      let progressWidth = '33%';
      
      switch (step) {
        case 1:
          stepText = '步骤1/3：正在发送参数...';
          progressWidth = '10%';
          break;
        case 2:
          stepText = '步骤2/3：已成功调用大模型...';
          progressWidth = '20%';
          break;
        case 3:
          stepText = '步骤3/3：流式输出，切勿更换页面和点击其他按钮...';
          progressWidth = '100%';
          break;
      }
      
      stepElement.textContent = stepText;
      progressBar.style.width = progressWidth;
    }
  }

  /**
   * 隐藏流式动效指示器
   */
  hideStreamingIndicator() {
    // 停止计时器
    this.stopTimer();
    
    // 隐藏全屏加载指示器
    const loadingOverlay = document.getElementById('loadingOverlay');
    if (loadingOverlay) {
      loadingOverlay.style.display = 'none';
    }
  }

  /**
   * 在生成结果区域显示错误信息
   */
  showErrorInResult(errorMessage) {
    const resultDiv = document.getElementById('optimizationResult');
    const contentDiv = document.getElementById('optimizedContent');
    
    if (!resultDiv || !contentDiv) {
      return;
    }
    
    // 显示结果区域
    resultDiv.style.display = 'block';
    
    // 安全地显示错误内容
    contentDiv.innerHTML = ''; // 清空内容
    
    const errorDiv = this.safeCreateElement('div', { className: 'error-result' });
    const iconDiv = this.safeCreateElement('div', { className: 'error-icon', textContent: '❌' });
    const titleDiv = this.safeCreateElement('div', { className: 'error-title', textContent: '生成失败' });
    const messageDiv = this.safeCreateElement('div', { className: 'error-message', textContent: errorMessage });
    
    const actionsDiv = this.safeCreateElement('div', { className: 'error-actions' });
    const retryBtn = this.safeCreateElement('button', { 
      className: 'btn-small btn-primary', 
      textContent: '重试' 
    });
    retryBtn.id = 'retryGenerationBtn';
    
    const closeBtn = this.safeCreateElement('button', { 
      className: 'btn-small', 
      textContent: '关闭' 
    });
    closeBtn.id = 'discardOptimizationBtn';
    
    actionsDiv.appendChild(retryBtn);
    actionsDiv.appendChild(closeBtn);
    
    errorDiv.appendChild(iconDiv);
    errorDiv.appendChild(titleDiv);
    errorDiv.appendChild(messageDiv);
    errorDiv.appendChild(actionsDiv);
    
    contentDiv.appendChild(errorDiv);
    
    // 滚动到结果区域
    resultDiv.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }

  /**
   * 重试生成
   */
  retryGeneration() {
    // 隐藏错误结果
    this.discardOptimization();
    
    // 重新调用生成方法
    this.generateContent();
  }

  /**
   * 更新流式内容显示
   */
  updateStreamingContent(content, isComplete) {
    const resultDiv = document.getElementById('optimizationResult');
    const contentDiv = document.getElementById('optimizedContent');

    if (!content) return;

    // 显示结果区域
    if (resultDiv.style.display === 'none') {
      resultDiv.style.display = 'block';
      // 滚动到结果区域
      resultDiv.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }

    // 安全地更新内容
    contentDiv.innerHTML = ''; // 清空内容
    const contentTextDiv = this.safeCreateElement('div', { 
      className: 'content-text', 
      textContent: content 
    });
    contentDiv.appendChild(contentTextDiv);

    // 如果未完成，显示加载指示器
    if (!isComplete) {
      const loadingDiv = this.safeCreateElement('div', { className: 'streaming-indicator' });
      const loadingSpan = this.safeCreateElement('span', { 
        className: 'loading-dots', 
        textContent: '正在生成...' 
      });
      loadingDiv.appendChild(loadingSpan);
      contentDiv.appendChild(loadingDiv);
    }

    // 自动滚动到底部
    contentDiv.scrollTop = contentDiv.scrollHeight;
  }

  // 显示优化结果
  showOptimizationResult(optimizedContent) {
    const resultDiv = document.getElementById('optimizationResult');
    const contentDiv = document.getElementById('optimizedContent');

    // 安全地设置优化结果内容
    contentDiv.innerHTML = ''; // 清空内容
    const contentTextDiv = this.safeCreateElement('div', { 
      className: 'content-text', 
      textContent: optimizedContent 
    });
    contentDiv.appendChild(contentTextDiv);
    resultDiv.style.display = 'block';

    // 滚动到结果区域
    resultDiv.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }

  // 应用优化结果
  async applyOptimization() {
    try {
      const optimizedContent = document.getElementById('optimizedContent').textContent;
      const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });

      const response = await chrome.tabs.sendMessage(tab.id, {
        type: 'REPLACE_CONTENT',
        data: { content: optimizedContent }
      });

      if (response && response.success) {
        this.showNotification('内容已应用', 'success');
        this.discardOptimization();
        // 刷新内容显示
        setTimeout(() => this.checkContentStatus(), 500);
      } else {
        this.showNotification('应用失败', 'error');
      }
    } catch (error) {
      this.showNotification('应用失败', 'error');
    }
  }

  // 复制优化结果
  async copyOptimization() {
    try {
      const optimizedContent = document.getElementById('optimizedContent').textContent;
      await navigator.clipboard.writeText(optimizedContent);
      this.showNotification('内容已复制到剪贴板', 'success');
    } catch (error) {
      this.showNotification('复制失败', 'error');
    }
  }

  // 丢弃优化结果
  discardOptimization() {
    document.getElementById('optimizationResult').style.display = 'none';
  }

  // ============ 模板选择相关方法 ============

  /**
   * 初始化模板选择器
   */
  async initTemplateSelector() {
    try {
      const response = await chrome.runtime.sendMessage({
        type: 'GET_TEMPLATES',
        data: { forceRefresh: false }
      });

      if (response && response.success && response.data) {
        this.populateTemplateSelector(response.data);
      }
    } catch (error) {
      // 静默处理错误
    }
  }

  /**
   * 填充模板选择器
   */
  populateTemplateSelector(templates) {
    const selector = document.getElementById('templateSelect');

    // 安全地清空现有选项（保留默认选项）
    selector.innerHTML = ''; // 清空所有选项
    const defaultOption = this.safeCreateElement('option', { textContent: '请选择模板...' });
    defaultOption.value = '';
    selector.appendChild(defaultOption);

    if (!templates || templates.length === 0) {
      const option = document.createElement('option');
      option.value = '';
      option.textContent = '暂无可用模板';
      option.disabled = true;
      selector.appendChild(option);
      return;
    }

    // 按分类组织模板
    const groupedTemplates = templates.reduce((groups, template) => {
      const category = template.category || '通用';
      if (!groups[category]) {
        groups[category] = [];
      }
      groups[category].push(template);
      return groups;
    }, {});

    // 添加分类和模板选项
    Object.entries(groupedTemplates).forEach(([category, categoryTemplates]) => {
      const optgroup = document.createElement('optgroup');
      optgroup.label = `${category} (${categoryTemplates.length})`;

      categoryTemplates.forEach(template => {
        const option = document.createElement('option');
        option.value = template.id;
        option.textContent = template.name;
        option.dataset.templateData = JSON.stringify(template);
        optgroup.appendChild(option);
      });

      selector.appendChild(optgroup);
    });
  }

  /**
   * 选择模板
   */
  selectTemplate(templateId) {
    const selector = document.getElementById('templateSelect');
    const generateBtn = document.getElementById('generateBtn');
    const templateInfo = document.getElementById('selectedTemplateInfo');

    if (!templateId) {
      this.selectedTemplate = null;
      generateBtn.disabled = true;
      templateInfo.style.display = 'none';
      return;
    }

    // 获取选中的模板数据
    const selectedOption = selector.querySelector(`option[value="${templateId}"]`);
    if (selectedOption && selectedOption.dataset.templateData) {
      try {
        this.selectedTemplate = JSON.parse(selectedOption.dataset.templateData);

        // 更新界面显示已移除，使用新的模板卡片选择机制
        generateBtn.disabled = false;
        templateInfo.style.display = 'block';

      } catch (error) {
        this.selectedTemplate = null;
        generateBtn.disabled = true;
        templateInfo.style.display = 'none';
      }
    }
  }

  /**
   * 更新已选中模板信息显示
   */
  updateSelectedTemplateInfo(template) {
    document.getElementById('selectedTemplateName').textContent = template.name;
    document.getElementById('selectedTemplateDesc').textContent = template.description;

    const typeBadge = document.getElementById('selectedTemplateType');
    typeBadge.textContent = template.type;
    typeBadge.className = `template-type-badge ${template.type}`;
  }

  // [新增] 实时更新编辑器的方法
  async updateEditorInRealtime(contentToApply) {
    try {
      // 如果 contentToApply 未定义，则使用当前累积的内容
      const finalContent = typeof contentToApply === 'string' ? contentToApply : this.streamingContent;
      await this.applyContentToEditor(finalContent);
    } catch (error) {
      
      // 在流式更新中，单个更新失败可以容忍，不中断整个流程
    }
  }

  /**
   * 应用内容到编辑器
   */
  async applyContentToEditor(content) {
    try {
      const tab = await this.getCurrentTab();
      if (!tab || !tab.id) {
        throw new Error('无法找到有效的活动标签页来应用内容');
      }
      const response = await this.sendTabMessage(tab.id, {
        type: 'REPLACE_CONTENT',
        data: { content: content }
      });
      if (response && response.success) {
        setTimeout(() => this.checkContentStatus(), 500);
        return true;
      } else {
        const errorMessage = response?.error || '未知错误';
        throw new Error(`应用到编辑器失败: ${errorMessage}`);
      }
    } catch (error) {
      throw error;
    }
  }

  // 统一的运行时消息发送助手：Firefox优先使用 browser.runtime，回退到 chrome.runtime 回调
  async sendRuntimeMessage(message) {
    try {
      const br = (typeof window !== 'undefined' && window.browser && window.browser.runtime) ? window.browser.runtime : null;
      if (br && typeof br.sendMessage === 'function') {
        return await br.sendMessage(message);
      }

      const cr = (typeof chrome !== 'undefined' && chrome.runtime) ? chrome.runtime : null;
      if (cr && typeof cr.sendMessage === 'function') {
        return await new Promise((resolve) => {
          try {
            cr.sendMessage(message, (response) => {
              if (chrome.runtime.lastError) {
                // 如果有 lastError，说明消息发送失败，返回 undefined
                resolve(undefined);
              } else {
                resolve(response);
              }
            });
          } catch (err) {
            resolve(undefined);
          }
        });
      }

      return undefined;
    } catch (e) {
      return undefined;
    }
  }

  // 统一的Tab消息发送助手：Firefox优先使用 browser.tabs，回退到 chrome.tabs 回调
  async sendTabMessage(tabId, message) {
    try {
      const bt = (typeof window !== 'undefined' && window.browser && window.browser.tabs) ? window.browser.tabs : null;
      if (bt && typeof bt.sendMessage === 'function') {
        return await bt.sendMessage(tabId, message);
      }

      const ct = (typeof chrome !== 'undefined' && chrome.tabs) ? chrome.tabs : null;
      if (ct && typeof ct.sendMessage === 'function') {
        return await new Promise((resolve) => {
          try {
            ct.sendMessage(tabId, message, (response) => {
               if (chrome.runtime.lastError) {
                resolve({ success: false, error: chrome.runtime.lastError.message });
              } else {
                resolve(response);
              }
            });
          } catch (err) {
            resolve({ success: false, error: err.message });
          }
        });
      }

      return undefined;
    } catch (e) {
      return { success: false, error: e.message };
    }
  }

  // 获取所有frame并尝试在所有frame发送一次，返回第一个成功的响应
  async sendMessageToAnyFrame(tabId, message) {
    try {
      const frames = await new Promise((resolve) => {
        if (chrome.webNavigation && chrome.webNavigation.getAllFrames) {
          chrome.webNavigation.getAllFrames({ tabId }, (f) => resolve(f || []));
        } else {
          resolve([]);
        }
      });

      // 优先尝试不带frameId（顶层）
      const topResponse = await this.sendTabMessage(tabId, message);
      if (topResponse && topResponse.success) return topResponse;

      // 逐个frame尝试
      for (const f of frames) {
        if (typeof f.frameId === 'number') {
          const resp = await new Promise((resolve) => {
            try {
              chrome.tabs.sendMessage(tabId, message, { frameId: f.frameId }, (r) => {
                if (chrome.runtime.lastError) {
                  resolve(undefined);
                } else {
                  resolve(r);
                }
              });
            } catch (e) {
              resolve(undefined);
            }
          });
          if (resp && resp.success) return resp;
        }
      }
      return topResponse; // 返回顶层的结果（可能为undefined/失败）
    } catch (e) {
      return undefined;
    }
  }

  // 加载配置
  async loadConfig() {
    try {
      const response = await this.sendRuntimeMessage({ type: 'GET_CONFIG' });
      if (response && response.success !== false) {
        this.config = { ...this.config, ...response };
      }
    } catch (error) {
      // 静默处理错误
    }
  }

  // 保存配置
  async saveConfig() {
    try {
      const enablePlugin = document.getElementById('enablePlugin');
      const customPromptInput = document.getElementById('customPromptInput');

      const newConfig = {
        isEnabled: enablePlugin ? enablePlugin.checked : false,
        customPrompt: customPromptInput ? customPromptInput.value.trim() : ''
      };

      const response = await this.sendRuntimeMessage({
        type: 'SET_CONFIG',
        data: newConfig
      });

      if (response && response.success) {
        this.config = { ...this.config, ...newConfig };
        this.showNotification('设置已保存', 'success');
        this.updateStatus(newConfig.isEnabled);
      } else {
        this.showNotification('保存失败', 'error');
      }
    } catch (error) {
      this.showNotification('保存失败', 'error');
    }
  }


  // 更新状态指示器
  updateStatus(isConnected) {
    const indicator = document.getElementById('statusIndicator');
    const dot = indicator.querySelector('.status-dot');
    const text = indicator.querySelector('.status-text');

    if (isConnected) {
      dot.classList.add('connected');
      text.textContent = '已连接';
    } else {
      dot.classList.remove('connected');
      text.textContent = '未连接';
    }
  }

  // 显示加载状态
  showLoading(show) {
    const overlay = document.getElementById('loadingOverlay');
    if (overlay) {
      overlay.style.display = show ? 'flex' : 'none';
    }

    // 禁用相关按钮
    const generateBtn = document.getElementById('generateBtn');

    if (generateBtn) {
      generateBtn.disabled = show;
    }
  }

  // 滑动时锁定按钮
  lockButtonsDuringScroll(lock) {
    const generateBtn = document.getElementById('generateBtn');

    if (generateBtn) {
      generateBtn.disabled = lock;
    }
  }

  // 显示通知
  showNotification(message, type = 'info') {
    const notification = document.getElementById('notification');
    if (!notification) {
      return;
    }

    const icon = notification.querySelector('.notification-icon');
    const text = notification.querySelector('.notification-text');

    if (!icon || !text) {
      return;
    }

    // 设置图标
    const icons = {
      success: '✅',
      error: '❌',
      warning: '⚠️',
      info: 'ℹ️'
    };
    icon.textContent = icons[type] || icons.info;

    // 设置文本和样式
    text.textContent = message;
    notification.className = `notification ${type}`;
    notification.style.display = 'flex';

    // 自动隐藏
    setTimeout(() => {
      notification.style.display = 'none';
    }, 5000);
  }












  // [修改] onMessage 被重构以处理流式消息
// sidepanel.js
// ...
  onMessage(message, sender, sendResponse) {
    if (message.source === 'content-script') {
      switch (message.type) {
        case 'CONTENT_UPDATED':
          this.currentContent = message.data.content;
          clearTimeout(this.contentCheckDebounceTimer);
          this.contentCheckDebounceTimer = setTimeout(() => {
            this.refreshStructuredContent();
          }, 300);
          break;
          
        case 'WORD_COUNT_UPDATED':
          const currentText = this.currentContent ? this.currentContent.replace(/<[^>]*>/g, '') : '';
          const currentStructured = this.currentStructuredContent || [];
          if (currentText && currentText.trim()) {
            this.updateContentStatus(currentText, message.data.count, currentStructured);
          }
          break;
      }
    } else {
      // 处理来自 service-worker 的消息
      switch (message.type) {
        case 'STREAM_UPDATE':
          if (this.isStreaming && message.data.content) {
            this.streamingContent += message.data.content;
            this.debouncedUpdateEditor(); // 调用防抖函数来更新编辑器
          }
          break;

        case 'STREAM_COMPLETE':
          this.isStreaming = false;
          this.hideStreamingIndicator(); // 隐藏加载动画
          
          if (message.success) {
            // 最后再用完整内容更新一次，确保内容完全正确
            this.updateEditorInRealtime(message.data.content);
            this.streamingContent = message.data.content; // 更新最终内容

            let successMessage = '内容已流式生成并应用';
            if (message.data.tokenUsage) {
              const usage = message.data.tokenUsage;
              const tokenInfo = [];
              if (usage.prompt_tokens) tokenInfo.push(`输入${usage.prompt_tokens}`);
              if (usage.completion_tokens) tokenInfo.push(`输出${usage.completion_tokens}`);
              if (usage.total_tokens) tokenInfo.push(`总计${usage.total_tokens}`);
              if (tokenInfo.length > 0) {
                successMessage += `，Token数：${tokenInfo.join('、')}`;
              }
            }
            this.showNotification(successMessage, 'success');
          } else {
            this.showErrorInResult(message.error || '生成失败，请稍后重试');
            this.showNotification(`生成失败: ${message.error}`, 'error');
          }
          break;
      }
    }

    // 虽然在这个场景下我们不使用 sendResponse，但保留这个模式是好的实践
    if (sendResponse) {
      sendResponse({ received: true });
    }
    
    // 【核心修复】必须返回 true 以表明我们将异步处理消息
    return true;
  }
// ...












  // 刷新结构化内容
  async refreshStructuredContent() {
    try {
      const tab = await this.getCurrentTab();
      if (!tab) return;
      
      const response = await this.sendTabMessage(tab.id, {
        type: 'GET_STRUCTURED_CONTENT'
      });
      
      if (response && response.success) {
        this.currentStructuredContent = response.data.structured;
        const currentText = response.data.text;
        
        try {
          const wcRes = await this.sendTabMessage(tab.id, { type: 'GET_WORD_COUNT' });
          const wordCount = (wcRes && wcRes.success && wcRes.data) ? wcRes.data.count : null;
          this.updateContentStatus(currentText, wordCount, this.currentStructuredContent);
        } catch (e) {
          this.updateContentStatus(currentText, null, this.currentStructuredContent);
        }
      }
    } catch (error) {
      // 静默处理错误
    }
  }

  // 格式化结构化内容为文本，供大模型理解
  formatStructuredContent(structured) {
    if (!structured || !Array.isArray(structured)) {
      return '';
    }

    let formattedContent = '';
    
    structured.forEach((item, index) => {
      if (item.type === 'text') {
        formattedContent += `[文本${index + 1}] ${item.content}\n\n`;
      } else if (item.type === 'image') {
        const imgData = item.content;
        formattedContent += `[图片${index + 1}] `;
        formattedContent += `元素：${imgData.element}\n`;
        if (imgData.url) formattedContent += `URL：${imgData.url}\n`;
        if (imgData.alt) formattedContent += `描述：${imgData.alt}\n`;
        formattedContent += '\n';
      } else if (item.type === 'video') {
        const videoData = item.content;
        formattedContent += `[视频${index + 1}] `;
        formattedContent += `元素：${videoData.element}\n`;
        if (videoData.url) formattedContent += `URL：${videoData.url}\n`;
        if (videoData.mpvid) formattedContent += `视频ID：${videoData.mpvid}\n`;
        if (videoData.cover) formattedContent += `封面：${videoData.cover}\n`;
        if (videoData.width && videoData.height) formattedContent += `尺寸：${videoData.width}x${videoData.height}\n`;
        formattedContent += '\n';
      }
    });
    
    return formattedContent;
  }

  // 安全的HTML转义函数
  escapeHtml(text) {
    if (typeof text !== 'string') {
      return '';
    }
    return window.domSanitizer ? window.domSanitizer.escapeHtml(text) : text;
  }

  // 安全的DOM内容设置
  safeSetContent(element, content, isHtml = false) {
    if (!element) return;
    
    if (window.domSanitizer) {
      if (isHtml) {
        window.domSanitizer.safeSetInnerHTML(element, content);
      } else {
        window.domSanitizer.safeSetTextContent(element, content);
      }
    } else {
      // 降级处理
      if (isHtml) {
        element.textContent = content; // 安全降级，不允许HTML
      } else {
        element.textContent = content;
      }
    }
  }

  // 安全创建DOM元素
  safeCreateElement(tagName, options = {}) {
    if (window.domSanitizer) {
      return window.domSanitizer.createElement(tagName, options);
    } else {
      // 降级处理
      const element = document.createElement(tagName);
      if (options.className) {
        element.className = options.className;
      }
      if (options.textContent) {
        element.textContent = options.textContent;
      }
      return element;
    }
  }

  /**
   * 加载API配置和VIP密钥
   */
  async loadApiConfig() {
    try {
      const apiResponse = await this.sendRuntimeMessage({ type: 'GET_API_CONFIG' });

      if (apiResponse && apiResponse.success) {
        const apiConfig = apiResponse.data;

        const apiKeyInput = document.getElementById('apiKeyInput');
        const modelInput = document.getElementById('modelInput');
        const vipKeyInput = document.getElementById('vipKeyInput');

        // 填充 API Key 和 Model
        if (apiKeyInput && apiConfig.apiKey) {
          apiKeyInput.value = apiConfig.apiKey;
          this.validateApiKeyInput();
        }
        if (modelInput) {
          modelInput.value = apiConfig.model || '';
        }

        const vipStatus = document.getElementById('vipStatus');
        const vipInfo = document.getElementById('vipInfo');

        // 【核心修改】处理 VIP 密钥的逻辑
        if (vipKeyInput && apiConfig.vipKey) {
          // 1. 无论如何，只要有密钥，就先把它填入输入框
          vipKeyInput.value = apiConfig.vipKey;
          this.validateVipKeyInput();

          // 2. 立即显示一个“正在检查”的中间状态，给用户即时反馈
          vipStatus.style.display = 'block';
          vipStatus.className = 'vip-status'; // 移除 success/error 类
          vipStatus.querySelector('.status-text').textContent = 'VIP密钥检查中...';
          vipInfo.style.display = 'none'; // 暂时隐藏天数信息

          // 3. 然后在后台发起状态检查，这个过程不会阻塞UI
          this.checkVipKeyStatus(); 
          
        } else {
          // 如果没有保存的VIP密钥，确保UI是干净的
          if (vipKeyInput) vipKeyInput.value = '';
          if (vipStatus) vipStatus.style.display = 'none';
          if (vipInfo) vipInfo.style.display = 'none';
        }
      }
    } catch (error) {
      // 即使加载配置失败，也要确保UI不会显示错误的状态
      const vipStatus = document.getElementById('vipStatus');
      const vipInfo = document.getElementById('vipInfo');
      if (vipStatus) vipStatus.style.display = 'none';
      if (vipInfo) vipInfo.style.display = 'none';
    }
  }

  // 保存所有配置
  saveAllConfig() {
    const apiKeyInput = document.getElementById('apiKeyInput');
    const modelInput = document.getElementById('modelInput');
    const vipKeyInput = document.getElementById('vipKeyInput');

    const apiKey = apiKeyInput ? apiKeyInput.value : '';
    const model = modelInput ? modelInput.value : '';
    const vipKey = vipKeyInput ? vipKeyInput.value : '';

    this.sendRuntimeMessage({ type: 'SET_API_CONFIG', data: { apiKey, model, vipKey } });
  }

  // 验证API Key输入
  validateApiKeyInput() {
    const apiKeyInput = document.getElementById('apiKeyInput');
    const apiKey = apiKeyInput ? apiKeyInput.value : '';

    if (apiKey) {
      apiKeyInput.classList.remove('invalid');
    } else {
      apiKeyInput.classList.add('invalid');
    }
  }

  // 验证VIP Key输入
  validateVipKeyInput() {
    const vipKeyInput = document.getElementById('vipKeyInput');
    const vipKey = vipKeyInput ? vipKeyInput.value : '';

    if (vipKey) {
      vipKeyInput.classList.remove('invalid');
    } else {
      vipKeyInput.classList.add('invalid');
    }
  }

  // 检查VIP Key状态
  checkVipKeyStatus() {
    const vipKeyInput = document.getElementById('vipKeyInput');
    const vipKey = vipKeyInput ? vipKeyInput.value : '';

    if (vipKey) {
      this.sendRuntimeMessage({ type: 'CHECK_VIP_KEY_STATUS', data: { vipKey } });
    }
  }

  // 切换标签页
  switchTab(tabId) {
    const tabs = document.querySelectorAll('.tab');
    const contents = document.querySelectorAll('.tab-content');

    tabs.forEach(tab => {
      if (tab.id === tabId) {
        tab.classList.add('active');
      } else {
        tab.classList.remove('active');
      }
    });

    contents.forEach(content => {
      if (content.id === `${tabId}-content`) {
        content.style.display = 'block';
      } else {
        content.style.display = 'none';
      }
    });
  }

  /**
   * 保存所有配置（API配置 + VIP密钥）
   */
  async saveAllConfig() {
    try {
      const apiKeyInput = document.getElementById('apiKeyInput');
      const modelInput = document.getElementById('modelInput');
      const vipKeyInput = document.getElementById('vipKeyInput');

      if (!apiKeyInput || !modelInput || !vipKeyInput) {
        this.showNotification('配置表单元素未找到', 'error');
        return;
      }

      const apiConfig = {
        apiKey: apiKeyInput.value.trim(),
        model: modelInput.value.trim()
      };

      if (!apiConfig.apiKey || !this.validateApiKey(apiConfig.apiKey)) {
        this.showNotification('API Key格式不正确', 'error');
        return;
      }

      const vipKey = vipKeyInput.value.trim();
      if (vipKey && !this.validateVipKey(vipKey)) {
        this.showNotification('VIP密钥格式不正确', 'error');
        return;
      }

      this.showNotification('正在保存配置...', 'info');

      // 统一保存 API Key 和 Model (后台不再单独处理 vipKey 保存到 apiConfig)
      const baseConfigResponse = await this.sendRuntimeMessage({
          type: 'SAVE_API_CONFIG',
          data: { ...apiConfig, vipKey: vipKey }
      });

      if (!baseConfigResponse || !baseConfigResponse.success) {
          this.showNotification('API配置保存失败: ' + (baseConfigResponse?.error || '未知错误'), 'error');
          return;
      }
      
      const vipStatus = document.getElementById('vipStatus');
      const vipInfo = document.getElementById('vipInfo');

      // 如果有VIP密钥，则进行验证并更新UI
      if (vipKey) {
        // 发送保存并验证的请求
        const vipResponse = await this.sendRuntimeMessage({
          type: 'SAVE_VIP_KEY',
          data: { vipKey: vipKey }
        });

        if (vipResponse && vipResponse.success) {
          // 【核心优化】直接使用返回的数据更新UI，不再二次请求
          this.showNotification('所有配置已保存，VIP密钥有效', 'success');
          
          vipStatus.style.display = 'block';
          vipStatus.className = 'vip-status success';
          vipStatus.querySelector('.status-text').textContent = 'VIP密钥有效';
          
          this.displayVipInfo(vipResponse.data); // 使用返回的数据更新天数
          vipInfo.style.display = 'block';

        } else {
          // 保存成功但验证失败，或保存彻底失败
          this.showNotification('配置已保存，但VIP密钥验证失败: ' + (vipResponse?.error || '未知错误'), 'warning');
          vipStatus.style.display = 'block';
          vipStatus.className = 'vip-status error';
          vipStatus.querySelector('.status-text').textContent = 'VIP密钥无效或验证失败';
          vipInfo.style.display = 'none';
        }
      } else {
        // 如果没有输入VIP密钥，则清空状态并显示成功
        this.showNotification('配置保存成功', 'success');
        if (vipStatus) vipStatus.style.display = 'none';
        if (vipInfo) vipInfo.style.display = 'none';
        this.stopVipKeyMonitoring();
      }

    } catch (error) {
      
      this.showNotification('保存失败: ' + error.message, 'error');
    }
  }













  /**
   * 保存API配置
   */
  async saveApiConfig() {
    try {
      const apiKeyInput = document.getElementById('apiKeyInput');
      const modelInput = document.getElementById('modelInput');

      if (!apiKeyInput || !modelInput) {
        this.showNotification('API配置表单元素未找到', 'error');
        return;
      }

      const apiConfig = {
        apiKey: apiKeyInput.value.trim(),
        model: modelInput.value.trim()
      };


      // 验证API Key
      if (!apiConfig.apiKey) {
        this.showNotification('API Key不能为空', 'error');
        return;
      }

      if (!this.validateApiKey(apiConfig.apiKey)) {
        this.showNotification('API Key格式不正确', 'error');
        return;
      }

      const response = await this.sendRuntimeMessage({
        type: 'SAVE_API_CONFIG',
        data: apiConfig
      });

      if (response && response.success) {
        this.showNotification('API配置保存成功', 'success');
      } else {
        this.showNotification('保存失败: ' + (response?.error || '未知错误'), 'error');
      }
    } catch (error) {
      
      this.showNotification('保存失败: ' + error.message, 'error');
    }
  }

  /**
   * 验证API Key输入
   */
  validateApiKeyInput() {
    const apiKeyInput = document.getElementById('apiKeyInput');

    if (!apiKeyInput) {
      return;
    }

    const apiKey = apiKeyInput.value.trim();

    if (apiKey && this.validateApiKey(apiKey)) {
      apiKeyInput.style.borderColor = '#28a745';
    } else {
      apiKeyInput.style.borderColor = apiKey ? '#dc3545' : '#ddd';
    }
  }

  /**
   * 验证API Key格式
   */
  validateApiKey(apiKey) {
    return apiKey && typeof apiKey === 'string' && apiKey.length > 10;
  }

  /**
   * 切换API Key显示/隐藏
   */
  toggleApiKeyVisibility() {
    const apiKeyInput = document.getElementById('apiKeyInput');
    const toggleBtn = document.getElementById('toggleApiKeyBtn');

    if (!apiKeyInput || !toggleBtn) {
      return;
    }

    // 直接切换输入框类型，同时切换按钮文本
    if (apiKeyInput.type === 'password') {
      apiKeyInput.type = 'text';
      toggleBtn.textContent = '🙈';
    } else {
      apiKeyInput.type = 'password';
      toggleBtn.textContent = '👁️';
    }
  }



  /**
   * 加载模板预览
   */
  async loadTemplatePreview(templates) {
    // 限制同时加载的数量以提升性能
    const maxConcurrent = 3;
    let loadedCount = 0;

    for (let i = 0; i < templates.length; i += maxConcurrent) {
      const batch = templates.slice(i, i + maxConcurrent);
      const promises = batch.map(template => this.loadSingleTemplatePreview(template));

      try {
        await Promise.all(promises);
        loadedCount += batch.length;

      } catch (error) {
        // 静默处理错误
      }
    }
  }

  /**
   * 加载单个模板预览
   */
  async loadSingleTemplatePreview(template) {
    try {
      const thumbnailContainer = document.getElementById(`thumbnail-${template.id}`);
      if (!thumbnailContainer) return;

      // 使用预览图URL获取内容（html字段可能为data:image Base64，或回退到url字段）
      const previewUrl = template.html || template.url;
      

      if (!previewUrl) {
        this.showPreviewError(thumbnailContainer, '模板预览地址无效');
        return;
      }

      // 如果是Base64图片，直接渲染图片作为缩略图
      if (typeof previewUrl === 'string' && previewUrl.startsWith('data:image/')) {
        // 安全地清空容器
        while (thumbnailContainer.firstChild) {
          thumbnailContainer.removeChild(thumbnailContainer.firstChild);
        }
        thumbnailContainer.style.width = '100%';
        thumbnailContainer.style.height = '600px';
        thumbnailContainer.style.overflow = 'hidden';
        thumbnailContainer.style.position = 'relative';

        const img = document.createElement('img');
        img.src = previewUrl;
        img.alt = template.name || '模板预览图';
        img.style.width = '100%';
        img.style.height = '100%';
        img.style.objectFit = 'contain';
        img.style.background = 'white';
        img.referrerPolicy = 'no-referrer';

        thumbnailContainer.appendChild(img);
        
        return; // 已渲染图片，结束
      }

      // 否则按原逻辑请求并渲染HTML预览
      const response = await this.sendRuntimeMessage({
        type: 'GET_TEMPLATE_CONTENT',
        data: { templateUrl: previewUrl }
      });
      

      if (response && response.success && response.data) {
        const content = response.data.content;
        if (!content || typeof content !== 'string' || content.trim().length === 0) {
          this.showPreviewError(thumbnailContainer, '模板内容为空');
          return;
        }
        const htmlContent = content;

        // 创建iframe预览
        const iframe = document.createElement('iframe');
        iframe.style.width = '100%';    // 宽度匹配外框容器
        iframe.style.height = '600px';   // 固定预览高度600px
        iframe.style.border = 'none';
        iframe.style.transformOrigin = 'top left';
        iframe.style.pointerEvents = 'none';
        iframe.style.background = 'white';
        iframe.style.display = 'block';
        iframe.style.overflow = 'hidden'; // 防止iframe内部滚动条
        iframe.style.transform = 'none'; // 初始无缩放
        iframe.style.position = 'relative';

        // 设置安全属性（移除allow-scripts以避免安全风险）
        iframe.sandbox = 'allow-same-origin';

        // 使用更安全的方式设置iframe内容
        iframe.addEventListener('load', () => {
          try {
            const iframeDoc = iframe.contentDocument || iframe.contentWindow.document;

            // 立即应用基础的600px限制，防止闪烁
            iframe.style.height = '600px';
            thumbnailContainer.style.height = '600px';

            // 创建样式元素 - 为缩放适配优化的样式
            const style = iframeDoc.createElement('style');
            style.textContent = `
              html, body {
                margin: 0;
                padding: 0;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
                background: white;
                /* 强制限制高度为600px，隐藏超出内容 */
                height: 600px !important;
                max-height: 600px !important;
                overflow: hidden !important;
                width: auto;
                min-width: auto;
              }
              body {
                padding: 8px;
                /* 确保body也限制在600px内 */
                height: 592px !important;
                max-height: 592px !important;
                width: auto;
                min-height: auto;
                display: block;
                overflow: hidden !important;
                box-sizing: border-box;
              }
              .template-container {
                width: auto;
                /* 容器内容高度限制 */
                height: 584px !important;
                max-height: 584px !important;
                padding: 0;
                margin: 0;
                overflow: hidden !important;
                display: block;
                box-sizing: border-box;
              }
              * {
                box-sizing: border-box;
              }
              p, div, h1, h2, h3, h4, h5, h6 {
                margin: 2px 0;
                line-height: 1.2;
                word-wrap: normal;
                white-space: normal;
                font-size: 12px;
                /* 防止文本溢出 */
                overflow: hidden;
              }
              img {
                max-width: 100%;
                max-height: 200px;
                height: auto;
                display: block;
              }
              section, article, aside, nav, header, footer, main {
                width: auto;
                max-height: 200px;
                overflow: hidden;
              }
              table {
                width: auto;
                white-space: nowrap;
                max-height: 200px;
                overflow: hidden;
              }
            `;

            // 创建容器元素
            const container = iframeDoc.createElement('div');
            container.className = 'template-container';

            // 安全地设置内容，使用DOM清理器
            this.safeSetContent(container, htmlContent, true);

            // 安全地清空并重新构建文档
            while (iframeDoc.head.firstChild) {
              iframeDoc.head.removeChild(iframeDoc.head.firstChild);
            }
            while (iframeDoc.body.firstChild) {
              iframeDoc.body.removeChild(iframeDoc.body.firstChild);
            }

            iframeDoc.head.appendChild(style);
            iframeDoc.body.appendChild(container);

            // 等待内容加载完成后确保预览样式正确
            setTimeout(() => {
              // 由于CSS已经强制限制了50px，这里只需要确保容器样式正确
              this.ensurePreviewContainerStyle(thumbnailContainer);
            }, 100); // 减少延迟，因为不需要复杂计算

            try {
              
            } catch (e) {}
          } catch (error) {
            this.showPreviewError(thumbnailContainer, '预览加载失败');
          }
        });

        iframe.onerror = () => {
          this.showPreviewError(thumbnailContainer, 'iframe加载失败');
        };

        // 安全地清空加载状态并添加iframe
        while (thumbnailContainer.firstChild) {
          thumbnailContainer.removeChild(thumbnailContainer.firstChild);
        }

        // 立即设置容器默认预览样式，防止闪烁
        thumbnailContainer.style.width = '100%';
        thumbnailContainer.style.height = '600px';
        thumbnailContainer.style.overflow = 'hidden';
        thumbnailContainer.style.position = 'relative';

        thumbnailContainer.appendChild(iframe);

        // 滑动支持将在iframe加载完成后启用

      } else {
        // 提供更详细的错误信息
        let errorMsg = '内容获取失败';
        if (response) {
          if (!response.success) {
            errorMsg = response.error || '服务器返回失败';
          } else if (!response.data) {
            errorMsg = '响应数据为空';
          }
        } else {
          errorMsg = '无响应数据';
        }
        
        this.showPreviewError(thumbnailContainer, errorMsg);
      }
    } catch (error) {
      const thumbnailContainer = document.getElementById(`thumbnail-${template.id}`);
      if (thumbnailContainer) {
        this.showPreviewError(thumbnailContainer, `加载异常: ${error.message}`);
      }
    }
  }

  /**
   * 显示预览错误
   */
  showPreviewError(container, errorMsg) {
    // 安全地显示预览错误
    while (container.firstChild) {
      container.removeChild(container.firstChild);
    }
    
    const errorDiv = this.safeCreateElement('div', { className: 'preview-error' });
    const iconSpan = this.safeCreateElement('span', { className: 'error-icon', textContent: '⚠️' });
    const textSpan = this.safeCreateElement('span', { className: 'error-text', textContent: errorMsg });
    
    errorDiv.appendChild(iconSpan);
    errorDiv.appendChild(textSpan);
    container.appendChild(errorDiv);
  }

  /**
   * 确保预览容器样式正确（简化版本）
   */
  ensurePreviewContainerStyle(container) {
    if (!container) return;

    // 强制设置容器固定600px高度
    container.style.width = '100%';
    container.style.height = '600px';
    container.style.overflow = 'hidden';
    container.style.position = 'relative';
    container.style.boxSizing = 'border-box';

    // 确保内部iframe也符合预期
    const iframe = container.querySelector('iframe');
    if (iframe) {
      iframe.style.width = '100%';
      iframe.style.height = '600px';
      iframe.style.maxHeight = '600px';
      iframe.style.overflow = 'hidden';
      iframe.style.border = 'none';
      iframe.style.display = 'block';
    }

  }

  /**
   * 应用预览样式
   */
  applyPreviewStyle(iframe, container, templateContent) {
    // 固定预览高度为600px
    const previewHeight = 600;

    // 设置容器样式
    container.style.width = '100%';
    container.style.height = previewHeight + 'px';
    container.style.overflow = 'hidden';
    container.style.position = 'relative';

    // 设置iframe样式
    iframe.style.width = '100%';
    iframe.style.height = previewHeight + 'px';
    iframe.style.border = 'none';
    iframe.style.display = 'block';
  }

  /**
   * 应用默认预览样式（降级方案）
   */
  applyDefaultPreviewStyle(iframe, container) {
    // 固定预览高度为600px
    const previewHeight = 600;

    // 设置容器样式
    container.style.width = '100%';
    container.style.height = previewHeight + 'px';
    container.style.overflow = 'hidden';
    container.style.position = 'relative';

    // 设置iframe样式
    iframe.style.width = '100%';
    iframe.style.height = previewHeight + 'px';
    iframe.style.transform = 'none';
    iframe.style.border = 'none';
    iframe.style.display = 'block';
  }

  /**
   * 显示悬浮预览框
   */
  async showHoverPreview(event, templateId, templateUrl, templateName) {
    // 防抖：如果正在显示相同的模板，直接返回
    if (this.currentPreviewTemplateId === templateId) {
      return;
    }

    // 记录当前预览的模板ID
    this.currentPreviewTemplateId = templateId;
    

    // 清除之前的预览框（切换到新模板时）
    this.hideHoverPreview(true);

    // 创建预览框
    const previewBox = document.createElement('div');
    previewBox.className = 'hover-preview';
    previewBox.id = 'hover-preview-box';
    previewBox.style.position = 'fixed'; // 使用fixed定位
    previewBox.style.zIndex = '10000'; // 高z-index确保在最前面
    previewBox.style.backgroundColor = 'white';
    previewBox.style.border = '1px solid #ddd';
    previewBox.style.borderRadius = '8px';
    previewBox.style.boxShadow = '0 4px 20px rgba(0,0,0,0.15)';
    previewBox.style.width = '400px';
    previewBox.style.maxHeight = '650px';
    previewBox.style.overflow = 'hidden';

    // 创建头部
    const header = this.safeCreateElement('div', { className: 'hover-preview-header' });
    const titleSpan = this.safeCreateElement('span', { textContent: templateName });
    const closeBtn = this.safeCreateElement('button', { 
      className: 'hover-preview-close', 
      textContent: '×' 
    });
    
    header.appendChild(titleSpan);
    header.appendChild(closeBtn);

    // 添加关闭按钮事件监听器
    closeBtn.addEventListener('click', () => {
      closeBtn.closest('.hover-preview').remove();
    });

    // 创建内容区域
    const content = document.createElement('div');
    content.className = 'hover-preview-content';

    // 创建iframe
    const iframe = document.createElement('iframe');
    iframe.style.width = '100%';
    iframe.style.height = '100%';
    iframe.style.border = 'none';
    iframe.style.background = 'white';

    content.appendChild(iframe);
    previewBox.appendChild(header);
    previewBox.appendChild(content);

    // 添加到页面最外层（document.body的父级或直接到document.body）
    // 如果是在侧栏中，尝试添加到更外层的容器
    let targetContainer = document.body;

    // 检查是否在iframe或侧栏容器中
    if (window.parent !== window) {
      // 在iframe中，尝试添加到父窗口
      try {
        targetContainer = window.parent.document.body;
      } catch (e) {
        // 跨域限制，使用当前document.body
        targetContainer = document.body;
      }
    }

    targetContainer.appendChild(previewBox);

    // 定位预览框
    this.positionHoverPreview(previewBox, event);

    // 加载完整内容
      try {
        const response = await this.sendRuntimeMessage({
        type: 'GET_TEMPLATE_CONTENT',
        data: { templateUrl: templateUrl }
      });

      if (response && response.success && response.data) {
        const content = response.data.content;
        if (!content || typeof content !== 'string' || content.trim().length === 0) {
          const contentDiv = previewBox.querySelector('.hover-preview-content');
          if (contentDiv) {
            const emptyDiv = this.safeCreateElement('div', { 
              textContent: '模板内容为空' 
            });
            emptyDiv.style.cssText = 'padding: 20px; text-align: center; color: #999;';
            contentDiv.innerHTML = '';
            contentDiv.appendChild(emptyDiv);
          }
          return;
        }
        const htmlContent = content;

        // 设置iframe内容
        iframe.addEventListener('load', () => {
          try {
            const iframeDoc = iframe.contentDocument || iframe.contentWindow.document;

            // 创建样式元素
            const style = iframeDoc.createElement('style');
            style.textContent = `
              html, body {
                margin: 0;
                padding: 0;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
                background: white;
                width: auto;
                min-width: auto;
                overflow: visible;
              }
              body {
                padding: 16px;
                width: auto;
                min-height: auto;
                display: block;
                overflow: visible;
              }
              .template-container {
                width: auto;
                min-height: auto;
                padding: 0;
                margin: 0;
                overflow: visible;
                display: block;
              }
              * {
                box-sizing: border-box;
              }
              p, div, h1, h2, h3, h4, h5, h6 {
                margin: 8px 0;
                line-height: 1.5;
                word-wrap: normal;
                white-space: normal;
                font-size: 14px;
              }
              img {
                max-width: 100%;
                height: auto;
                display: block;
              }
              section, article, aside, nav, header, footer, main {
                width: auto;
              }
              table {
                width: auto;
                white-space: nowrap;
              }
            `;

            // 创建容器元素
            const container = iframeDoc.createElement('div');
            container.className = 'template-container';

            // 安全地设置内容，使用DOM清理器
            this.safeSetContent(container, htmlContent, true);

            // 安全地清空并重新构建文档
            while (iframeDoc.head.firstChild) {
              iframeDoc.head.removeChild(iframeDoc.head.firstChild);
            }
            while (iframeDoc.body.firstChild) {
              iframeDoc.body.removeChild(iframeDoc.body.firstChild);
            }

            iframeDoc.head.appendChild(style);
            iframeDoc.body.appendChild(container);

            // 调整iframe尺寸以显示完整内容
            setTimeout(() => {
              this.adjustFullPreviewIframeSize(iframe);
            }, 100);

          } catch (error) {
            const errorDiv = this.safeCreateElement('div', { 
              textContent: '预览加载失败' 
            });
            errorDiv.style.cssText = 'padding: 20px; text-align: center; color: #999;';
            content.innerHTML = '';
            content.appendChild(errorDiv);
          }
        });

        iframe.srcdoc = htmlContent;

      } else {
        // 提供更详细的错误信息
        let errorMsg = '内容获取失败';
        if (response) {
          if (!response.success) {
            errorMsg = response.error || '服务器返回失败';
          } else if (!response.data) {
            errorMsg = '响应数据为空';
          }
        } else {
          errorMsg = '无响应数据';
        }
        const errorDiv = this.safeCreateElement('div', { 
          textContent: errorMsg 
        });
        errorDiv.style.cssText = 'padding: 20px; text-align: center; color: #999;';
        content.innerHTML = '';
        content.appendChild(errorDiv);
      }
    } catch (error) {
      const errorDiv = this.safeCreateElement('div', { 
        textContent: `加载异常: ${error.message}` 
      });
      errorDiv.style.cssText = 'padding: 20px; text-align: center; color: #999;';
      content.innerHTML = '';
      content.appendChild(errorDiv);
    }

    // 显示预览框
    setTimeout(() => {
      previewBox.classList.add('show');
    }, 10);

    // 添加鼠标事件处理
    previewBox.addEventListener('mouseenter', () => {
      this.hoverPreviewVisible = true;
      // 取消延迟隐藏定时器（用户滑动到预览框）
      if (this.hidePreviewTimer) {
        clearTimeout(this.hidePreviewTimer);
        this.hidePreviewTimer = null;
      }
    });

    previewBox.addEventListener('mouseleave', () => {
      this.hoverPreviewVisible = false;
      this.hideHoverPreview(false); // 延迟隐藏
    });
  }

  /**
   * 隐藏悬浮预览框
   * @param {boolean} immediate - 是否立即隐藏，默认false（延迟100ms）
   */
  hideHoverPreview(immediate = false) {
    // 清除之前的延迟隐藏定时器
    if (this.hidePreviewTimer) {
      clearTimeout(this.hidePreviewTimer);
      this.hidePreviewTimer = null;
    }

    const previewBox = document.getElementById('hover-preview-box');
    if (!previewBox) return;

    if (immediate) {
      // 立即隐藏（切换到其他模板时）- 添加小延迟避免频闪
      previewBox.classList.remove('show');
      this.hidePreviewTimer = setTimeout(() => {
        if (previewBox.parentNode) {
          previewBox.parentNode.removeChild(previewBox);
        }
        this.hidePreviewTimer = null;
        this.currentPreviewTemplateId = null; // 清除当前预览ID
      }, 50); // 50ms小延迟，让动画平滑完成
    } else {
      // 延迟隐藏（鼠标离开时）- 回到200ms
      previewBox.classList.remove('show');
      this.hidePreviewTimer = setTimeout(() => {
        if (previewBox.parentNode) {
          previewBox.parentNode.removeChild(previewBox);
        }
        this.hidePreviewTimer = null;
        this.currentPreviewTemplateId = null; // 清除当前预览ID
      }, 200); // 回到200毫秒延迟
    }
  }

  /**
   * 定位悬浮预览框（显示在侧栏外部）
   */
  positionHoverPreview(previewBox, event) {
    const previewWidth = 400;
    const previewHeight = 500;
    const margin = 10;

    // 获取触发元素的位置（相对于视口）
    const triggerRect = event.target.getBoundingClientRect();

    // 获取视口尺寸
    let viewportWidth, viewportHeight;

    try {
      // 尝试获取父窗口的视口尺寸（如果在iframe中）
      if (window.parent !== window && window.parent.innerWidth) {
        viewportWidth = window.parent.innerWidth;
        viewportHeight = window.parent.innerHeight;
      } else {
        viewportWidth = window.innerWidth;
        viewportHeight = window.innerHeight;
      }
    } catch (e) {
      // 跨域限制，使用当前窗口尺寸
      viewportWidth = window.innerWidth;
      viewportHeight = window.innerHeight;
    }

    // 计算默认位置（在触发元素右侧）
    let left = triggerRect.right + margin;
    let top = triggerRect.top;

    // 如果在iframe中，需要调整位置坐标
    if (window.parent !== window) {
      try {
        // 获取iframe在父窗口中的位置
        const iframeRect = window.frameElement.getBoundingClientRect();
        left += iframeRect.left;
        top += iframeRect.top;
      } catch (e) {
        // 跨域限制，保持原位置
      }
    }

    // 检查右侧空间是否足够
    if (left + previewWidth > viewportWidth) {
      // 右侧空间不够，显示在左侧
      left = triggerRect.left - previewWidth - margin;

      // 如果在iframe中，调整坐标
      if (window.parent !== window) {
        try {
          const iframeRect = window.frameElement.getBoundingClientRect();
          left += iframeRect.left;
        } catch (e) { }
      }
    }

    // 检查下方空间是否足够
    if (top + previewHeight > viewportHeight) {
      top = viewportHeight - previewHeight - margin;
    }

    // 确保不超出视口边界
    left = Math.max(margin, Math.min(left, viewportWidth - previewWidth - margin));
    top = Math.max(margin, Math.min(top, viewportHeight - previewHeight - margin));

    // 设置位置（使用fixed定位相对于视口）
    previewBox.style.position = 'fixed';
    previewBox.style.left = left + 'px';
    previewBox.style.top = top + 'px';
    previewBox.style.zIndex = '10000'; // 高z-index确保在最前面
  }

  /**
   * 调整完整预览iframe尺寸
   */
  adjustFullPreviewIframeSize(iframe) {
    try {
      const iframeDoc = iframe.contentDocument || iframe.contentWindow.document;
      if (iframeDoc && iframeDoc.body) {
        const contentHeight = iframeDoc.body.scrollHeight;
        const contentWidth = iframeDoc.body.scrollWidth;

        // 设置iframe高度为内容高度，但不超过最大高度
        const maxHeight = 400;
        const finalHeight = Math.min(contentHeight + 32, maxHeight); // 32px为padding

        iframe.style.height = finalHeight + 'px';
        iframe.style.width = '100%';
      }
    } catch (error) {
      // 静默处理错误
    }
  }

  /**
   * 为容器启用交互支持（已禁用滚动）
   */
  enableScrollForContainer(container) {
    // 禁用所有滚动功能，保持静态显示
    container.style.overflow = 'hidden';
    return;
  }

  // ============ 模板管理相关方法 ============

  /**
   * 添加窗口大小变化监听器
   */
  addResizeListener() {
    let resizeTimeout = null;

    // 监听窗口大小变化
    window.addEventListener('resize', () => {
      // 防抖处理，避免频繁重渲染
      if (resizeTimeout) {
        clearTimeout(resizeTimeout);
      }

      resizeTimeout = setTimeout(() => {
        this.refreshTemplatePreview();
      }, 500); // 增加到500ms，确保窗口调整完成
    });

    // 监听侧边栏容器大小变化（如果支持 ResizeObserver）
    if (window.ResizeObserver) {
      const templatesList = document.getElementById('templatesList');
      if (templatesList) {
        const resizeObserver = new ResizeObserver((entries) => {
          for (let entry of entries) {
            const newWidth = entry.contentRect.width;

            // 只有宽度变化超过50px才重新计算，减少不必要的重渲染
            if (!this.lastContainerWidth || Math.abs(newWidth - this.lastContainerWidth) > 50) {
              this.lastContainerWidth = newWidth;

              // 防抖处理
              if (resizeTimeout) {
                clearTimeout(resizeTimeout);
              }
              resizeTimeout = setTimeout(() => {
                this.refreshTemplatePreview();
              }, 300);
            }
          }
        });

        resizeObserver.observe(templatesList);
      }
    }
  }

  /**
   * 刷新所有模板预览
   */
  refreshTemplatePreview() {
    // 获取所有已渲染的模板卡片
    const templateCards = document.querySelectorAll('.template-card');

    if (templateCards.length === 0) {
      return;
    }

    let refreshCount = 0;
    templateCards.forEach(card => {
      const templateId = card.getAttribute('data-template-id');
      const thumbnailContainer = document.getElementById(`thumbnail-${templateId}`);

      if (thumbnailContainer) {
        // 检查是否已经有iframe
        const existingIframe = thumbnailContainer.querySelector('iframe');
        if (existingIframe) {
          // 重新确保预览容器样式
          this.ensurePreviewContainerStyle(thumbnailContainer);
          refreshCount++;
        }
      }
    });
  }

  /**
   * 调整iframe尺寸 - 支持缩放适配
   */
  adjustIframeSize(iframe, container) {
    try {
      const iframeDoc = iframe.contentDocument || iframe.contentWindow.document;
      if (iframeDoc && iframeDoc.body) {
        // 等待内容完全加载
        setTimeout(() => {
          try {
            // 获取容器的实际尺寸（固定50px高度，宽度自适应）
            const containerWidth = container.offsetWidth;
            const containerHeight = 50;

            // 重置iframe和内容样式
            iframe.style.width = '100%';
            iframe.style.height = 'auto';
            iframe.style.transform = 'none';
            iframe.style.transformOrigin = 'top left';

            // 设置iframe内容的原始尺寸
            iframeDoc.documentElement.style.width = 'auto';
            iframeDoc.documentElement.style.height = 'auto';
            iframeDoc.body.style.width = 'auto';
            iframeDoc.body.style.height = 'auto';
            iframeDoc.body.style.margin = '0';
            iframeDoc.body.style.padding = '8px';
            iframeDoc.body.style.overflow = 'visible';

            // 再等待一个周期让布局重新计算
            setTimeout(() => {
              try {
                // 获取内容的自然尺寸
                const contentWidth = iframeDoc.body.scrollWidth;
                const contentHeight = iframeDoc.body.scrollHeight;

                // 计算缩放比例以适应固定高度50px
                const scaleRatio = containerHeight / contentHeight;

                // 设置iframe为原始内容尺寸
                iframe.style.width = contentWidth + 'px';
                iframe.style.height = contentHeight + 'px';

                // 应用缩放变换
                iframe.style.transform = `scale(${scaleRatio})`;
                iframe.style.transformOrigin = 'top left';

                // 保持容器固定高度，宽度自适应
                container.style.width = '100%';
                container.style.height = containerHeight + 'px';
                container.style.overflow = 'hidden';

                // 重新启用容器的交互功能
                this.enableScrollForContainer(container);

              } catch (innerError) {
                // 失败时使用默认样式
                this.applyDefaultIframeStyle(iframe, container);
              }
            }, 250); // 等待150ms让内容布局稳定

          } catch (innerError) {
            this.applyDefaultIframeStyle(iframe, container);
          }
        }, 200); // 初始等待100ms
      }
    } catch (error) {
      this.applyDefaultIframeStyle(iframe, container);
    }
  }

  /**
   * 应用默认iframe样式（降级方案）
   */
  applyDefaultIframeStyle(iframe, container) {
    iframe.style.width = '100%';
    iframe.style.height = '100%';
    iframe.style.transform = 'none';
    container.style.width = '100%';
    container.style.height = '50px';
    container.style.overflow = 'hidden';
  }

  /**
   * 检查后台服务是否就绪
   */
  async checkBackendReady() {
    try {
      // 尝试使用browser API（Firefox推荐）
      const runtime = window.browser?.runtime || chrome.runtime;
      
      // 尝试使用Promise包装的方式
      const response = await new Promise((resolve, reject) => {
        runtime.sendMessage({
          type: 'CHECK_READY'
        }, (response) => {
          if (runtime.lastError) {
            reject(new Error(runtime.lastError.message));
          } else {
            resolve(response);
          }
        });
      });
      
      return response && response.success && response.ready;
    } catch (error) {
      return false;
    }
  }



  /**
   * 加载模板列表
   */
  async loadTemplates() {
    // 先检查后台是否就绪
    const isReady = await this.checkBackendReady();
    
    if (!isReady) {
      setTimeout(() => {
        this.loadTemplates();
      }, 3000);
      return;
    }
    
    // 添加重试机制
    const maxRetries = 3;
    let retryCount = 0;
    
    while (retryCount < maxRetries) {
      try {
        const runtime = window.browser?.runtime || chrome.runtime;
        const response = await new Promise((resolve, reject) => {
          runtime.sendMessage({
            type: 'GET_TEMPLATES',
            data: { forceRefresh: false }
          }, (response) => {
            if (runtime.lastError) {
              reject(new Error(runtime.lastError.message));
            } else {
              resolve(response);
            }
          });
        });

        if (response && response.success) {
          this.displayTemplates(response.data);
          this.updateTemplatesStats(response);
          return; // 成功则退出
        } else if (response === undefined) {
          retryCount++;
          if (retryCount < maxRetries) {
            await new Promise(resolve => setTimeout(resolve, retryCount * 1000));
            continue;
          }
        } else {
          this.showTemplatesError(response ? response.error : '加载模板失败');
          return;
        }

      } catch (error) {
        retryCount++;
        if (retryCount < maxRetries) {
          await new Promise(resolve => setTimeout(resolve, retryCount * 1000));
          continue;
        }
      }
    }
    
    // 所有重试都失败了
    this.showTemplatesError('加载模板失败：后台服务未就绪，请稍后重试');
  }

  /**
   * 直接加载模板列表（跳过就绪检查）
   */
  async loadTemplatesDirect() {
    const maxRetries = 3;
    let retryCount = 0;
    
    while (retryCount < maxRetries) {
      try {
        const runtime = window.browser?.runtime || chrome.runtime;
        const response = await new Promise((resolve, reject) => {
          runtime.sendMessage({
            type: 'GET_TEMPLATES',
            data: { forceRefresh: false }
          }, (response) => {
            if (runtime.lastError) {
              reject(new Error(runtime.lastError.message));
            } else {
              resolve(response);
            }
          });
        });

        if (response && response.success) {
          this.displayTemplates(response.data);
          this.updateTemplatesStats(response);
          return; // 成功则退出
        } else if (response === undefined) {
          retryCount++;
          if (retryCount < maxRetries) {
            await new Promise(resolve => setTimeout(resolve, retryCount * 1000));
            continue;
          }
        } else {
          this.showTemplatesError(response ? response.error : '加载模板失败');
          return;
        }

      } catch (error) {
        retryCount++;
        if (retryCount < maxRetries) {
          await new Promise(resolve => setTimeout(resolve, retryCount * 1000));
          continue;
        }
      }
    }
    
    // 所有重试都失败了
    this.showTemplatesError('加载模板失败：后台服务未就绪，请稍后重试');
  }

  /**
   * 处理搜索输入
   */
  handleSearchInput(query) {
    this.searchQuery = query.trim();
    this.updateSearchClearButton();
    this.applyFiltersAndSearch();
  }

  /**
   * 清除搜索
   */
  clearSearch() {
    const searchInput = document.getElementById('templateSearchInput');
    if (searchInput) {
      searchInput.value = '';
    }
    this.searchQuery = '';
    this.updateSearchClearButton();
    this.applyFiltersAndSearch();
  }

  /**
   * 更新搜索清除按钮显示状态
   */
  updateSearchClearButton() {
    const searchClearBtn = document.getElementById('searchClearBtn');
    if (searchClearBtn) {
      if (this.searchQuery) {
        searchClearBtn.classList.add('show');
      } else {
        searchClearBtn.classList.remove('show');
      }
    }
  }

  /**
   * 处理筛选变化
   */
  handleFilterChange(filter) {
    // 更新筛选标签状态
    document.querySelectorAll('.filter-tab').forEach(tab => {
      tab.classList.remove('active');
    });
    document.querySelector(`[data-filter="${filter}"]`).classList.add('active');
    
    this.currentFilter = filter;
    this.applyFiltersAndSearch();
  }

  /**
   * 应用筛选和搜索
   */
  applyFiltersAndSearch() {
    let filtered = [...this.allTemplates];

    // 应用VIP筛选
    if (this.currentFilter === 'free') {
      filtered = filtered.filter(template => template.vip !== 'vip');
    } else if (this.currentFilter === 'vip') {
      filtered = filtered.filter(template => template.vip === 'vip');
    }

    // 应用搜索筛选
    if (this.searchQuery) {
      const query = this.searchQuery.toLowerCase();
      filtered = filtered.filter(template => {
        return template.name.toLowerCase().includes(query) ||
               (template.description && template.description.toLowerCase().includes(query)) ||
               (template.category && template.category.toLowerCase().includes(query));
      });
    }

    this.filteredTemplates = filtered;
    this.displayFilteredTemplates();
  }

  /**
   * 显示筛选后的模板
   */
  displayFilteredTemplates() {
    const templatesList = document.getElementById('templatesList');
    if (!templatesList) return;

    // 显示搜索结果信息
    this.showSearchResultsInfo();

    if (this.filteredTemplates.length === 0) {
      this.showEmptyState();
      return;
    }

    // 渲染筛选后的模板
    this.renderTemplates(this.filteredTemplates);
  }

  /**
   * 显示搜索结果信息
   */
  showSearchResultsInfo() {
    let infoContainer = document.querySelector('.search-results-info');
    if (!infoContainer) {
      infoContainer = document.createElement('div');
      infoContainer.className = 'search-results-info';
      const templatesList = document.getElementById('templatesList');
      templatesList.parentNode.insertBefore(infoContainer, templatesList);
    }

    const totalCount = this.allTemplates.length;
    const filteredCount = this.filteredTemplates.length;
    const hasSearch = this.searchQuery.length > 0;
    const hasFilter = this.currentFilter !== 'all';

    let infoText = '';
    if (hasSearch && hasFilter) {
      infoText = `搜索"${this.searchQuery}" + ${this.getFilterText()}，找到 ${filteredCount} 个模板`;
    } else if (hasSearch) {
      infoText = `搜索"${this.searchQuery}"，找到 ${filteredCount} 个模板`;
    } else if (hasFilter) {
      infoText = `${this.getFilterText()}，共 ${filteredCount} 个模板`;
    } else {
      infoText = `共 ${totalCount} 个模板`;
    }

    infoContainer.textContent = infoText;
    infoContainer.className = `search-results-info ${filteredCount > 0 ? 'highlight' : ''}`;
  }

  /**
   * 获取筛选文本
   */
  getFilterText() {
    switch (this.currentFilter) {
      case 'free': return '通用模板';
      case 'vip': return 'VIP模板';
      default: return '全部模板';
    }
  }

  /**
   * 安全地显示空状态
   */
  showEmptyState() {
    const templatesList = document.getElementById('templatesList');
    const hasSearch = this.searchQuery.length > 0;
    const hasFilter = this.currentFilter !== 'all';

    // 清空现有内容
    templatesList.innerHTML = '';

    const emptyStateDiv = this.safeCreateElement('div', { className: 'empty-state' });
    const iconDiv = this.safeCreateElement('div', { className: 'empty-state-icon' });
    const titleDiv = this.safeCreateElement('div', { className: 'empty-state-title' });
    const descDiv = this.safeCreateElement('div', { className: 'empty-state-desc' });

    if (hasSearch && hasFilter) {
      iconDiv.textContent = '🔍';
      titleDiv.textContent = '未找到匹配的模板';
      descDiv.textContent = `没有找到同时满足"${this.searchQuery}"和${this.getFilterText()}条件的模板`;
      
      const actionDiv = this.safeCreateElement('div', { 
        className: 'empty-state-action', 
        textContent: '清除筛选条件' 
      });
      actionDiv.id = 'clearSearchAndFilterBtn';
      emptyStateDiv.appendChild(actionDiv);
    } else if (hasSearch) {
      iconDiv.textContent = '🔍';
      titleDiv.textContent = '未找到匹配的模板';
      descDiv.textContent = `没有找到包含"${this.searchQuery}"的模板，请尝试其他关键词`;
      
      const actionDiv = this.safeCreateElement('div', { 
        className: 'empty-state-action', 
        textContent: '清除搜索' 
      });
      actionDiv.id = 'clearSearchBtn';
      emptyStateDiv.appendChild(actionDiv);
    } else if (hasFilter) {
      iconDiv.textContent = '🎨';
      titleDiv.textContent = `暂无${this.getFilterText()}`;
      descDiv.textContent = `当前没有${this.getFilterText()}，请尝试其他筛选条件`;
      
      const actionDiv = this.safeCreateElement('div', { 
        className: 'empty-state-action', 
        textContent: '查看全部' 
      });
      actionDiv.id = 'clearFilterBtn';
      emptyStateDiv.appendChild(actionDiv);
    } else {
      iconDiv.textContent = '🎨';
      titleDiv.textContent = '暂无可用模板';
      descDiv.textContent = '当前没有可用的模板，请稍后再试';
    }

    emptyStateDiv.appendChild(iconDiv);
    emptyStateDiv.appendChild(titleDiv);
    emptyStateDiv.appendChild(descDiv);
    
    templatesList.appendChild(emptyStateDiv);
  }

  /**
   * 清除搜索和筛选
   */
  clearSearchAndFilter() {
    this.clearSearch();
    this.handleFilterChange('all');
  }



  /**
   * 清除筛选
   */
  clearFilter() {
    this.handleFilterChange('all');
  }

  /**
   * 显示模板列表
   */
  displayTemplates(templates) {
    // 检查模板数据
    if (!templates || !Array.isArray(templates)) {
      return;
    }

    // 存储模板数据用于搜索和筛选
    this.allTemplates = templates;

    // 渲染模板列表
    this.renderTemplates(templates);
  }

  /**
   * 应用搜索和筛选
   */
  applySearchAndFilter() {
    // 获取搜索关键词和筛选类型
    const query = this.searchQuery.toLowerCase().trim();
    const filter = this.currentFilter;

    // 筛选模板
    let filtered = [...this.allTemplates];

    // 应用筛选类型
    if (filter === 'free') {
      filtered = filtered.filter(template => !template.isVip);
    } else if (filter === 'vip') {
      filtered = filtered.filter(template => template.isVip);
    }

    // 应用搜索关键词
    if (query) {
      filtered = filtered.filter(template => 
        template.name.toLowerCase().includes(query) ||
        (template.description && template.description.toLowerCase().includes(query))
      );
    }

    // 更新筛选结果
    this.filteredTemplates = filtered;

    // 渲染模板列表
    this.renderTemplates(this.filteredTemplates);
  }

  /**
   * 渲染模板列表
   */
  renderTemplates(templates) {
    // 检查模板数据
    if (!templates || !Array.isArray(templates)) {
      return;
    }

    const templatesList = document.getElementById('templatesList');
    if (!templatesList) {
      // 静默处理错误
      return;
    }

    if (!templates || templates.length === 0) {
      return;
    }

    // 按分类组织模板
    const groupedTemplates = templates.reduce((groups, template) => {
      const category = template.category || '通用';
      if (!groups[category]) {
        groups[category] = [];
      }
      groups[category].push(template);
      return groups;
    }, {});

    // 生成HTML
    let html = '';
    Object.entries(groupedTemplates).forEach(([category, categoryTemplates]) => {
      html += `
        <div class="template-category">
          <h4 class="category-title">${category} (${categoryTemplates.length})</h4>
          <div class="templates-grid">
      `;

      categoryTemplates.forEach(template => {
        const isVip = template.vip === 'vip';
        const vipClass = isVip ? 'vip-template' : '';
        const vipBadge = isVip ? '<div class="vip-badge">VIP</div>' : '';

        // 确保有html和url字段
        const previewUrl = template.html || template.url; // 预览图是html字段
        const actualUrl = template.url; // 实际模板是url字段

        html += `
          <div class="template-card ${vipClass}" data-template-id="${template.id}" data-template-url="${actualUrl}" data-preview-url="${previewUrl}" data-is-vip="${isVip}">
            ${vipBadge}
            <div class="template-preview-container">
              <div class="template-thumbnail" id="thumbnail-${template.id}">
                <div class="preview-loading">🔄</div>
              </div>
            </div>
            <div class="template-info">
              <div class="template-name">${template.name}</div>
            </div>
          </div>
        `;
      });

      html += `
          </div>
        </div>
      `;
    });

    // 安全地设置模板列表内容
    this.safeSetContent(templatesList, html, true);

    // 绑定事件
    this.bindTemplateEvents();

    // 为模板列表容器添加滑动锁定功能
    this.addScrollLockToTemplatesList();

    // 异步加载模板预览
    this.loadTemplatePreview(templates);
  }

  /**
   * 为模板列表容器添加滑动锁定功能
   */
  addScrollLockToTemplatesList() {
    const templatesList = document.getElementById('templatesList');
    if (!templatesList) {
      return;
    }

    let scrollTimeout = null;

    const lockButtons = () => {
      this.lockButtonsDuringScroll(true);

      // 清除之前的定时器
      if (scrollTimeout) {
        clearTimeout(scrollTimeout);
      }

      // 设置新的定时器，滑动停止后解锁按钮
      scrollTimeout = setTimeout(() => {
        this.lockButtonsDuringScroll(false);
      }, 150); // 150ms后解锁按钮
    };

    // 监听鼠标滚轮滑动
    templatesList.addEventListener('wheel', (e) => {
      // 检查是否需要滑动
      const canScrollDown = templatesList.scrollTop < (templatesList.scrollHeight - templatesList.clientHeight);
      const canScrollUp = templatesList.scrollTop > 0;

      if ((e.deltaY > 0 && canScrollDown) || (e.deltaY < 0 && canScrollUp)) {
        lockButtons(); // 滑动时锁定按钮
      }
    }, { passive: true });

    // 监听触摸滑动（移动设备）
    let startY = 0;
    let scrollTop = 0;
    let isScrolling = false;

    templatesList.addEventListener('touchstart', (e) => {
      startY = e.touches[0].pageY;
      scrollTop = templatesList.scrollTop;
      isScrolling = false;
    }, { passive: true });

    templatesList.addEventListener('touchmove', (e) => {
      const y = e.touches[0].pageY;
      const deltaY = startY - y;

      // 检查是否真的在滑动
      if (Math.abs(deltaY) > 5) {
        isScrolling = true;
        lockButtons(); // 滑动时锁定按钮
      }
    }, { passive: true });

    templatesList.addEventListener('touchend', () => {
      if (isScrolling) {
        // 触摸结束，延迟解锁按钮
        if (scrollTimeout) {
          clearTimeout(scrollTimeout);
        }
        scrollTimeout = setTimeout(() => {
          this.lockButtonsDuringScroll(false);
        }, 200);
      }
    }, { passive: true });
  }

  /**
   * 绑定模板事件
   */
  bindTemplateEvents() {
    // 模板卡片点击事件
    document.querySelectorAll('.template-card').forEach(card => {
      card.addEventListener('click', (e) => {
        const templateId = card.getAttribute('data-template-id');
        this.selectTemplateById(templateId);
      });

      // 双击事件 - 显示左侧预览面板
      card.addEventListener('dblclick', (e) => {
        const templateId = card.getAttribute('data-template-id');
        const previewUrl = card.getAttribute('data-preview-url');
        const templateName = card.querySelector('.template-name').textContent;
        const templateUrl = card.getAttribute('data-template-url');
        const isVip = card.getAttribute('data-is-vip') === 'true';
        
        this.showPreviewPanel({
          id: templateId,
          name: templateName,
          url: templateUrl,
          html: previewUrl,
          isVip: isVip
        });
      });
    });
  }

  /**
   * 根据ID选择模板
   */
  async selectTemplateById(templateId) {
    const selectedCard = document.querySelector(`[data-template-id="${templateId}"]`);
    if (!selectedCard) {
      return;
    }

    // 获取当前是否已选中
    const isCurrentlySelected = selectedCard.classList.contains('selected');

    // 清除所有其他模板的选中状态
    document.querySelectorAll('.template-card').forEach(card => {
      card.classList.remove('selected');
    });

    // 如果点击的是同一个模板，则切换选中/取消状态
    if (isCurrentlySelected) {
      // 取消选中
      this.selectedTemplate = null;
      document.getElementById('generateBtn').disabled = true;
      this.showNotification('已取消模板选择', 'info');
      // 取消选择时也关闭页面左侧预览面板
      await this.requestClosePagePreview();
      return;
    }

    // 选中新模板
    const isVipTemplate = selectedCard.getAttribute('data-is-vip') === 'true';

    // 不在选择时校验VIP，推迟到点击“开始生成”时校验

    // 设置选中状态
    selectedCard.classList.add('selected');

    // 获取模板数据
    const templateUrl = selectedCard.getAttribute('data-template-url'); // 实际模板URL
    const previewUrl = selectedCard.getAttribute('data-preview-url') || templateUrl; // 预览图URL
    const templateName = selectedCard.querySelector('.template-name').textContent;

    // 设置选中的模板
    this.selectedTemplate = {
      id: templateId,
      name: templateName,
      url: templateUrl, // 实际模板URL，用于生成内容
      html: previewUrl, // 预览图URL，用于展示
      isVip: isVipTemplate
    };

    // 启用生成按钮
    document.getElementById('generateBtn').disabled = false;

    const vipText = isVipTemplate ? ' (VIP)' : '';
    this.showNotification(`已选择模板: ${templateName}${vipText}`, 'success');

    // 自动显示页面预览面板
    this.showPagePreviewPanel(this.selectedTemplate);
  }

  /**
   * 请求关闭页面左侧预览面板
   */
  async requestClosePagePreview() {
    try {
      
      let tab = null;
      if (this._previewTabId) {
        try { tab = await chrome.tabs.get(this._previewTabId); } catch (_) { tab = null; }
      }
      if (!tab) {
        tab = await this.getCurrentTab();
      }
      
      if (!tab) {
        return;
      }
      if (tab) {
        await this.sendTabMessage(tab.id, { type: 'CLOSE_PAGE_PREVIEW' });
      }
    } catch (e) {
      // 忽略关闭失败
    }
  }

  /**
   * 预览模板
   */
  async previewTemplate(templateUrl) {
    try {
      
      this.showLoading(true, '正在加载模板内容...');

      const response = await this.sendRuntimeMessage({
        type: 'GET_TEMPLATE_CONTENT',
        data: { templateUrl: templateUrl }
      });

      if (response && response.success) {
        // 切换到编辑标签并显示预览
        this.switchTab('editor');
        this.showOptimizationResult(response.data.content);
        this.showNotification(`模板“${response.data.name}”预览加载成功`, 'success');
      } else {
        this.showNotification(`模板预览失败: ${response ? response.error : '未知错误'}`, 'error');
      }

    } catch (error) {
      this.showNotification(`模板预览失败: ${error.message}`, 'error');
    } finally {
      this.showLoading(false);
    }
  }

  /**
   * 使用模板
   */
  async useTemplate(templateUrl) {
    try {
      
      this.showLoading(true, '正在应用模板...');

      const response = await this.sendRuntimeMessage({
        type: 'GET_TEMPLATE_CONTENT',
        data: { templateUrl: templateUrl }
      });

      if (response && response.success) {
        // 切换到编辑标签
        this.switchTab('editor');

        // 直接应用到编辑器
        const tab = await this.getCurrentTab();
        
        if (!tab) {
          this.showNotification('无法获取当前标签页', 'error');
          return;
        }
        const applyResponse = await chrome.tabs.sendMessage(tab.id, {
          type: 'REPLACE_CONTENT',
          data: { content: response.data.content }
        });

        if (applyResponse && applyResponse.success) {
          this.showNotification(`模板“${response.data.name}”应用成功`, 'success');
          // 刷新内容显示
          setTimeout(() => this.refreshContent(), 500);
        } else {
          this.showNotification('模板应用失败', 'error');
        }
      } else {
        this.showNotification(`模板加载失败: ${response ? response.error : '未知错误'}`, 'error');
      }

    } catch (error) {
      this.showNotification(`模板使用失败: ${error.message}`, 'error');
    } finally {
      this.showLoading(false);
    }
  }

  /**
   * 刷新模板
   */
  async refreshTemplates() {
    try {
      this.showLoading(true, '正在刷新模板数据...');

      const response = await this.sendRuntimeMessage({
        type: 'REFRESH_TEMPLATES_CACHE'
      });

      if (response && response.success) {
        // 重新加载模板列表
        await this.loadTemplates();
        this.showNotification('模板数据刷新成功', 'success');
      } else {
        this.showNotification(`模板刷新失败: ${response ? response.error : '未知错误'}`, 'error');
      }

    } catch (error) {
      this.showNotification(`模板刷新失败: ${error.message}`, 'error');
    } finally {
      this.showLoading(false);
    }
  }

  /**
   * 清除模板缓存
   */
  async clearTemplatesCache() {
    if (!confirm('确定要清除模板缓存吗？这将强制从云端重新加载模板数据。')) {
      return;
    }

    try {
      this.showLoading(true, '正在清除缓存...');

      const response = await this.sendRuntimeMessage({
        type: 'CLEAR_TEMPLATES_CACHE'
      });

      if (response && response.success) {
        // 重新加载模板列表
        await this.loadTemplates();
        this.showNotification('模板缓存已清除', 'success');
      } else {
        this.showNotification('清除缓存失败', 'error');
      }

    } catch (error) {
      this.showNotification(`清除缓存失败: ${error.message}`, 'error');
    } finally {
      this.showLoading(false);
    }
  }

  /**
   * 更新模板统计信息
   */
  updateTemplatesStats(response) {
    // 由于我们已经移除了模板统计信息显示，这个方法现在只用于记录
  }

  /**
   * 显示模板错误
   */
  showTemplatesError(errorMessage) {
    const templatesList = document.getElementById('templatesList');
    if (!templatesList) {
      return;
    }

    // 安全地显示错误状态
    templatesList.innerHTML = '';
    
    const errorDiv = this.safeCreateElement('div', { className: 'empty-state error' });
    const iconSpan = this.safeCreateElement('span', { className: 'empty-icon', textContent: '⚠️' });
    const messageP = this.safeCreateElement('p', { textContent: errorMessage });
    const retryBtn = this.safeCreateElement('button', { 
      className: 'btn btn-secondary', 
      textContent: '重试' 
    });
    retryBtn.id = 'retryTemplatesBtn';
    
    errorDiv.appendChild(iconSpan);
    errorDiv.appendChild(messageP);
    errorDiv.appendChild(retryBtn);
    
    templatesList.appendChild(errorDiv);

    // 绑定重试按钮事件
    if (retryBtn) {
      retryBtn.addEventListener('click', () => {
        this.loadTemplates();
      });
    }
  }

  /**
   * 修改showLoading方法支持自定义消息
   */
  showLoading(show, message = '正在处理中...') {
    const overlay = document.getElementById('loadingOverlay');
    if (!overlay) {
      return;
    }

    if (show) {
      // 显示加载状态，但隐藏进度组件（用于非流式加载）
      const loadingText = overlay.querySelector('#loadingText');
      const progressInfo = overlay.querySelector('.progress-info');
      const loadingProgress = overlay.querySelector('.loading-progress');
      
      if (loadingText) loadingText.textContent = message;
      if (progressInfo) progressInfo.style.display = 'none';
      if (loadingProgress) loadingProgress.style.display = 'none';
      
      overlay.style.display = 'flex';
    } else {
      overlay.style.display = 'none';
    }

    // 禁用相关按钮
    const generateBtn = document.getElementById('generateBtn');

    if (generateBtn) {
      generateBtn.disabled = show;
    }
  }

  // ============ VIP密钥管理方法 ============

  /**
   * 验证VIP密钥输入
   */
  validateVipKeyInput() {
    const vipKeyInput = document.getElementById('vipKeyInput');

    if (!vipKeyInput) {
      return;
    }

    const vipKey = vipKeyInput.value.trim();

    // VIP密钥可以为空（非必填）
    if (!vipKey) {
      vipKeyInput.style.borderColor = '#ddd'; // 默认颜色
    } else if (this.validateVipKey(vipKey)) {
      vipKeyInput.style.borderColor = '#28a745'; // 绿色（有效）
    } else {
      vipKeyInput.style.borderColor = '#dc3545'; // 红色（无效）
    }
  }

  /**
   * 验证VIP密钥格式
   */
  validateVipKey(vipKey) {
    if (vipKey === 'backend-synchronized') return true;
    return vipKey && typeof vipKey === 'string' && vipKey.length > 5;
  }

  /**
   * 切换VIP密钥显示/隐藏
   */
  toggleVipKeyVisibility() {
    const vipKeyInput = document.getElementById('vipKeyInput');
    const toggleBtn = document.getElementById('toggleVipKeyBtn');

    if (!vipKeyInput || !toggleBtn) {
      return;
    }

    // 直接切换输入框类型，同时切换按钮文本
    if (vipKeyInput.type === 'password') {
      vipKeyInput.type = 'text';
      toggleBtn.textContent = '🙈';
    } else {
      vipKeyInput.type = 'password';
      toggleBtn.textContent = '👁️';
    }
  }

  /**
   * 保存VIP密钥
   */
  async saveVipKey() {
    try {
      const vipKeyInput = document.getElementById('vipKeyInput');
      const saveVipKeyBtn = document.getElementById('saveVipKeyBtn');

      if (!vipKeyInput) {
        this.showNotification('VIP密钥输入框未找到', 'error');
        return;
      }

      const vipKey = vipKeyInput.value.trim();

      // VIP密钥可以为空（清除功能）
      if (!vipKey) {
        // 清除VIP密钥
        
        const clearResponse = await chrome.runtime.sendMessage({
          type: 'SAVE_API_CONFIG',
          data: { vipKey: '' }
        });
        

        if (clearResponse && clearResponse.success) {
          this.showNotification('VIP密钥已清除', 'success');

          // 隐藏VIP状态信息
          const vipStatus = document.getElementById('vipStatus');
          const vipInfo = document.getElementById('vipInfo');
          if (vipStatus) vipStatus.style.display = 'none';
          if (vipInfo) vipInfo.style.display = 'none';

          // 停止监控
          this.stopVipKeyMonitoring();
        } else {
          this.showNotification('清除失败: ' + (clearResponse?.error || '未知错误'), 'error');
        }
        return;
      }

      // 验证VIP密钥格式
      if (!this.validateVipKey(vipKey)) {
        this.showNotification('VIP密钥格式不正确（应以sk-开头且长度大于20）', 'error');
        return;
      }

      // 显示保存中状态
      if (saveVipKeyBtn) {
        saveVipKeyBtn.disabled = true;
        saveVipKeyBtn.textContent = '保存中...';
      }

      try {
        
        const response = await chrome.runtime.sendMessage({
          type: 'SAVE_VIP_KEY',
          data: { vipKey: vipKey }
        });
        

        if (response && response.success) {
          this.showNotification('VIP密钥保存成功', 'success');

          // 保存成功后主动重新获取VIP状态信息，确保缓存实时更新
          setTimeout(async () => {
            await this.checkVipKeyStatus();
          }, 500);
        } else {
          this.showNotification('保存失败: ' + (response?.error || '未知错误'), 'error');
        }
      } finally {
        // 恢复按钮状态
        if (saveVipKeyBtn) {
          saveVipKeyBtn.disabled = false;
          saveVipKeyBtn.textContent = '保存';
        }
      }
    } catch (error) {
      
      this.showNotification('保存失败: ' + error.message, 'error');

      // 恢复按钮状态
      const saveVipKeyBtn = document.getElementById('saveVipKeyBtn');
      if (saveVipKeyBtn) {
        saveVipKeyBtn.disabled = false;
        saveVipKeyBtn.textContent = '保存';
      }
    }
  }

  /**
   * 检查VIP密钥状态
   */
  async checkVipKeyStatus() {
    try {
      const vipStatus = document.getElementById('vipStatus');
      const vipInfo = document.getElementById('vipInfo');

      if (!vipStatus || !vipInfo) {
        return;
      }

      // 显示检查状态
      vipStatus.style.display = 'block';
      vipStatus.className = 'vip-status';
      vipStatus.querySelector('.status-text').textContent = 'VIP密钥检查中...';

      // 发送检查请求
      const response = await this.sendRuntimeMessage({
        type: 'CHECK_VIP_KEY_STATUS'
      });

      if (response && response.success) {
        // 检查成功
        vipStatus.className = 'vip-status success';
        vipStatus.querySelector('.status-text').textContent = 'VIP密钥有效';

        // 显示VIP信息
        this.displayVipInfo(response.data);
        vipInfo.style.display = 'block';

        // 保存VIP状态到本地缓存，用于快速权限检查
        this.cacheVipStatus({
          isValid: true,
          remainingDays: response.data.remainingDays,
          timestamp: Date.now()
        });

      } else {
        // 检查失败
        vipStatus.className = 'vip-status error';
        vipStatus.querySelector('.status-text').textContent = 'VIP密钥无效: ' + (response?.error || '未知错误');
        vipInfo.style.display = 'none';

        // 清除本地VIP状态缓存
        this.clearVipStatusCache();
      }
    } catch (error) {
      const vipStatus = document.getElementById('vipStatus');
      if (vipStatus) {
        vipStatus.className = 'vip-status error';
        vipStatus.querySelector('.status-text').textContent = 'VIP密钥检查失败: ' + error.message;
      }

      // 清除本地VIP状态缓存
      this.clearVipStatusCache();
    }
  }

  /**
   * 显示VIP信息
   */
  displayVipInfo(vipData) {
    const vipRemainingDays = document.getElementById('vipRemainingDays');

    if (!vipRemainingDays) {
      return;
    }

    // 只显示剩余天数
    vipRemainingDays.textContent = `${vipData.remainingDays} 天`;

    // 根据剩余天数设置样式
    const remainingDays = vipData.remainingDays;
    vipRemainingDays.className = 'info-value';

    if (remainingDays <= 0) {
      vipRemainingDays.classList.add('expired');
    } else if (remainingDays <= 7) {
      vipRemainingDays.classList.add('warning');
    } else {
      vipRemainingDays.classList.add('normal');
    }
  }











  /**
   * 检查VIP访问权限（仅本地检查，不调用云函数）
   */
  async checkVipAccess() {
    try {
      // 1. 快速检查 localStorage 缓存
      const cachedVipStatus = this.getVipStatusCache();
      if (cachedVipStatus && cachedVipStatus.isValid && cachedVipStatus.remainingDays > 0) {

        return true;
      }
      

      // 2. 如果缓存无效，向后台发送强制检查请求
      // 这个请求会清除后台缓存并进行一次实时的云端验证
      const response = await this.sendRuntimeMessage({ type: 'FORCE_CHECK_VIP_STATUS' });



      // 3. 根据实时验证结果判断权限
      if (response && response.success && response.data && response.data.isValid && response.data.remainingDays > 0) {
        // 验证成功后，更新本地缓存和UI，为下一次检查做准备
        this.cacheVipStatus({
          isValid: true,
          remainingDays: response.data.remainingDays,
          timestamp: Date.now()
        });
        // 可以在这里静默更新一下UI，但不是必须
        const vipStatus = document.getElementById('vipStatus');
        if (vipStatus.style.display !== 'block' || !vipStatus.classList.contains('success')) {
            this.checkVipKeyStatus(); // 触发一次完整的UI更新
        }
        return true;
      }
      
      // 4. 如果所有检查都失败，则无权限

      return false;

    } catch (error) {

      return false;
    }
  }











  /**
   * 缓存VIP状态到本地存储
   */
  cacheVipStatus(vipStatusData) {
    try {
      const cacheData = {
        ...vipStatusData,
        cacheTime: Date.now()
      };
      localStorage.setItem('vipStatusCache', JSON.stringify(cacheData));
    } catch (error) {
      // 静默处理错误
    }
  }

  /**
   * 从本地存储获取VIP状态缓存
   */
  getVipStatusCache() {
    try {
      const cached = localStorage.getItem('vipStatusCache');
      if (!cached) return null;

      const cacheData = JSON.parse(cached);
      const now = Date.now();
      const tenMinutes = 10 * 60 * 1000; // 10分钟

      // 缓存超过10分钟则失效
      if (now - cacheData.cacheTime > tenMinutes) {
        this.clearVipStatusCache();
        return null;
      }

      // 剩余天数小于1天不使用缓存
      if (cacheData.remainingDays < 1) {
        return null;
      }

      return cacheData;
    } catch (error) {
      return null;
    }
  }

  /**
   * 清除本地VIP状态缓存
   */
  clearVipStatusCache() {
    try {
      localStorage.removeItem('vipStatusCache');
    } catch (error) {
      // 静默处理错误
    }
  }

  // ============ VIP密钥监控方法 ============

  /**
   * 启动VIP密钥监控
   */
  startVipKeyMonitoring() {
    // 避免重复开启
    if (this.vipKeyMonitorInterval) {
      clearInterval(this.vipKeyMonitorInterval);
      this.vipKeyMonitorInterval = null;
    }

    if (this.vipExpiryUpdateInterval) {
      clearInterval(this.vipExpiryUpdateInterval);
      this.vipExpiryUpdateInterval = null;
    }

    // 仅设置每分钟基于现有数据的到期显示刷新（不请求云端）
    this.vipExpiryUpdateInterval = setInterval(() => {
      this.updateVipExpiryDisplay();
    }, 60 * 1000); // 1分钟
  }

  /**
   * 停止VIP密钥监控
   */
  stopVipKeyMonitoring() {
    if (this.vipKeyMonitorInterval) {
      clearInterval(this.vipKeyMonitorInterval);
      this.vipKeyMonitorInterval = null;
    }

    if (this.vipExpiryUpdateInterval) {
      clearInterval(this.vipExpiryUpdateInterval);
      this.vipExpiryUpdateInterval = null;
    }
  }

  /**
   * 检查VIP密钥状态（监控用）
   */
  async checkVipKeyStatusForMonitoring() {
    // 已取消定时云端校验，保留方法以兼容可能的调用，但不执行任何远端请求
    return;
  }

  /**
   * 更新VIP状态显示
   */
  updateVipStatusDisplay(vipData) {
    const vipStatus = document.getElementById('vipStatus');
    const vipInfo = document.getElementById('vipInfo');

    if (!vipStatus || !vipInfo) {
      return;
    }

    if (vipData.isValid) {
      vipStatus.className = 'vip-status success';
      vipStatus.querySelector('.status-text').textContent = 'VIP密钥有效';
      vipInfo.style.display = 'block';
      this.displayVipInfo(vipData);
    } else {
      vipStatus.className = 'vip-status error';
      vipStatus.querySelector('.status-text').textContent = 'VIP密钥已过期';
      vipInfo.style.display = 'none';
    }
  }

  /**
   * 更新VIP到期时间显示
   */
  updateVipExpiryDisplay() {
    const vipRemainingDays = document.getElementById('vipRemainingDays');
    if (!vipRemainingDays || !vipRemainingDays.textContent.includes('天')) {
      return;
    }

    // 从显示文本中提取剩余天数
    const remainingText = vipRemainingDays.textContent;
    const daysMatch = remainingText.match(/(\d+)\s*天/);

    if (daysMatch) {
      const remainingDays = parseInt(daysMatch[1]);

      // 更新样式
      vipRemainingDays.className = 'info-value';

      if (remainingDays <= 0) {
        vipRemainingDays.classList.add('expired');
        vipRemainingDays.textContent = '已过期';
      } else if (remainingDays <= 7) {
        vipRemainingDays.classList.add('warning');
        vipRemainingDays.textContent = `${remainingDays} 天 (即将过期)`;
      } else {
        vipRemainingDays.classList.add('normal');
        vipRemainingDays.textContent = `${remainingDays} 天`;
      }
    }
  }


  /**
   * 清除预览缓存
   */
  clearPreviewCache() {
    this.previewCache.clear();
  }

  /**
   * 显示页面预览面板
   */
  async showPagePreviewPanel(templateData) {
    try {
      
      // 选择或预览模板时不再校验VIP权限，允许预览；仅在点击"开始生成"时校验

      // 获取当前活动标签页
      const tab = await this.getCurrentTab();
      // 记录用于后续消息下发的 tabId，避免后续因焦点切换导致发错目标
      this._previewTabId = tab.id;
      
      if (!tab) {
        this.showNotification('无法获取当前标签页', 'error');
        return;
      }

      // 发送消息到content script显示预览
      const response = await this.sendTabMessage(this._previewTabId, {
        type: 'SHOW_PAGE_PREVIEW',
        data: { templateData: templateData }
      });

      if (response && response.success) {
        // 获取模板内容并显示
        await this.loadAndDisplayPagePreviewContent(templateData);
      } else {
        this.showNotification('预览面板显示失败', 'error');
      }

    } catch (error) {
      this.showNotification(`预览失败: ${error.message}`, 'error');
    }
  }

  /**
   * 加载并显示页面预览内容
   */
  async loadAndDisplayPagePreviewContent(templateData) {
    try {
      
      // 检查缓存
      const cacheKey = templateData.id;
      if (this.previewCache.has(cacheKey)) {
        this.showPreviewContent(this.previewCache.get(cacheKey));
        return;
      }

      // 如果是Base64图片，避免消息大payload：改为后台写storage，页面按key读取
      if (templateData && typeof templateData.html === 'string' && templateData.html.startsWith('data:image/')) {
        const res = await this.sendRuntimeMessage({
          type: 'PREPARE_PREVIEW_IMAGE',
          data: { templateId: templateData.id, templateUrl: templateData.url }
        });
        if (res && res.success && res.key) {
          const descriptor = { mode: 'storage_key', key: res.key, templateId: templateData.id, name: templateData.name };
          this.showPreviewContent(descriptor);
        } else {
          this.showPagePreviewError('预览图准备失败');
        }
        return;
      }

      // 否则从远端获取模板内容
      const response = await this.sendRuntimeMessage({
        type: 'GET_TEMPLATE_CONTENT',
        data: { templateUrl: templateData.html || templateData.url }
      });

      if (response && response.success && response.data) {
        const content = response.data.content;
        if (!content || typeof content !== 'string' || content.trim().length === 0) {
          this.showPagePreviewError('模板内容为空');
          return;
        }

        // 缓存内容
        this.previewCache.set(cacheKey, content);
        this.limitPreviewCache();

        // 显示内容
        this.showPreviewContent(content);

      } else {
        let errorMsg = '内容获取失败';
        if (response) {
          if (!response.success) {
            errorMsg = response.error || '服务器返回失败';
          } else if (!response.data) {
            errorMsg = '响应数据为空';
          }
        } else {
          errorMsg = '无响应数据';
        }
        this.showPagePreviewError(errorMsg);
      }

    } catch (error) {
      this.showPagePreviewError(`加载异常: ${error.message}`);
    }
  }

  /**
   * 显示页面预览面板
   */
  async showPreviewPanel(templateData) {
    try {
      
      // 选择目标tab：优先使用已记录的预览tabId
      let targetTabId = this._previewTabId;
      if (!targetTabId) {
        const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
        if (!tab) { return; }
        targetTabId = tab.id;
        this._previewTabId = targetTabId;
      }

      // 发送消息到content script显示预览面板
      const response = await this.sendTabMessage(targetTabId, {
        type: 'SHOW_PAGE_PREVIEW',
        data: { templateData }
      });

      // 静默处理响应
    } catch (error) {
      // 静默处理错误
    }
  }

  /**
   * 显示页面预览内容
   */
  async showPreviewContent(content) {
    try {
      
      // 选择目标tab：优先使用已记录的预览tabId
      let targetTabId = this._previewTabId;
      if (!targetTabId) {
        const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
        if (!tab) { return; }
        targetTabId = tab.id;
        this._previewTabId = targetTabId;
      }

      // 发送内容到content script显示预览
      const response = await this.sendTabMessage(targetTabId, {
        type: 'DISPLAY_PAGE_PREVIEW_CONTENT',
        data: { content }
      });

      // 静默处理响应
    } catch (error) {
      // 静默处理错误
    }
  }

  /**
   * 显示页面预览错误
   */
  async showPagePreviewError(errorMsg) {
    try {
      
      // 选择目标tab：优先使用已记录的预览tabId
      let targetTabId = this._previewTabId;
      if (!targetTabId) {
        const tab = await this.getCurrentTab();
        if (!tab) { return; }
        targetTabId = tab.id;
        this._previewTabId = targetTabId;
      }

      await this.sendTabMessage(targetTabId, {
        type: 'SHOW_PAGE_PREVIEW_ERROR',
        data: { errorMsg: errorMsg }
      });

    } catch (error) {
      // 静默处理错误
    }
  }

  /**
   * 限制预览缓存大小，避免内存泄漏
   */
  limitPreviewCache() {
    const maxCacheSize = 10; // 最多缓存10个模板
    if (this.previewCache.size > maxCacheSize) {
      const firstKey = this.previewCache.keys().next().value;
      this.previewCache.delete(firstKey);
    }
  }


  // 切换标签
  switchTab(tabName) {
    // 更新标签按钮状态
    document.querySelectorAll('.tab-btn').forEach(btn => {
      btn.classList.remove('active');
    });
    document.querySelector(`[data-tab="${tabName}"]`).classList.add('active');

    // 更新内容面板
    document.querySelectorAll('.tab-content').forEach(content => {
      content.classList.remove('active');
    });
    document.getElementById(`${tabName}Tab`).classList.add('active');

    this.currentTab = tabName;

    // 根据标签类型加载相应数据
    if (tabName === 'editor') {
      // 切换到内容生成标签时，确保模板列表是最新的
      this.loadTemplates();
    }
  }
}

// 初始化侧边栏
window.weChatAssistant = new WeChatAssistantSidePanel();