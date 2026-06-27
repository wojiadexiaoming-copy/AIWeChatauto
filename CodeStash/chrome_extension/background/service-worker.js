// service-worker.js
// 公众号智能美化助手 - 后台服务
// 处理API请求、消息传递和插件状态管理

'use strict';

// 全局错误处理
self.addEventListener('error', (event) => {
  // 静默处理错误
});

self.addEventListener('unhandledrejection', (event) => {
  event.preventDefault();
});

// 内嵌加密解密工具
class EncryptionUtils {
  static encrypt(text) {
    try {
      let encrypted = '';
      for (let i = 0; i < text.length; i++) {
        const char = text.charCodeAt(i);
        encrypted += String.fromCharCode(char ^ (i % 256));
      }
      // 使用更安全的Base64编码方式
      return btoa(unescape(encodeURIComponent(encrypted)));
    } catch (error) {
      // 静默处理错误
      return text;
    }
  }

  static decrypt(encryptedText) {
    try {
      const decoded = decodeURIComponent(escape(atob(encryptedText)));
      let decrypted = '';
      for (let i = 0; i < decoded.length; i++) {
        const char = decoded.charCodeAt(i);
        decrypted += String.fromCharCode(char ^ (i % 256));
      }
      return decrypted;
    } catch (error) {
      // 静默处理错误
      return encryptedText;
    }
  }

  static get ENCRYPTED_URLS() {
    return {
      GET_Edge_tenplates: 'aHR0cHM6Ly9lbnYtMDBqeHR4eDl5NThrLmRldi1oei5jbG91ZGJhc2VmdW5jdGlvbi5jbi9HRVRfRWRnZV90ZW5wbGF0ZXM=',
      GET_Edge_key: 'aHR0cHM6Ly9lbnYtMDBqeHR4eDl5NThrLmRldi1oei5jbG91ZGJhc2VmdW5jdGlvbi5jbi9HRVRfRWRnZV9rZXk='
    };
  }

  static getDecryptedUrl(functionName) {
    const encryptedUrl = this.ENCRYPTED_URLS[functionName];
    if (!encryptedUrl) {
      // 静默处理错误
      return null;
    }
    
    try {
      // 直接使用Base64解码，因为URL是用Base64编码的
      return atob(encryptedUrl);
    } catch (error) {
      // 静默处理错误
      return null;
    }
  }
}

// Edge兼容性：全局错误处理
self.addEventListener('error', (event) => {
  // 静默处理错误
});

self.addEventListener('unhandledrejection', (event) => {
  event.preventDefault();
});

// API配置 - 基础配置，用户配置优先
const API_CONFIG = {
  alibaba: {
    baseUrl: 'https://dashscope.aliyuncs.com/compatible-mode/v1', // 使用OpenAI兼容模式
    defaultModel: '' // 默认模型为空，由用户自定义
  },
  // UniCloud云函数配置
  unicloud: {
    // 使用加密的云函数URL
    getBaseUrl: () => {
      const url = EncryptionUtils.getDecryptedUrl('GET_Edge_tenplates');
      if (!url) {
        // 静默处理错误
      }
      return url;
    },
    functionName: 'GET_Edge_tenplates',
    timeout: 30000 // 30秒超时
  }
};

// 内嵌IndexedDB工具类 - 避免importScripts路径问题
class BackgroundDB {
  constructor() {
    this.dbName = 'WeChatAssistantDB';
    this.version = 2; // 升级版本号来添加cache表
    this.db = null;
    this._memoryCache = new Map(); // 内存缓存作为备用
  }

  async init() {
    return new Promise((resolve, reject) => {
      const request = indexedDB.open(this.dbName, this.version);

      request.onerror = () => reject(request.error);
      request.onsuccess = () => {
        this.db = request.result;
        resolve(this.db);
      };

      request.onupgradeneeded = (event) => {
        const db = event.target.result;
        
        if (!db.objectStoreNames.contains('config')) {
          db.createObjectStore('config', { keyPath: 'key' });
        }
        
        
        // 添加缓存表
        if (!db.objectStoreNames.contains('cache')) {
          const cacheStore = db.createObjectStore('cache', { keyPath: 'key' });
          cacheStore.createIndex('expiry', 'expiry', { unique: false });
        }
      };
    });
  }

  async ensureConnection() {
    if (!this.db) {
      await this.init();
    }
    return this.db;
  }

  async saveConfig(configData) {
    try {
      await this.ensureConnection();
      const transaction = this.db.transaction(['config'], 'readwrite');
      const store = transaction.objectStore('config');

      const promises = Object.entries(configData).map(([key, value]) => {
        return new Promise((resolve, reject) => {
          const request = store.put({ key, value, timestamp: Date.now() });
          request.onsuccess = () => { resolve(); };
          request.onerror = () => {
            
            reject(request.error);
          };
        });
      });

      await Promise.all(promises);
      return { success: true };
    } catch (error) {
      
      return { success: false, error: error.message };
    }
  }

  async getConfig() {
    try {
      await this.ensureConnection();
      const transaction = this.db.transaction(['config'], 'readonly');
      const store = transaction.objectStore('config');
      
      return new Promise((resolve) => {
        const request = store.getAll();
        request.onsuccess = () => {
          const configs = {};
          request.result.forEach(item => {
            configs[item.key] = item.value;
          });
          
          const defaultConfig = {
            isEnabled: true,
            customPrompt: ''
          };
          resolve({ ...defaultConfig, ...configs });
        };
        request.onerror = () => {
          resolve({});
        };
      });
    } catch (error) {
      return { isEnabled: true, customPrompt: '' };
    }
  }


  // 缓存相关方法
  async setCache(key, value, expiryMinutes = 60) {
    try {
      await this.ensureConnection();
      const transaction = this.db.transaction(['cache'], 'readwrite');
      const store = transaction.objectStore('cache');
      
      const expiry = new Date();
      expiry.setMinutes(expiry.getMinutes() + expiryMinutes);
      
      const request = store.put({
        key,
        value,
        expiry: expiry.getTime(),
        timestamp: Date.now()
      });
      
      return new Promise((resolve, reject) => {
        request.onsuccess = () => resolve(true);
        request.onerror = () => reject(request.error);
      });
    } catch (error) {
      // 静默处理错误，使用内存缓存作为备用
      this._memoryCache.set(key, { value, expiry: Date.now() + (expiryMinutes * 60 * 1000) });
      return true;
    }
  }

  async getCache(key) {
    try {
      await this.ensureConnection();
      const transaction = this.db.transaction(['cache'], 'readonly');
      const store = transaction.objectStore('cache');
      
      return new Promise((resolve) => {
        const request = store.get(key);
        request.onsuccess = () => {
          const result = request.result;
          if (!result) {
            resolve(null);
            return;
          }
          
          // 检查是否过期
          if (result.expiry && result.expiry < Date.now()) {
            // 过期则删除
            this.deleteCache(key);
            resolve(null);
            return;
          }
          
          resolve(result.value);
        };
        request.onerror = () => {
          // 数据库查询失败，尝试内存缓存
          const memoryItem = this._memoryCache.get(key);
          if (memoryItem && memoryItem.expiry > Date.now()) {
            resolve(memoryItem.value);
          } else {
            this._memoryCache.delete(key);
            resolve(null);
          }
        };
      });
    } catch (error) {
      // 静默处理错误，尝试内存缓存
      const memoryItem = this._memoryCache.get(key);
      if (memoryItem && memoryItem.expiry > Date.now()) {
        return memoryItem.value;
      } else {
        this._memoryCache.delete(key);
        return null;
      }
    }
  }

  async deleteCache(key) {
    try {
      await this.ensureConnection();
      const transaction = this.db.transaction(['cache'], 'readwrite');
      const store = transaction.objectStore('cache');
      
      const request = store.delete(key);
      
      // 同时删除内存缓存
      this._memoryCache.delete(key);
      
      return new Promise((resolve, reject) => {
        request.onsuccess = () => resolve(true);
        request.onerror = () => reject(request.error);
      });
    } catch (error) {
      // 静默处理错误
      this._memoryCache.delete(key);
      return true;
    }
  }

  // 定期清理过期缓存
  async cleanupExpiredCache() {
    try {
      await this.ensureConnection();
      const transaction = this.db.transaction(['cache'], 'readwrite');
      const store = transaction.objectStore('cache');
      const index = store.index('expiry');
      
      // 查询所有过期的缓存项
      const now = Date.now();
      const request = index.getAllKeys(IDBKeyRange.upperBound(now));
      
      request.onsuccess = () => {
        const keys = request.result;
        if (keys && keys.length > 0) {
          // 删除所有过期的缓存项
          keys.forEach(key => {
            store.delete(key);
          });
        }
      };
    } catch (error) {
      // 静默处理错误
    }
  }
}

// 主要的后台服务类
class WeChatAssistantService {
  constructor() {
    this.db = new BackgroundDB();
    this.isInitialized = false;
    this.apiConfig = {
      apiKey: '',
      model: API_CONFIG.alibaba.defaultModel
    };
    
    // VIP相关
    this.vipKeyRequestLog = []; // 存储请求记录
    this.vipKeyCache = new Map(); // 修复未初始化导致的访问错误
    
    this.init();
  }





  // 【新增辅助函数】
  async sendRuntimeMessageAsync(message) {
    return new Promise((resolve, reject) => {
      chrome.runtime.sendMessage(message, (response) => {
        if (chrome.runtime.lastError) {
          // 如果有错误，比如接收方不存在，Promise 将被 reject
          reject(new Error(chrome.runtime.lastError.message));
        } else {
          resolve(response);
        }
      });
    });
  }












  // 初始化
  async init() {
    try {
      // 设置事件监听器
      if (chrome.runtime && chrome.runtime.onInstalled) {
        chrome.runtime.onInstalled.addListener(this.onInstalled.bind(this));
      }
      
      // 监听消息
      if (chrome.runtime && chrome.runtime.onMessage) {
        chrome.runtime.onMessage.addListener(this.onMessage.bind(this));
      }
      
      // 监听标签页更新
      if (chrome.tabs && chrome.tabs.onUpdated) {
        chrome.tabs.onUpdated.addListener(this.onTabUpdated.bind(this));
      }
      
      // 监听标签页激活事件
      if (chrome.tabs && chrome.tabs.onActivated) {
        chrome.tabs.onActivated.addListener(this.onTabActivated.bind(this));
      }
      
      // 监听标签页移除事件
      if (chrome.tabs && chrome.tabs.onRemoved) {
        chrome.tabs.onRemoved.addListener(this.onTabRemoved.bind(this));
      }
      
      // 监听扩展图标点击事件 (Manifest V3 使用 chrome.action)
      if (chrome.action && chrome.action.onClicked) {
        chrome.action.onClicked.addListener(this.onActionClicked.bind(this));
      } else if (chrome.browserAction && chrome.browserAction.onClicked) {
        chrome.browserAction.onClicked.addListener(this.onActionClicked.bind(this));
      }
      
      // 异步初始化
      this.delayedInit();
    } catch (error) {
      // 静默处理错误
    }
  }

  // 异步初始化（不阻塞Service Worker注册）
  async delayedInit() {
    try {
      // 初始化数据库
      await this.db.init();
      
      // 加载用户API配置
      await this.loadUserApiConfig();

      // 设置 Chrome 侧边栏点击图标直接打开的行为 (任何网站均可打开，不做域名限制)
      if (chrome.sidePanel && chrome.sidePanel.setPanelBehavior) {
        chrome.sidePanel.setPanelBehavior({ openPanelOnActionClick: true }).catch(e => {
          console.error('[Chrome 扩展] 设置侧边栏打开行为失败:', e);
        });
      }
      
      this.isInitialized = true;
      
      // 启动定期清理任务（每小时清理一次过期缓存）
      setInterval(() => {
        this.db.cleanupExpiredCache();
      }, 60 * 60 * 1000);

      // 启动自动发布状态机轮询
      this.startTaskPolling();
    } catch (error) {
      // 静默处理错误，避免影响Service Worker注册
    }
  }

  /**
   * 加载用户API配置
   */
  async loadUserApiConfig() {
    try {
      const configResult = await this.getApiConfig();
      if (configResult.success && configResult.data.apiKey) {
        this.apiConfig.apiKey = configResult.data.apiKey;
        this.apiConfig.model = configResult.data.model || API_CONFIG.alibaba.defaultModel;
      }
    } catch (error) {
      // 静默处理错误
    }
  }

  // 启动后台任务状态轮询
  startTaskPolling() {
    const poll = async () => {
      try {
        const response = await fetch('http://127.0.0.1:5000/api/extension/task');
        if (response.ok) {
          const data = await response.json();
          if (data.success && data.task) {
            const task = data.task;
            if (task.status === 'start') {
              await this.handleStartTask(task);
            }
          }
        }
      } catch (err) {
        // 后端可能未启动，静默处理
      }
      setTimeout(poll, 3000);
    };
    poll();
  }

  // 处理开始任务：打开公众号页面并推进状态
  async handleStartTask(task) {
    try {
      // 1. 查询现有的公众号页面标签页
      const tabs = await chrome.tabs.query({});
      let wechatTab = tabs.find(t => t.url && t.url.includes('mp.weixin.qq.com'));
      
      if (wechatTab) {
        // 激活并聚焦已存在的标签页
        await chrome.windows.update(wechatTab.windowId, { focused: true });
        await chrome.tabs.update(wechatTab.id, { active: true });
      } else {
        // 不存在则新建一个
        wechatTab = await chrome.tabs.create({ url: 'https://mp.weixin.qq.com/' });
      }
      
      // 2. 将后端任务推进到 waiting_login 状态
      await fetch('http://127.0.0.1:5000/api/extension/task/progress', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: 'waiting_login' })
      });
    } catch (e) {
      // 上报错误
      await fetch('http://127.0.0.1:5000/api/extension/task/progress', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: 'error', error_message: '打开公众号后台失败: ' + e.message })
      });
    }
  }

  // 插件安装时的初始化
  async onInstalled(details) {
    try {
      // 初始化IndexedDB
      await this.db.init();
      
      // 设置默认配置
      await this.db.saveConfig({
        isEnabled: true,
        customPrompt: ''
      });
    } catch (error) {
      // 静默处理错误
    }
  }

  // 消息处理中心 - 10分钟超时和流式处理
  onMessage(message, sender, sendResponse) {
    
    // 设置10分钟超时机制
    const timeoutId = setTimeout(() => {
      if (sendResponse) {
        sendResponse({ success: false, error: '处理超时（10分钟），请稍后重试' });
      }
    }, 600000); // 10分钟超时（600秒）
    
    // 处理异步消息，返回Promise
    const handleMessage = async () => {
      try {
        // 确保初始化完成（等待最多5秒）
        let waitCount = 0;
        while (!this.isInitialized && waitCount < 50) {
          await new Promise(resolve => setTimeout(resolve, 100));
          waitCount++;
        }
        
        if (!this.isInitialized) {
          // 静默处理错误
        }
        
        switch (message.type) {
          case 'PING':
            return { success: true, message: 'PONG', timestamp: Date.now() };
          
          case 'CHECK_READY':
            return { 
              success: true, 
              ready: this.isInitialized, 
              timestamp: Date.now(),
              message: this.isInitialized ? '后台服务已就绪' : '后台服务初始化中'
            };
          
          case 'PROCESS_CONTENT_STREAM':
            // [MODIFIED] 立即返回，并异步处理流式数据
            this.processContentStream(message.data, sender);
            // 告知调用方，这是一个异步流式响应
            sendResponse({ success: true, isStream: true, message: 'Streaming process started.' });
            return true; // 保持消息通道开放
          
          case 'GET_CONFIG':
            return await this.getConfig();
          
          case 'SET_CONFIG':
            return await this.setConfig(message.data);
          
          
          // ============ 云函数相关消息处理 ============
          case 'GET_TEMPLATES':
            return await this.getTemplatesFromCloud(message.data?.forceRefresh);
          
          case 'GET_TEMPLATE_CONTENT':
            return await this.getTemplateContentFromCloud(message.data?.templateUrl);
          
          case 'REFRESH_TEMPLATES_CACHE':
            return await this.refreshTemplatesCache();
          
          case 'CLEAR_TEMPLATES_CACHE':
            await this.clearTemplateCache();
            return { success: true, message: '模板缓存已清除' };

          // ============ 预览图准备（通过storage传输大数据） ============
          case 'PREPARE_PREVIEW_IMAGE':
            return await this.preparePreviewImage(message.data);
          
          // ============ API配置相关消息处理 ============
          case 'GET_API_CONFIG':
            return await this.getApiConfig();
          
          case 'SAVE_API_CONFIG':
            return await this.saveApiConfig(message.data);
          
          // ============ VIP相关消息处理 ============
          case 'SAVE_VIP_KEY':
            return await this.saveVipKey(message.data);
          
          case 'TEST_VIP_KEY':
            return await this.testVipKey(message.data);
          
          case 'CHECK_VIP_ACCESS':
            return await this.checkVipAccessLocal();
          
          case 'CHECK_VIP_KEY_STATUS':
            return await this.checkVipKeyStatus();
          




          // 【新增 CASE】
          case 'FORCE_CHECK_VIP_STATUS':

            // 获取已保存的密钥
            const config = await this.getApiConfig();
            if (config.success && config.data.vipKey) {
                // 清除缓存并重新验证
                this.vipKeyCache.delete(config.data.vipKey);
                return await this.validateVipKey(config.data.vipKey);
            }
            return { success: false, error: '未配置VIP密钥' };













          // 添加对content script消息的处理
          case 'WORD_COUNT_UPDATED':
            // 这个消息来自content script，需要转发给sidepanel
            // 但由于这是background script，我们不能直接发送消息给sidepanel
            // 静默处理
            return { success: true, message: '已接收字数更新' };
          
          case 'CONTENT_UPDATED':
            // 这个消息来自content script，需要转发给sidepanel
            // 但由于这是background script，我们不能直接发送消息给sidepanel
            // 静默处理
            return { success: true, message: '已接收内容更新' };
          
          default:
            return { success: false, error: `未知消息类型: ${message.type}` };
        }
      } catch (error) {
        return { success: false, error: error.message };
      } finally {
        // 清除超时定时器
        clearTimeout(timeoutId);
      }
    };

    // 执行消息处理
    handleMessage().then(response => {
      // [MODIFIED] 仅在 response 不为 true 时才调用 sendResponse
      // 因为流式处理已经调用过 sendResponse 了
      if (response !== true && sendResponse) {
        sendResponse(response);
      }
    }).catch(error => {
      if (sendResponse) {
        sendResponse({ success: false, error: error.message });
      }
    });

    // Firefox兼容性：返回true以保持消息通道开放
    return true;
  }

  // 扩展图标点击事件处理 - 打开侧边栏
  async onActionClicked(tab) {
    try {
      // 优先在当前窗口拉起 Chrome 侧边栏 (不限制域名，任何网站皆可打开)
      if (chrome.sidePanel && chrome.sidePanel.open) {
        await chrome.sidePanel.open({ windowId: tab.windowId });
      } else if (chrome.sidebarAction && chrome.sidebarAction.open) {
        // Firefox兼容性：使用sidebar_action API
        await chrome.sidebarAction.open();
      } else {
        // 备用方案：创建新窗口
        if (chrome.windows && chrome.windows.create) {
          await chrome.windows.create({
            url: chrome.runtime.getURL('sidepanel/sidepanel.html'),
            type: 'popup',
            width: 1000,
            height: 600,
            focused: true
          });
        }
      }
    } catch (error) {
      // 如果侧边栏打开失败，尝试备用方案
      try {
        if (chrome.windows && chrome.windows.create) {
          await chrome.windows.create({
            url: chrome.runtime.getURL('sidepanel/sidepanel.html'),
            type: 'popup',
            width: 1000,
            height: 600,
            focused: true
          });
        }
      } catch (fallbackError) {
        // 静默处理错误
      }
    }
  }

  // 标签页更新监听 - 在微信公众号页面启用侧边栏
  async onTabUpdated(tabId, changeInfo, tab) {
    if (changeInfo.status === 'complete' && 
        tab.url && 
        tab.url.includes('mp.weixin.qq.com')) {
      
      try {
        // Firefox兼容性：使用sidebar_action API
        if (chrome.sidebarAction && chrome.sidebarAction.setPanel) {
          await chrome.sidebarAction.setPanel({
            tabId,
            panel: 'sidepanel/sidepanel.html'
          });
        }
      } catch (error) {
        // 静默处理错误
      }
    }
  }

  // 标签页激活监听 - 当用户切换到微信公众号标签页时通知侧边栏更新
  async onTabActivated(activeInfo) {
    try {
      // 获取激活的标签页信息
      const tab = await chrome.tabs.get(activeInfo.tabId);
      
      // 检查是否为微信公众号页面
      if (tab.url && tab.url.includes('mp.weixin.qq.com')) {
        // 通知侧边栏更新状态
        // 注意：这里我们不直接发送消息，因为侧边栏可能未打开
        // 侧边栏会在打开时主动检查状态
      }
    } catch (error) {
      // 静默处理错误
      if (!error.message.includes('No tab') && !error.message.includes('Cannot access')) {
        // 静默处理错误
      }
    }
  }
  
  // 标签页移除监听 - 当微信公众号标签页关闭时清理相关资源
  async onTabRemoved(tabId, removeInfo) {
    try {
      // 可以在这里添加清理逻辑
    } catch (error) {
      // 静默处理错误
    }
  }

  // [MODIFIED] 处理流式内容优化请求
  async processContentStream(data, sender) {
    try {
      const { content, prompt, templateInfo, structuredContent } = data;
      
      const configResult = await this.getApiConfig();
      if (!configResult.success || !configResult.data.apiKey) {
        throw new Error('API Key 未配置');
      }
      
      const { apiKey, model } = configResult.data;
      if (!this.validateApiKey(apiKey)) {
        throw new Error('API Key 格式不正确');
      }









      // 定义流式更新的回调函数
      const onUpdate = (chunk, fullContent) => {
        // 使用新的异步辅助函数发送消息
        this.sendRuntimeMessageAsync({
          type: 'STREAM_UPDATE',
          data: { content: chunk }
        }).catch(e => {});
      };

      // 调用流式 API，并等待其完成
      const result = await this.callAliAPIStream(
        structuredContent, // 使用结构化内容以获得更好的结果
        prompt,
        apiKey,
        onUpdate, // 传递 onUpdate 回调
        templateInfo,
        model
      );
      
      // 流结束后，发送完成消息
      await this.sendRuntimeMessageAsync({
        type: 'STREAM_COMPLETE',
        success: true,
        data: {
          content: result.content,
          tokenUsage: result.tokenUsage
        }
      }).catch(e => {});

    } catch (error) {
      // 发送失败消息
      await this.sendRuntimeMessageAsync({
        type: 'STREAM_COMPLETE',
        success: false,
        error: error.message || '流式内容处理失败，请稍后重试'
      }).catch(e => {});
    }
  }




















  // [MODIFIED] 调用阿里百练API - 流式响应版本
  async callAliAPIStream(structuredContent, prompt, apiKey, onUpdate = null, templateInfo = null, model = null) {
    // 获取当前日期
    const currentDate = new Date().toLocaleDateString('zh-CN', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      weekday: 'long'
    });
    
    // 角色设定 - 包含完整的角色定义和详细要求
    const rolePrompt = `你是一位专业的微信公众号内容创作者和排版专家，拥有丰富的数字媒体经验，精通内容策划、用户心理分析和新媒体营销。你严谨且专业地将用户给到的内容在不更改任何文本的前提下，完美套用模板，确保内容符合微信官方要求。

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
    
    // 读取模板内容
    let formatTemplate = '';
    if (templateInfo && templateInfo.content) {
      formatTemplate = templateInfo.content;
    } else {
      formatTemplate = this.getBuiltinDefaultTemplate();
    }
    
    // 构建系统提示词
    const systemPrompt = rolePrompt + 
      "\n\n当前日期时间：" + currentDate + 
      "\n\n模板结构：\n" + formatTemplate + 
      "\n\n用户要求：" + prompt;

    // [MODIFIED] 使用格式化后的结构化内容作为用户输入
    const userContentText = this.formatStructuredContentForLLM(structuredContent);

    const requestBody = {
      model: model || this.apiConfig.model,
      messages: [
        { role: 'system', content: systemPrompt },
        { role: 'user', content: userContentText } // 使用格式化后的结构化内容
      ],
      stream: true,
      stream_options: { include_usage: true },
      temperature: 0.7,
      top_p: 0.9
    };

    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 300000); // 5分钟超时
      
      const response = await fetch('http://127.0.0.1:5000/api/chat/completions', {
          method: 'POST',
          headers: {
              'Content-Type': 'application/json'
          },
          body: JSON.stringify(requestBody),
          signal: controller.signal,
          cache: 'no-store'
      });

      clearTimeout(timeoutId);

      if (!response || !response.ok) {
        const errorText = response ? await response.text() : 'No response from server';
        let errorMessage = `API请求失败: ${response ? response.status : 'N/A'}`;
        
        try {
          const errorData = JSON.parse(errorText);
          if (errorData.error && errorData.error.message) {
            errorMessage += ` - ${errorData.error.message}`;
          } else if (errorData.message) {
            errorMessage += ` - ${errorData.message}`;
          }
        } catch (e) {
          errorMessage += ` - ${errorText}`;
        }
        
        throw new Error(errorMessage);
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let fullContent = '';
      let buffer = '';
      let tokenUsage = null;

      try {
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split('\n');
          buffer = lines.pop();

          for (const line of lines) {
            if (line.trim() === '' || !line.startsWith('data: ')) continue;
            
            const data = line.slice(6);
            if (data === '[DONE]') continue;

            try {
              const chunk = JSON.parse(data);
              
              // 提取内容块
              const contentChunk = chunk.choices?.[0]?.delta?.content;
              if (contentChunk) {
                fullContent += contentChunk;
                // 【核心修改】调用 onUpdate 回调，实时将数据块发出去
                if (typeof onUpdate === 'function') {
                  onUpdate(contentChunk, fullContent);
                }
              }
              
              // 提取最终的 token usage
              if (chunk.usage) {
                tokenUsage = chunk.usage;
              }
            } catch (parseError) {
            }
          }
        }
      } finally {
        reader.releaseLock();
      }

      // 返回最终的完整内容和token使用信息
      return {
        content: fullContent,
        tokenUsage: tokenUsage
      };

    } catch (error) {
      const msg = (error && error.message) ? error.message : '';
      if (/network/i.test(msg) || /typeerror/i.test(error?.name || '') || /abort/i.test(error?.name || '')) {
        throw new Error('网络连接失败或被拦截，请检查网络/代理设置，稍后重试');
      }
      throw this.handleAPIError(error);
    }
  }

  // [ADDED] 新增工具函数
  formatStructuredContentForLLM(structured) {
    if (!structured || !Array.isArray(structured)) {
      return '';
    }
    return structured.map((item, index) => {
      if (item.type === 'text') {
        return `[文本${index + 1}] ${item.content}`;
      } else if (item.type === 'image') {
        return `[图片${index + 1}] 元素: ${item.content.element}`;
      } else if (item.type === 'video') {
        return `[视频${index + 1}] 元素: ${item.content.element}`;
      }
      return '';
    }).join('\n\n');
  }

  // 判断是否应该重试
  shouldNotRetry(error) {
    const message = error.message.toLowerCase();
    return message.includes('401') ||  // 认证错误
           message.includes('403') ||  // 权限错误
           message.includes('invalid') || // 无效请求
           message.includes('quota'); // 配额错误
  }

  // 统一的错误处理
  handleAPIError(error) {
    const message = error.message;
    
    if (message.includes('401')) {
      return new Error('API密钥验证失败，请检查API Key是否正确配置');
    } else if (message.includes('429')) {
      return new Error('请求频率过高，请稍后重试');
    } else if (message.includes('quota')) {
      return new Error('API调用额度不足，请检查账户余额');
    } else if (message.includes('timeout')) {
      return new Error('请求超时，请检查网络连接');
    } else if (message.includes('network')) {
      return new Error('网络连接失败，请检查网络状态');
    }
    
    return new Error(`API调用失败: ${message}`);
  }

  // 获取配置（使用IndexedDB）
  async getConfig() {
    try {
      const config = await this.db.getConfig();
      return config;
    } catch (error) {
      return {
        isEnabled: true,
        customPrompt: ''
      };
    }
  }

  // 设置配置（使用IndexedDB）
  async setConfig(config) {
    try {
      const result = await this.db.saveConfig(config);
      return result;
    } catch (error) {
      return { success: false, error: error.message };
    }
  }


  // ============ 云函数相关方法 ============
  /**
   * 将模板预览图写入 storage 并返回 key，避免大数据通过消息通道传输
   * @param {{ templateId?: string, templateUrl?: string }} data
   */
  async preparePreviewImage(data) {
    try {
      const { templateId, templateUrl } = data || {};
      // 从缓存的模板列表中查找
      const list = await this.db.getCache('templates_list');
      if (list && Array.isArray(list)) {
        const item = list.find(t => t.id === templateId || t.url === templateUrl);
        if (item && item.html && typeof item.html === 'string' && item.html.startsWith('data:image/')) {
          const key = `preview_image_${templateId || Date.now()}`;
          if (chrome.storage && chrome.storage.local) {
            await new Promise(resolve => chrome.storage.local.set({ [key]: item.html }, resolve));
          }
          return { success: true, key, size: item.html.length };
        }
      }
      return { success: false, error: '未找到预览图数据' };
    } catch (error) {
      return { success: false, error: error.message };
    }
  }
  
  /**
   * 从云端获取模板列表
   * @param {boolean} forceRefresh 是否强制刷新（忽略缓存）
   * @returns {Promise<Object>} 模板列表数据
   */
  async getTemplatesFromCloud(forceRefresh = false) {
    try {
      // 优先从本地后台获取模板列表
      try {
        const response = await fetch('http://127.0.0.1:5000/api/style-templates');
        if (response.ok) {
          const json = await response.json();
          const templates = Array.isArray(json) ? json : (json.data || []);
          
          // 缓存模板列表到本地数据库
          await this.db.setCache('templates_list', templates, 7 * 24 * 60);
          
          return {
            success: true,
            data: templates,
            source: 'backend'
          };
        }
      } catch (e) {
        console.error('[Chrome 扩展] 获取后台模板失败，尝试使用本地缓存:', e);
      }

      // 尝试从缓存获取模板列表
      if (!forceRefresh) {
        const cachedData = await this.db.getCache('templates_list');
        if (cachedData) {
          return {
            success: true,
            data: cachedData,
            source: 'cache'
          };
        }
      }

      return {
        success: true,
        data: [],
        source: 'empty'
      };
    } catch (error) {
      return {
        success: false,
        error: error.message
      };
    }
  }
  
  /**
   * 从云端获取模板内容
   * @param {string} templateUrl 模板URL
   * @returns {Promise<Object>} 模板内容数据
   */
  async getTemplateContentFromCloud(templateUrl) {
    try {
      // 优先在缓存模板列表中查找匹配的 content
      const cachedList = await this.db.getCache('templates_list');
      if (cachedList && Array.isArray(cachedList)) {
        const matched = cachedList.find(t => t.url === templateUrl || t.id === templateUrl || t.name === templateUrl);
        if (matched && matched.content) {
          return {
            success: true,
            data: matched.content,
            source: 'cache'
          };
        }
      }

      // 如果缓存没有，直接拉取后台接口
      const response = await fetch('http://127.0.0.1:5000/api/style-templates');
      if (response.ok) {
        const json = await response.json();
        const templates = Array.isArray(json) ? json : (json.data || []);
        const matched = templates.find(t => t.url === templateUrl || t.id === templateUrl || t.name === templateUrl);
        if (matched && matched.content) {
          return {
            success: true,
            data: matched.content,
            source: 'backend'
          };
        }
      }

      return {
        success: false,
        error: '未找到指定模板内容'
      };
    } catch (error) {
      return {
        success: false,
        error: error.message,
        code: 'TEMPLATE_CONTENT_ERROR'
      };
    }
  }
  
  /**
   * 刷新所有模板缓存
   * @returns {Promise<Object>} 刷新结果
   */
  async refreshTemplatesCache() {
    try {
      // 获取云函数基础URL
      const baseUrl = API_CONFIG.unicloud.getBaseUrl();
      if (!baseUrl) {
        throw new Error('云函数URL配置错误');
      }
      
      const url = new URL(baseUrl);
      url.searchParams.append('action', 'refreshCache');
      
      const response = await fetch(url.toString(), {
        method: 'GET',
        headers: {
          'Accept': 'application/json',
          'User-Agent': 'Edge-WeChatAssistant-Plugin/1.0'
        }
      });
      
      if (!response.ok) {
        throw new Error(`云函数请求失败: ${response.status} ${response.statusText}`);
      }
      
      // 处理uniCloud的HTTP URL化响应
      const result = await response.json();
      
      // 检查响应格式
      let actualResult = result;
      if (result.statusCode && result.body && typeof result.body === 'string') {
        try {
          actualResult = JSON.parse(result.body);
        } catch (parseError) {
          throw new Error('云函数返回数据格式错误: 无法解析响应体');
        }
      }
      
      if (actualResult.success) {
        // 清除本地相关缓存
        await this.clearTemplateCache();
        
        return actualResult;
      } else {
        throw new Error(actualResult.error || '缓存刷新失败');
      }
      
    } catch (error) {
      return {
        success: false,
        error: error.message,
        code: 'CACHE_REFRESH_ERROR'
      };
    }
  }
  
  /**
   * 清除本地模板缓存
   */
  async clearTemplateCache() {
    try {
      // 清除模板列表缓存
      await this.db.deleteCache('templates_list');
      
      // 这里可以添加更多缓存清理逻辑
    } catch (error) {
      // 静默处理错误
    }
  }
  
  /**
   * 获取模板数据（仅使用云端，不再回退到本地文件）
   * @param {string} templateName 模板名称或URL
   * @returns {Promise<string>} 模板内容
   */
  async getTemplateData(templateName) {
    try {
      // 从云端获取模板列表
      const templatesResult = await this.getTemplatesFromCloud();
      
      if (templatesResult.success && templatesResult.data) {
      // 在模板列表中查找匹配的模板
        const template = templatesResult.data.find(t => 
          t.name === templateName || 
          t.originalFileName === templateName ||
          t.url.includes(templateName) ||
          templateName.includes(t.name)
        );
        
        if (template) {
          // 获取模板内容（使用实际模板URL，不是预览URL）
          const contentResult = await this.getTemplateContentFromCloud(template.url);
          if (contentResult.success) {
            const content = contentResult.data.content || contentResult.data;
            return content;
          }
        }
      }
      
    } catch (error) {
      // 静默处理错误
    }
    
    // 如果云端获取失败，返回一个通用的默认模板
    return this.getBuiltinDefaultTemplate();
  }
  
  /**
   * 获取内置默认模板（不依赖任何文件）
   * @returns {string} 默认模板HTML内容
   */
  getBuiltinDefaultTemplate() {
    return `<div style="font-family: -apple-system, system-ui, BlinkMacSystemFont, 'Helvetica Neue', 'PingFang SC', 'Microsoft YaHei', sans-serif; line-height: 1.8; padding: 20px; max-width: 600px; margin: 0 auto; background: #fff;">
  <h2 style="color: #333; font-size: 24px; margin-bottom: 20px; text-align: center; border-bottom: 2px solid #667eea; padding-bottom: 10px;">默认模板标题</h2>
  
  <p style="color: #666; font-size: 16px; margin-bottom: 16px; text-indent: 2em;">这是默认模板的段落内容。您可以根据需要修改这里的文字和样式。</p>
  
  <blockquote style="border-left: 4px solid #667eea; background: #f8f9ff; padding: 16px; margin: 20px 0; color: #555; font-style: italic;">
    重要提示：这是一个默认模板，请配置正确的云端模板以获得更好的效果。
  </blockquote>
  
  <ul style="color: #666; padding-left: 20px; margin: 16px 0;">
    <li style="margin-bottom: 8px;">列表项目一</li>
    <li style="margin-bottom: 8px;">列表项目二</li>
    <li style="margin-bottom: 8px;">列表项目三</li>
  </ul>
  
  <p style="color: #666; font-size: 16px; margin-bottom: 16px; text-indent: 2em;">结尾段落内容，为您的文章提供完美收尾。</p>
</div>`;
  }
  
  // ============ API配置管理方法 ============
  
  /**
   * 从后台获取配置信息
   */
  async fetchBackendConfig() {
    try {
      const response = await fetch('http://127.0.0.1:5000/api/config');
      if (response.ok) {
        const json = await response.json();
        if (json.success) {
          return json.data;
        }
      }
    } catch (e) {
      console.error('[Chrome 扩展] 从后台获取配置失败:', e);
    }
    return null;
  }

  /**
   * 获取API配置
   */
  async getApiConfig() {
    try {
      // 优先从本地后台获取配置以实现密钥共享
      const backendConfig = await this.fetchBackendConfig();
      if (backendConfig) {
        let apiKey = '';
        let model = '';
        
        // 尝试按照顺序提取有效配置的 API Key 和 Model
        if (backendConfig.gemini_api_key) {
          apiKey = backendConfig.gemini_api_key;
          model = 'gemini';
        } else if (backendConfig.deepseek_api_key) {
          apiKey = backendConfig.deepseek_api_key;
          model = 'deepseek';
        } else if (backendConfig.dashscope_api_key) {
          apiKey = backendConfig.dashscope_api_key;
          model = 'dashscope';
        } else if (backendConfig.inodetree_api_key) {
          apiKey = backendConfig.inodetree_api_key;
          model = 'inodetree';
        }
        
        return {
          success: true,
          data: {
            apiKey: apiKey,
            model: model,
            vipKey: backendConfig.vip_key || 'backend-synchronized', // 优先提取后台保存的真正的 vip_key
            backendConfig: backendConfig
          }
        };
      }
      
      // 降级使用扩展本地存储的配置
      const config = await this.db.getConfig();
      return {
        success: true,
        data: {
          apiKey: config.apiKey || '',
          model: config.model || '',
          vipKey: config.vipKey || ''
        }
      };
    } catch (error) {
      return {
        success: false,
        error: error.message
      };
    }
  }
  
  /**
   * 保存API配置
   */
  async saveApiConfig(apiConfig) {
    try {
      if (!apiConfig.apiKey || !apiConfig.apiKey.trim()) {
        return {
          success: false,
          error: 'API Key不能为空'
        };
      }
      
      // 与后台进行配置同步
      const backendConfig = await this.fetchBackendConfig() || {};
      const model = (apiConfig.model || 'gemini').toLowerCase();
      
      if (model.includes('gemini')) {
        backendConfig.gemini_api_key = apiConfig.apiKey.trim();
        if (apiConfig.modelName) backendConfig.gemini_model = apiConfig.modelName;
      } else if (model.includes('deepseek')) {
        backendConfig.deepseek_api_key = apiConfig.apiKey.trim();
        if (apiConfig.modelName) backendConfig.deepseek_model = apiConfig.modelName;
      } else if (model.includes('dashscope') || model.includes('qwen')) {
        backendConfig.dashscope_api_key = apiConfig.apiKey.trim();
        if (apiConfig.modelName) backendConfig.dashscope_model = apiConfig.modelName;
      } else if (model.includes('inodetree')) {
        backendConfig.inodetree_api_key = apiConfig.apiKey.trim();
        if (apiConfig.modelName) backendConfig.inodetree_model = apiConfig.modelName;
      } else {
        backendConfig.dashscope_api_key = apiConfig.apiKey.trim();
        backendConfig.dashscope_model = apiConfig.model;
      }
      
      const response = await fetch('http://127.0.0.1:5000/api/config', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(backendConfig)
      });
      
      if (response.ok) {
        const json = await response.json();
        if (json.success) {
          this.apiConfig.apiKey = apiConfig.apiKey.trim();
          this.apiConfig.model = apiConfig.model || '';
          return {
            success: true,
            message: 'API配置同步到后端成功'
          };
        }
      }
      
      // 后台未启动时保存到扩展本地
      const configData = {
        apiKey: apiConfig.apiKey.trim(),
        model: apiConfig.model || '',
        vipKey: apiConfig.vipKey || ''
      };
      const result = await this.db.saveConfig(configData);
      if (result.success) {
        this.apiConfig.apiKey = apiConfig.apiKey.trim();
        this.apiConfig.model = apiConfig.model || '';
        return {
          success: true,
          message: 'API配置保存到本地成功'
        };
      }
      throw new Error(result.error || '保存失败');
    } catch (error) {
      return {
        success: false,
        error: error.message
      };
    }
  }
  
  /**
   * 验证API Key格式
   */
  validateApiKey(apiKey) {
    return apiKey && typeof apiKey === 'string' && 
           apiKey.startsWith('sk-') && apiKey.length > 20;
  }
  
  // ============ VIP相关方法 ============
  
  /**
   * 检查VIP密钥请求频率限制
   * @param {string} vipKey VIP密钥
   * @returns {boolean} 是否允许请求
   */
  checkVipKeyRequestLimit(vipKey) {
    const now = Date.now();
    const fiveMinutesAgo = now - (5 * 60 * 1000); // 5分钟前
    
    // 清理过期的请求记录
    this.vipKeyRequestLog = this.vipKeyRequestLog.filter(log => log.timestamp > fiveMinutesAgo);
    
    // 查找当前VIP密钥在5分钟内的请求次数
    const recentRequests = this.vipKeyRequestLog.filter(log => log.vipKey === vipKey);
    
    if (recentRequests.length >= 3) {
      return false;
    }
    
    // 记录此次请求
    this.vipKeyRequestLog.push({
      vipKey: vipKey,
      timestamp: now
    });
    
    return true;
  }
  
  /**
   * 检查VIP密钥缓存
   * @param {string} vipKey VIP密钥
   * @returns {Object|null} 缓存的验证结果或null
   */
  checkVipKeyCache(vipKey) {
    const cacheEntry = this.vipKeyCache.get(vipKey);
    
    if (!cacheEntry) {
      return null;
    }
    
    const now = Date.now();
    const tenMinutesAgo = now - (10 * 60 * 1000); // 10分钟前
    
    // 检查缓存是否过期
    if (cacheEntry.timestamp < tenMinutesAgo) {
      this.vipKeyCache.delete(vipKey);
      return null;
    }
    
    // 检查剩余天数是否大于等于1天
    if (cacheEntry.data && cacheEntry.data.remainingDays >= 1) {
      return cacheEntry;
    }
    
    // 如果剩余天数小于1天，不使用缓存
    return null;
  }
  
  /**
   * 缓存VIP密钥验证结果
   * @param {string} vipKey VIP密钥
   * @param {Object} data 验证结果数据
   */
  cacheVipKeyResult(vipKey, data) {
    this.vipKeyCache.set(vipKey, {
      data: data,
      timestamp: Date.now()
    });
  }
 





  /**
   * 保存VIP密钥
   */
  async saveVipKey(data) {
    try {
      const { vipKey } = data;
      
      if (!vipKey) {
        return { success: false, error: 'VIP密钥不能为空' };
      }
      
      // 【核心修复】在验证和保存前，先清除该密钥的旧缓存
      this.vipKeyCache.delete(vipKey);
      
      // 保存到IndexedDB
      const saveResult = await this.db.saveConfig({
        vipKey: vipKey
      });
      
      if (!saveResult.success) {
        return { success: false, error: 'VIP密钥保存失败: ' + (saveResult.error || '未知错误') };
      }
      
      // 强制重新验证密钥（因为缓存已清除，所以一定会调用云函数）
      const validationResult = await this.validateVipKey(vipKey);
      
      // 如果验证成功，validationResult 的结构是 { success: true, data: { isValid: true, remainingDays: ... } }
      // 我们直接将这个结果返回给 sidepanel
      if (validationResult.success) {
        return { 
          success: true, 
          message: 'VIP密钥已保存并验证成功',
          data: validationResult.data // 直接返回验证数据
        };
      } else {
        // 即使验证失败，保存操作也已成功，但要告知前端验证失败
         return { 
          success: false, // 将 success 设为 false，以触发前端的错误提示
          message: 'VIP密钥已保存，但验证失败',
          error: validationResult.error 
        };
      }
    } catch (error) {
      return { success: false, error: error.message };
    }
  }










  /**
   * 验证VIP密钥（纯验证，不保存）
   */
  async validateVipKey(vipKey) {
    try {
      if (!vipKey) {
        return { success: false, error: 'VIP密钥不能为空' };
      }
      
      // 1. 检查缓存
      const cachedResult = this.checkVipKeyCache(vipKey);
      // 【修复】正确处理缓存结构，直接返回缓存中的成功数据
      if (cachedResult && cachedResult.data && cachedResult.data.success) {
        return cachedResult.data;
      }
      
      // 2. 检查频率限制
      const isRequestAllowed = this.checkVipKeyRequestLimit(vipKey);
      // 【核心修复】当请求不被允许时（返回false），才认为是错误
      if (!isRequestAllowed) {
        return { success: false, error: '请求过于频繁，请在5分钟内最多尝试3次' };
      }
      
      // 3. 调用云函数验证
      const keyUrl = EncryptionUtils.getDecryptedUrl('GET_Edge_key');
      if (!keyUrl) {
        return { success: false, error: '云函数URL配置错误' };
      }
      
      const response = await fetch(keyUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          action: 'validateKey',
          key: vipKey
        })
      });
      
      if (!response.ok) {
        return { success: false, error: `云函数调用失败: ${response.status}` };
      }
      
      const result = await response.json();
      const responseData = result.body ? JSON.parse(result.body) : result;
      
      // 4. 缓存验证结果 (只有当验证成功且有剩余天数时才缓存)
      if (responseData.success && responseData.data && responseData.data.remainingDays >= 1) {
        this.cacheVipKeyResult(vipKey, responseData);
      }
      
      return responseData;

    } catch (error) {
      return { success: false, error: error.message };
    }
  }

















  /**
   * 测试VIP密钥（不保存，只验证）
   */
  async testVipKey(data) {
    try {
      const { vipKey } = data;
      
      if (!vipKey) {
        return { success: false, error: 'VIP密钥不能为空' };
      }
      
      // 直接调用验证方法
      return await this.validateVipKey(vipKey);
    } catch (error) {
      return { success: false, error: error.message };
    }
  }
  
  /**
   * 检查VIP访问权限（仅本地检查，不调用云函数）
   */
  async checkVipAccessLocal() {
    try {
      const configResult = await this.getApiConfig();
      
      // 后台已同步且包含任何 API Key 则判定为 VIP 权限
      if (configResult.success && configResult.data.backendConfig) {
        const bc = configResult.data.backendConfig;
        if (bc.gemini_api_key || bc.deepseek_api_key || bc.dashscope_api_key || bc.inodetree_api_key) {
          return { success: true, data: { hasVipAccess: true, reason: 'backend_valid' } };
        }
      }
      
      if (!configResult.success || !configResult.data.vipKey) {
        return { success: true, data: { hasVipAccess: false, reason: 'no_vip_key' } };
      }
      
      const vipKey = configResult.data.vipKey.trim();
      if (!vipKey.startsWith('sk-') || vipKey.length <= 20) { // VIP密钥格式验证
        return { success: true, data: { hasVipAccess: false, reason: 'invalid_format' } };
      }
      
      // 检查缓存中的VIP状态
      const cachedResult = this.checkVipKeyCache(vipKey);
      if (cachedResult && cachedResult.data && cachedResult.data.remainingDays > 0) {
        return { success: true, data: { hasVipAccess: true, reason: 'cached_valid' } };
      }
      
      // 没有有效的本地状态，需要用户手动验证
      return { success: true, data: { hasVipAccess: false, reason: 'need_verification' } };
      
    } catch (error) {
      return { success: false, error: error.message };
    }
  }
  
  /**
   * 检查VIP访问权限（旧版本，保留兼容性）
   */
  async checkVipAccess() {
    try {
      const configResult = await this.getApiConfig();
      
      // 后台已同步且包含任何 API Key 则判定为 VIP 权限
      if (configResult.success && configResult.data.backendConfig) {
        const bc = configResult.data.backendConfig;
        if (bc.gemini_api_key || bc.deepseek_api_key || bc.dashscope_api_key || bc.inodetree_api_key) {
          return { success: true, data: { hasVipAccess: true } };
        }
      }
      
      if (!configResult.success || !configResult.data.vipKey) {
        return { success: true, data: { hasVipAccess: false } };
      }
      
      // 验证VIP密钥状态
      const vipResult = await this.testVipKey({ vipKey: configResult.data.vipKey });
      
      if (vipResult.success && vipResult.data.isValid) {
        return { success: true, data: { hasVipAccess: true } };
      } else {
        return { success: true, data: { hasVipAccess: false } };
      }
    } catch (error) {
      return { success: false, error: error.message };
    }
  }
  
  /**
   * 检查VIP密钥状态
   */
  async checkVipKeyStatus() {
    try {
      const configResult = await this.getApiConfig();
      
      // 后台已同步且包含任何 API Key 则判定为 VIP 有效
      if (configResult.success && configResult.data.backendConfig) {
        const bc = configResult.data.backendConfig;
        if (bc.gemini_api_key || bc.deepseek_api_key || bc.dashscope_api_key || bc.inodetree_api_key) {
          return {
            success: true,
            data: {
              isValid: true,
              remainingDays: 9999,
              totalDays: 9999,
              message: '已成功与本地后台配置同步'
            }
          };
        }
      }
      
      if (!configResult.success || !configResult.data.vipKey) {
        return { success: false, error: 'VIP密钥未配置' };
      }
      
      // 调用云函数获取密钥信息
      const keyUrl = EncryptionUtils.getDecryptedUrl('GET_Edge_key');
      if (!keyUrl) {
        return { success: false, error: '云函数URL配置错误' };
      }
      
      const response = await fetch(keyUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          action: 'getKeyInfo',
          key: configResult.data.vipKey
        })
      });
      
      if (!response.ok) {
        return { success: false, error: `云函数调用失败: ${response.status}` };
      }
      
      const result = await response.json();
      
      // 云函数返回的是HTTP响应格式，需要检查body字段
      const responseData = result.body ? JSON.parse(result.body) : result;
      return responseData;
    } catch (error) {
      return { success: false, error: error.message };
    }
  }
  
  // 启动定期清理任务
  startPeriodicCleanup() {
    // 每5分钟清理一次过期数据
    setInterval(() => {
      this.cleanupExpiredData();
    }, 5 * 60 * 1000); // 5分钟
  }
  
  // 清理过期的缓存和记录
  cleanupExpiredData() {
    const now = Date.now();
    
    // 清理过期的VIP密钥缓存
    for (const [key, cacheData] of this.vipKeyCache.entries()) {
      if (now > cacheData.expiry) {
        this.vipKeyCache.delete(key);
      }
    }
    
    // 清理过期的请求记录（5分钟前的记录）
    const fiveMinutesAgo = now - 5 * 60 * 1000;
    const originalLength = this.vipKeyRequestLog.length;
    this.vipKeyRequestLog = this.vipKeyRequestLog.filter(log => log.timestamp > fiveMinutesAgo);
  }
}

// 定期清理过期缓存
setInterval(() => {
  backgroundService.db.cleanupExpiredCache();
}, 60 * 60 * 1000); // 每小时执行一次

// Service Worker 事件监听
self.addEventListener('activate', (event) => {
  event.waitUntil(clients.claim());
});

self.addEventListener('install', (event) => {
  event.waitUntil(self.skipWaiting());
});

// 初始化流程
let backgroundService = null;
try {
  // 初始化扩展实例并保存到全局变量
  backgroundService = new WeChatAssistantService();
  self.weChatAssistant = backgroundService;
} catch (error) {
  // 静默处理错误
}
