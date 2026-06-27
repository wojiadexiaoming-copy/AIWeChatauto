// 公众号智能美化助手 - API 配置文件

const API_CONFIG = {
  // 阿里百联API配置 - 硬编码API Key
  alibaba: {
    apiKey: 'sk-your-dashscope-api-key-here', // 请替换为您的实际API Key
    baseUrl: 'https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation',
    models: {
      'qwen-turbo': {
        name: 'Qwen-Turbo',
        description: '通用对话模型，响应速度快',
        maxTokens: 2000
      },
      'qwen-plus': {
        name: 'Qwen-Plus',
        description: '增强版模型，理解能力更强',
        maxTokens: 4000
      },
      'qwen-max': {
        name: 'Qwen-Max',
        description: '最强模型，适合复杂任务',
        maxTokens: 8000
      }
    },
    defaultModel: 'qwen-turbo',
    headers: {
      'Content-Type': 'application/json',
      'X-DashScope-SSE': 'disable'
    },
    parameters: {
      temperature: 0.7,
      top_p: 0.9,
      repetition_penalty: 1.1
    }
  },

  // 预设优化提示模板
  prompts: {
    general: {
      name: '通用优化',
      template: '请优化以下公众号文章内容，保持原意的同时提升可读性和吸引力，让表达更加清晰流畅：',
      description: '适用于大部分内容的通用优化'
    },
    engaging: {
      name: '提升吸引力',
      template: '请将以下内容改写得更加引人入胜和吸引人，增加情感色彩和感染力，但保持信息准确性：',
      description: '增强内容的吸引力和感染力'
    },
    professional: {
      name: '专业化表达',
      template: '请将以下内容调整为更加专业严谨的表达方式，使用更准确的术语和正式的语言风格：',
      description: '适合商务、学术等正式场合'
    },
    friendly: {
      name: '亲和力增强',
      template: '请将以下内容改写得更加亲切友好，使用温暖的语调和贴近读者的表达方式：',
      description: '让内容更加亲民易懂'
    },
    concise: {
      name: '精简表达',
      template: '请将以下内容精简表达，去掉冗余信息，保留核心要点，使表达更加简洁有力：',
      description: '简化表达，突出重点'
    },
    detailed: {
      name: '详细展开',
      template: '请将以下内容进行详细展开，增加具体的例子、解释和细节，使内容更加丰富完整：',
      description: '丰富内容，增加详细信息'
    }
  },

  // 错误处理配置
  errorHandling: {
    retryTimes: 3,
    retryInterval: 1000,
    timeoutDuration: 30000,
    errorMessages: {
      'network_error': '网络连接失败，请检查网络状态',
      'api_key_invalid': 'API Key 无效，请检查配置',
      'quota_exceeded': 'API 调用次数已达上限',
      'content_too_long': '内容过长，请分段处理',
      'unknown_error': '未知错误，请稍后重试'
    }
  },

  // 内容处理配置
  content: {
    maxLength: 5000, // 最大处理长度
    minLength: 10,   // 最小处理长度
    preserveFormatting: true, // 保留格式
    encoding: 'utf-8'
  },

  // 用户界面配置
  ui: {
    theme: {
      primary: '#667eea',
      secondary: '#764ba2',
      success: '#28a745',
      warning: '#ffc107',
      danger: '#dc3545',
      info: '#17a2b8'
    },
    animations: {
      duration: 300,
      easing: 'ease-out'
    }
  },

  // 存储配置
  storage: {
    keys: {
      apiKey: 'wechat_assistant_api_key',
      config: 'wechat_assistant_config',
      preferences: 'wechat_assistant_preferences'
    }
  },

  // 安全配置
  security: {
    encryptApiKey: false, // 是否加密存储API Key
    validateContent: true, // 是否验证内容安全性
    sanitizeHtml: true,   // 是否清理HTML
    allowedDomains: [
      'mp.weixin.qq.com',
      'dashscope.aliyuncs.com'
    ]
  },

};

// 配置验证函数
function validateApiKey(apiKey) {
  return apiKey && typeof apiKey === 'string' && apiKey.length > 20;
}

function validateModel(model) {
  return API_CONFIG.alibaba.models.hasOwnProperty(model);
}

function validateContent(content) {
  if (!content || typeof content !== 'string') {
    return { valid: false, error: 'content_empty' };
  }
  
  if (content.length < API_CONFIG.content.minLength) {
    return { valid: false, error: 'content_too_short' };
  }
  
  if (content.length > API_CONFIG.content.maxLength) {
    return { valid: false, error: 'content_too_long' };
  }
  
  return { valid: true };
}

// 导出配置（在浏览器环境中使用全局变量）
if (typeof module !== 'undefined' && module.exports) {
  module.exports = { API_CONFIG, validateApiKey, validateModel, validateContent };
} else {
  window.API_CONFIG = API_CONFIG;
  window.validateApiKey = validateApiKey;
  window.validateModel = validateModel;
  window.validateContent = validateContent;
}