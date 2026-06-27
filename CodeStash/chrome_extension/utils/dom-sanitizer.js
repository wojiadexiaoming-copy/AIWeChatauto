/**
 * DOM安全清理工具
 * 用于防止XSS攻击和不安全的DOM注入
 */

class DOMSanitizer {
  constructor() {
    // 允许的HTML标签白名单
    this.allowedTags = new Set([
      'div', 'span', 'p', 'br', 'strong', 'b', 'em', 'i', 'u', 
      'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'ul', 'ol', 'li',
      'img', 'a', 'blockquote', 'pre', 'code'
    ]);

    // 允许的属性白名单
    this.allowedAttributes = new Set([
      'class', 'id', 'style', 'src', 'alt', 'href', 'title',
      'data-*', 'width', 'height'
    ]);

    // 危险的属性黑名单
    this.dangerousAttributes = new Set([
      'onclick', 'onload', 'onerror', 'onmouseover', 'onmouseout',
      'onfocus', 'onblur', 'onchange', 'onsubmit', 'onreset',
      'javascript:', 'vbscript:', 'data:text/html'
    ]);
  }

  /**
   * 转义HTML特殊字符
   */
  escapeHtml(text) {
    if (typeof text !== 'string') {
      return '';
    }
    
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  /**
   * 清理HTML内容，移除危险元素和属性
   */
  sanitizeHtml(html) {
    if (typeof html !== 'string') {
      return '';
    }

    // 创建临时DOM容器
    const tempDiv = document.createElement('div');
    tempDiv.innerHTML = html;

    // 递归清理所有节点
    this.cleanNode(tempDiv);

    return tempDiv.innerHTML;
  }

  /**
   * 递归清理DOM节点
   */
  cleanNode(node) {
    if (!node) return;

    // 处理元素节点
    if (node.nodeType === Node.ELEMENT_NODE) {
      const tagName = node.tagName.toLowerCase();

      // 如果标签不在白名单中，移除该节点
      if (!this.allowedTags.has(tagName)) {
        node.remove();
        return;
      }

      // 清理属性
      const attributes = Array.from(node.attributes);
      attributes.forEach(attr => {
        const attrName = attr.name.toLowerCase();
        const attrValue = attr.value.toLowerCase();

        // 检查是否为危险属性
        if (this.dangerousAttributes.has(attrName) || 
            attrValue.includes('javascript:') || 
            attrValue.includes('vbscript:') ||
            attrValue.includes('data:text/html')) {
          node.removeAttribute(attr.name);
        }
      });
    }

    // 递归处理子节点
    const children = Array.from(node.childNodes);
    children.forEach(child => this.cleanNode(child));
  }

  /**
   * 安全地设置元素的HTML内容
   */
  safeSetInnerHTML(element, html) {
    if (!element) return;
    
    const cleanHtml = this.sanitizeHtml(html);
    element.innerHTML = cleanHtml;
  }

  /**
   * 安全地设置元素的文本内容
   */
  safeSetTextContent(element, text) {
    if (!element) return;
    
    element.textContent = this.escapeHtml(text);
  }

  /**
   * 创建安全的DOM元素
   */
  createElement(tagName, options = {}) {
    const element = document.createElement(tagName);
    
    // 设置安全的属性
    if (options.className) {
      element.className = this.escapeHtml(options.className);
    }
    
    if (options.id) {
      element.id = this.escapeHtml(options.id);
    }
    
    if (options.textContent) {
      element.textContent = options.textContent;
    }
    
    if (options.innerHTML) {
      this.safeSetInnerHTML(element, options.innerHTML);
    }
    
    return element;
  }
}

// 创建全局实例
window.domSanitizer = new DOMSanitizer();