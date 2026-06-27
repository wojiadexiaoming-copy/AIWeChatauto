// 公众号智能美化助手 - IndexedDB 数据库工具类
// 提供大容量的本地存储功能

class WeChatAssistantDB {
  constructor() {
    this.dbName = 'WeChatAssistantDB';
    this.version = 1;
    this.db = null;
    
    // 数据表配置
    this.stores = {
      config: 'config',
      history: 'history',
      cache: 'cache'
    };
  }

  // 初始化数据库
  async init() {
    return new Promise((resolve, reject) => {
      const request = indexedDB.open(this.dbName, this.version);

      request.onerror = () => {
        reject(request.error);
      };

      request.onsuccess = () => {
        this.db = request.result;
        resolve(this.db);
      };

      request.onupgradeneeded = (event) => {
        const db = event.target.result;

        // 创建配置表
        if (!db.objectStoreNames.contains(this.stores.config)) {
          const configStore = db.createObjectStore(this.stores.config, {
            keyPath: 'key'
          });
        }

        // 创建历史记录表
        if (!db.objectStoreNames.contains(this.stores.history)) {
          const historyStore = db.createObjectStore(this.stores.history, {
            keyPath: 'id',
            autoIncrement: true
          });
          historyStore.createIndex('timestamp', 'timestamp', { unique: false });
        }

        // 创建缓存表
        if (!db.objectStoreNames.contains(this.stores.cache)) {
          const cacheStore = db.createObjectStore(this.stores.cache, {
            keyPath: 'key'
          });
          cacheStore.createIndex('expiry', 'expiry', { unique: false });
        }
      };
    });
  }

  // 确保数据库连接
  async ensureConnection() {
    if (!this.db) {
      await this.init();
    }
    return this.db;
  }

  // 保存配置
  async saveConfig(configData) {
    try {
      await this.ensureConnection();
      
      const transaction = this.db.transaction([this.stores.config], 'readwrite');
      const store = transaction.objectStore(this.stores.config);
      
      // 将配置对象转换为键值对存储
      const promises = Object.entries(configData).map(([key, value]) => {
        return new Promise((resolve, reject) => {
          const request = store.put({
            key: key,
            value: value,
            timestamp: Date.now()
          });
          
          request.onsuccess = () => resolve();
          request.onerror = () => reject(request.error);
        });
      });

      await Promise.all(promises);
      return { success: true };
    } catch (error) {
      return { success: false, error: error.message };
    }
  }

  // 获取配置
  async getConfig() {
    try {
      await this.ensureConnection();
      
      const transaction = this.db.transaction([this.stores.config], 'readonly');
      const store = transaction.objectStore(this.stores.config);
      
      return new Promise((resolve, reject) => {
        const request = store.getAll();
        
        request.onsuccess = () => {
          const configs = {};
          request.result.forEach(item => {
            configs[item.key] = item.value;
          });
          
          // 设置默认值
          const defaultConfig = {
            isEnabled: true,
            customPrompt: ''
          };
          
          resolve({ ...defaultConfig, ...configs });
        };
        
        request.onerror = () => reject(request.error);
      });
    } catch (error) {
      return {};
    }
  }

  // 保存历史记录
  async saveHistory(historyItem) {
    try {
      await this.ensureConnection();
      
      const transaction = this.db.transaction([this.stores.history], 'readwrite');
      const store = transaction.objectStore(this.stores.history);
      
      const item = {
        ...historyItem,
        timestamp: Date.now()
      };
      
      return new Promise((resolve, reject) => {
        const request = store.add(item);
        
        request.onsuccess = () => {
          // 清理旧记录，保持最新100条
          this.cleanupHistory();
          resolve(request.result);
        };
        
        request.onerror = () => reject(request.error);
      });
    } catch (error) {
      throw error;
    }
  }

  // 获取历史记录
  async getHistory(limit = 50) {
    try {
      await this.ensureConnection();
      
      const transaction = this.db.transaction([this.stores.history], 'readonly');
      const store = transaction.objectStore(this.stores.history);
      const index = store.index('timestamp');
      
      return new Promise((resolve, reject) => {
        const request = index.openCursor(null, 'prev'); // 按时间倒序
        const results = [];
        
        request.onsuccess = (event) => {
          const cursor = event.target.result;
          if (cursor && results.length < limit) {
            results.push(cursor.value);
            cursor.continue();
          } else {
            resolve(results);
          }
        };
        
        request.onerror = () => reject(request.error);
      });
    } catch (error) {
      return [];
    }
  }

  // 清空历史记录
  async clearHistory() {
    try {
      await this.ensureConnection();
      
      const transaction = this.db.transaction([this.stores.history], 'readwrite');
      const store = transaction.objectStore(this.stores.history);
      
      return new Promise((resolve, reject) => {
        const request = store.clear();
        
        request.onsuccess = () => {
          resolve({ success: true });
        };
        
        request.onerror = () => reject(request.error);
      });
    } catch (error) {
      return { success: false, error: error.message };
    }
  }

  // 清理旧的历史记录
  async cleanupHistory(keepCount = 100) {
    try {
      await this.ensureConnection();
      
      const transaction = this.db.transaction([this.stores.history], 'readwrite');
      const store = transaction.objectStore(this.stores.history);
      const index = store.index('timestamp');
      
      return new Promise((resolve, reject) => {
        const request = index.openCursor(null, 'prev');
        let count = 0;
        
        request.onsuccess = (event) => {
          const cursor = event.target.result;
          if (cursor) {
            count++;
            if (count > keepCount) {
              cursor.delete();
            }
            cursor.continue();
          } else {
            resolve();
          }
        };
        
        request.onerror = () => reject(request.error);
      });
    } catch (error) {
      // 静默处理错误
    }
  }

  // 保存缓存数据
  async setCache(key, value, expiryMinutes = 60) {
    try {
      await this.ensureConnection();
      
      const transaction = this.db.transaction([this.stores.cache], 'readwrite');
      const store = transaction.objectStore(this.stores.cache);
      
      const item = {
        key: key,
        value: value,
        expiry: Date.now() + (expiryMinutes * 60 * 1000),
        timestamp: Date.now()
      };
      
      return new Promise((resolve, reject) => {
        const request = store.put(item);
        
        request.onsuccess = () => resolve();
        request.onerror = () => reject(request.error);
      });
    } catch (error) {
      // 静默处理错误
    }
  }

  // 获取缓存数据
  async getCache(key) {
    try {
      await this.ensureConnection();
      
      const transaction = this.db.transaction([this.stores.cache], 'readonly');
      const store = transaction.objectStore(this.stores.cache);
      
      return new Promise((resolve, reject) => {
        const request = store.get(key);
        
        request.onsuccess = () => {
          const item = request.result;
          if (item && item.expiry > Date.now()) {
            resolve(item.value);
          } else {
            if (item) {
              // 清理过期数据
              this.deleteCache(key);
            }
            resolve(null);
          }
        };
        
        request.onerror = () => reject(request.error);
      });
    } catch (error) {
      return null;
    }
  }

  // 删除缓存
  async deleteCache(key) {
    try {
      await this.ensureConnection();
      
      const transaction = this.db.transaction([this.stores.cache], 'readwrite');
      const store = transaction.objectStore(this.stores.cache);
      
      return new Promise((resolve, reject) => {
        const request = store.delete(key);
        
        request.onsuccess = () => resolve();
        request.onerror = () => reject(request.error);
      });
    } catch (error) {
      // 静默处理错误
    }
  }

  // 获取数据库统计信息
  async getStats() {
    try {
      await this.ensureConnection();
      
      const stats = {};
      
      // 获取各表的记录数
      for (const [name, storeName] of Object.entries(this.stores)) {
        const transaction = this.db.transaction([storeName], 'readonly');
        const store = transaction.objectStore(storeName);
        
        stats[name] = await new Promise((resolve, reject) => {
          const request = store.count();
          request.onsuccess = () => resolve(request.result);
          request.onerror = () => reject(request.error);
        });
      }
      
      return stats;
    } catch (error) {
      return {};
    }
  }
}

// 创建全局实例
const dbInstance = new WeChatAssistantDB();

// 导出单例
if (typeof module !== 'undefined' && module.exports) {
  module.exports = dbInstance;
} else {
  window.WeChatAssistantDB = dbInstance;
}