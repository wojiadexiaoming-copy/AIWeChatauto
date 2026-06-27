/**
 * 简单的Base64加密解密工具
 * 用于保护云函数URL
 */

class EncryptionUtils {
  /**
   * 加密字符串
   * @param {string} text - 要加密的文本
   * @returns {string} - 加密后的Base64字符串
   */
  static encrypt(text) {
    try {
      // 简单的字符偏移加密 + Base64编码
      let encrypted = '';
      for (let i = 0; i < text.length; i++) {
        const char = text.charCodeAt(i);
        // 使用简单的XOR加密，密钥为字符位置
        encrypted += String.fromCharCode(char ^ (i % 256));
      }
      // 使用更安全的Base64编码方式
      return btoa(unescape(encodeURIComponent(encrypted)));
    } catch (error) {
      // 静默处理错误
      return text;
    }
  }

  /**
   * 解密字符串
   * @param {string} encryptedText - 加密的Base64字符串
   * @returns {string} - 解密后的原始文本
   */
  static decrypt(encryptedText) {
    try {
      // Base64解码 + 字符偏移解密
      const decoded = decodeURIComponent(escape(atob(encryptedText)));
      let decrypted = '';
      for (let i = 0; i < decoded.length; i++) {
        const char = decoded.charCodeAt(i);
        // 使用相同的XOR解密
        decrypted += String.fromCharCode(char ^ (i % 256));
      }
      return decrypted;
    } catch (error) {
      // 静默处理错误
      return encryptedText;
    }
  }

  /**
   * 获取加密的云函数URL
   * @param {string} functionName - 云函数名称
   * @returns {string} - 解密后的完整URL
   */
  static getCloudFunctionUrl(functionName) {
    const baseUrl = 'https://env-00jxtxx9y58k.dev-hz.cloudbasefunction.cn';
    const fullUrl = `${baseUrl}/${functionName}`;
    
    // 这里返回原始URL，实际使用时应该使用加密版本
    return fullUrl;
  }

  /**
   * 预定义的加密URL常量（使用Base64编码）
   */
  static get ENCRYPTED_URLS() {
    return {
      // 模板获取云函数
      GET_Edge_tenplates: 'aHR0cHM6Ly9lbnYtMDBqeHR4eDl5NThrLmRldi1oei5jbG91ZGJhc2VmdW5jdGlvbi5jbi9HRVRfRWRnZV90ZW5wbGF0ZXM=',
      // 密钥验证云函数  
      GET_Edge_key: 'aHR0cHM6Ly9lbnYtMDBqeHR4eDl5NThrLmRldi1oei5jbG91ZGJhc2VmdW5jdGlvbi5jbi9HRVRfRWRnZV9rZXk='
    };
  }

  /**
   * 获取解密后的云函数URL
   * @param {string} functionName - 云函数名称
   * @returns {string} - 解密后的URL
   */
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

// 导出供其他模块使用
if (typeof module !== 'undefined' && module.exports) {
  module.exports = EncryptionUtils;
} else if (typeof window !== 'undefined') {
  window.EncryptionUtils = EncryptionUtils;
}
