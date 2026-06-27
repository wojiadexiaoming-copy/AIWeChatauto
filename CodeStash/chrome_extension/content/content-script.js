// 公众号智能美化助手 - 内容监听脚本
// 监听公众号编辑器内容变化，提供内容获取和替换功能

class WeChatContentMonitor {
  constructor() {
    // 根据编辑器.md文件中的实际结构更新选择器
    this.targetSelector = 'div.ProseMirror[contenteditable="true"]';
    this.observer = null;
    this.lastContent = '';
    this.lastWordCount = 0;
    this.wordCountObserver = null;
    this.debounceTimer = null;
    this.wordCountDebounceTimer = null;
    this.isProcessing = false;
    this.isPreviewPanelOpen = false;
    
    // 添加内容哈希缓存，提高内容比较的稳定性
    this.lastContentHash = '';

    // 自动发布相关的状态标志
    this.isAutoFilling = false;
    this.isSaving = false;
    
    this.init();
  }

  init() {
    // 等待页面加载完成
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', () => {
        this.startMonitoring();
      });
    } else {
      this.startMonitoring();
    }

    // 监听来自侧边栏的消息
    if (typeof chrome !== 'undefined' && chrome.runtime && chrome.runtime.onMessage) {
      chrome.runtime.onMessage.addListener(this.onMessage.bind(this));
    } else if (typeof browser !== 'undefined' && browser.runtime && browser.runtime.onMessage) {
      browser.runtime.onMessage.addListener(this.onMessage.bind(this));
    }
    
    // 添加页面可见性变化监听
    document.addEventListener('visibilitychange', () => {
      if (!document.hidden) {
        // 页面变为可见时检查一次内容
        setTimeout(() => this.handleContentChange(), 100);
      }
    });
    
    // 添加Firefox特定的页面激活监听
    if (typeof chrome !== 'undefined' && chrome.tabs && chrome.tabs.onActivated) {
      chrome.tabs.onActivated.addListener(() => {
        setTimeout(() => this.handleContentChange(), 200);
      });
    }

    // 启动自动发布状态机轮询
    this.startTaskPolling();
  }

  // 启动自动发布状态机轮询
  startTaskPolling() {
    if (window !== window.top) return; // 仅在顶层窗口运行状态机
    
    const poll = async () => {
      try {
        const response = await fetch('http://127.0.0.1:5000/api/extension/task');
        if (response.ok) {
          const data = await response.json();
          if (data.success && data.task) {
            await this.handleTaskStep(data.task);
          }
        }
      } catch (err) {
        // 静默处理
      }
      setTimeout(poll, 3000);
    };
    poll();
  }

  // 根据后端任务步骤执行相应动作
  async handleTaskStep(task) {
    const url = window.location.href;
    const urlObj = new URL(url);
    const token = urlObj.searchParams.get('token');
    const isEditorPage = url.includes('t=media/appmsg_edit');

    if (task.status === 'waiting_login') {
      if (token) {
        // 已登录，跳转到编辑器
        await this.updateTaskStatus('open_editor');
        if (!isEditorPage) {
          window.location.href = `https://mp.weixin.qq.com/cgi-bin/appmsg?t=media/appmsg_edit&action=edit&type=77&enable_comment=1&token=${token}&lang=zh_CN`;
        }
      }
    }
    else if (task.status === 'open_editor') {
      if (isEditorPage) {
        // 已进入编辑器，切为 filling_content 开始填正文
        await this.updateTaskStatus('filling_content');
      } else if (token) {
        // 没在编辑器但有token，跳转去编辑器
        window.location.href = `https://mp.weixin.qq.com/cgi-bin/appmsg?t=media/appmsg_edit&action=edit&type=77&enable_comment=1&token=${token}&lang=zh_CN`;
      }
    }
    else if (task.status === 'filling_content') {
      if (isEditorPage) {
        await this.fillEditorContent(task);
      }
    }
    else if (task.status === 'clicking_save') {
      if (isEditorPage) {
        await this.clickSaveButton();
      }
    }
  }

  // 向后端报告当前状态进度
  async updateTaskStatus(status, errorMessage = '') {
    try {
      await fetch('http://127.0.0.1:5000/api/extension/task/progress', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: status, error_message: errorMessage })
      });
    } catch (e) {
      console.error('[自动发布] updateTaskStatus 错误:', e);
    }
  }

  // 自动填充编辑器标题和正文
  async fillEditorContent(task) {
    if (this.isAutoFilling) return; // 避免重复填充
    this.isAutoFilling = true;
    
    try {
      const titleInput = document.getElementById('title') || document.querySelector('.js_title') || document.querySelector('#js_title');
      const authorInput = document.getElementById('author') || document.querySelector('.js_author') || document.querySelector('#js_author');
      const editor = document.querySelector('div.ProseMirror[contenteditable="true"]') || document.querySelector('.ProseMirror');
      
      if (!titleInput || !editor) {
        console.log('[自动发布] 标题框或编辑器未加载，等待中...');
        this.isAutoFilling = false;
        return; // 下次轮询再试
      }
      
      console.log('[自动发布] 开始自动填写内容...');
      
      // 1. 填充标题
      titleInput.value = task.title;
      titleInput.dispatchEvent(new Event('input', { bubbles: true }));
      titleInput.dispatchEvent(new Event('change', { bubbles: true }));
      
      // 2. 填充作者（如有）
      if (authorInput && task.author) {
        authorInput.value = task.author;
        authorInput.dispatchEvent(new Event('input', { bubbles: true }));
        authorInput.dispatchEvent(new Event('change', { bubbles: true }));
      }
      
      // 3. 填充编辑区
      editor.focus();
      // 选择全部并删除旧内容
      document.execCommand('selectAll', false, null);
      document.execCommand('delete', false, null);
      // 使用 insertHTML 注入
      document.execCommand('insertHTML', false, task.content);
      
      // 兜底方案：如果还是空的，直接修改 innerHTML
      if (editor.innerHTML.trim() === '') {
        editor.innerHTML = task.content;
      }
      
      editor.dispatchEvent(new Event('input', { bubbles: true }));
      editor.dispatchEvent(new Event('change', { bubbles: true }));
      editor.blur();
      
      console.log('[自动发布] 填写完成，推进状态至 clicking_save');
      await this.updateTaskStatus('clicking_save');
    } catch (e) {
      console.error('[自动发布] 填充内容失败:', e);
      await this.updateTaskStatus('error', '填充内容出错: ' + e.message);
    } finally {
      this.isAutoFilling = false;
    }
  }

  // 点击保存草稿按钮
  async clickSaveButton() {
    if (this.isSaving) return;
    this.isSaving = true;
    
    try {
      // 寻找保存按钮
      const buttons = Array.from(document.querySelectorAll('button, a, span.weui-desktop-btn, div.weui-desktop-btn'));
      const saveBtn = buttons.find(btn => {
        const text = btn.textContent.trim();
        return text === '保存' || text === '保存草稿' || text === '保存到草稿';
      }) || document.getElementById('js_save') || document.getElementById('js_temp_save');
      
      if (!saveBtn) {
        console.log('[自动发布] 未找到保存按钮，稍后再试...');
        this.isSaving = false;
        return;
      }
      
      console.log('[自动发布] 自动点击保存/保存草稿按钮:', saveBtn);
      saveBtn.click();
      
      // 延时等待 3 秒，确保公众号发起保存并完成后再标记为已完成
      setTimeout(async () => {
        console.log('[自动发布] 已点击保存按钮并等待3秒，标记任务为 completed');
        await this.updateTaskStatus('completed');
        this.isSaving = false;
      }, 3000);
    } catch (e) {
      console.error('[自动发布] 点击保存按钮出错:', e);
      await this.updateTaskStatus('error', '点击保存按钮失败: ' + e.message);
      this.isSaving = false;
    }
  }

  // 开始监听编辑器
  startMonitoring() {
    this.findAndObserveEditor();
    this.startWordCountMonitoring();
    
    // 定期检查编辑器是否存在（处理动态加载的情况）
    setInterval(() => {
      if (!this.observer || !document.querySelector(this.targetSelector)) {
        this.findAndObserveEditor();
      }
      // 同时检查字数监控器
      if (!this.wordCountObserver || !document.querySelector('#word_count_container .js_word_count')) {
        this.startWordCountMonitoring();
      }
    }, 3000);
  }

  // 查找并观察编辑器
  findAndObserveEditor() {
    // 更新选择器以匹配实际的元素结构
    const selectors = [
      'div.ProseMirror[contenteditable="true"]',
      '.ProseMirror[contenteditable="true"]',
      'div.ProseMirror',
      '.ProseMirror',
      '.view.rich_media_content .ProseMirror',
      '.mock-iframe-body .ProseMirror'
    ];
    
    let editor = null;
    let usedSelector = '';
    
    for (const selector of selectors) {
      editor = document.querySelector(selector);
      usedSelector = selector;
      if (editor) {
        break;
      }
    }
    
    this.targetSelector = usedSelector;
    
    if (editor) {
      if (!this.observer) {
        this.observeEditor(editor);
        this.addUI();
      }
    }
  }

  // 监听编辑器变化
  observeEditor(editor) {
    // 创建MutationObserver
    this.observer = new MutationObserver((mutations) => {
      this.debounceContentChange();
    });

    // 配置观察选项
    const config = {
      childList: true,
      subtree: true,
      characterData: true,
      attributes: false
    };

    this.observer.observe(editor, config);

    // 监听输入事件
    editor.addEventListener('input', () => {
      this.debounceContentChange();
    });

    // 监听粘贴事件
    editor.addEventListener('paste', () => {
      setTimeout(() => this.debounceContentChange(), 100);
    });
  }

  // 优化防抖处理内容变化 - 增加防抖时间以提高稳定性
  debounceContentChange() {
    clearTimeout(this.debounceTimer);
    this.debounceTimer = setTimeout(() => {
      this.handleContentChange();
    }, 800);
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

  // 处理内容变化
  handleContentChange() {
    const editor = document.querySelector(this.targetSelector);
    if (!editor) return;

    const currentContent = this.getEditorContent();
    const currentContentHash = this.getContentHash(currentContent);
    
    // 优化内容变化检测 - 使用哈希值比较，避免因空格或换行符等微小变化导致的误判
    // 修复：即使内容为空，也通知侧边栏，但侧边栏需要判断是否真正更新状态
    if (currentContentHash !== this.lastContentHash) {
      this.lastContent = currentContent;
      this.lastContentHash = currentContentHash;
      
      // 通知侧边栏内容已更新
      this.notifySidePanel('CONTENT_UPDATED', {
        content: currentContent
      });
      
      // 内容变化时也触发字数检查（以防字数元素更新延迟）
      setTimeout(() => {
        this.checkWordCountChange();
      }, 300);
    }
  }

  // 获取编辑器内容
  getEditorContent() {
    const editor = document.querySelector(this.targetSelector);
    if (!editor) {
      try {
        const selectedText = window.getSelection() ? window.getSelection().toString().trim() : '';
        if (selectedText) {
          return selectedText.split(/\n+/).map(p => `<p>${p.trim()}</p>`).join('');
        }
      } catch (e) {}
      return '';
    }

    try {
      // 获取富文本内容
      const content = editor.innerHTML || '';
      return content;
    } catch (error) {
      return '';
    }
  }

  // 获取纯文本内容
  getPlainTextContent() {
    const editor = document.querySelector(this.targetSelector);
    if (!editor) {
      try {
        return window.getSelection() ? window.getSelection().toString().trim() : '';
      } catch (e) {
        return '';
      }
    }

    return editor.innerText || editor.textContent || '';
  }

  // 获取完整内容结构（包含文本和图片按顺序）
  getStructuredContent() {
    const editor = document.querySelector(this.targetSelector);
    if (!editor) {
      let selectedText = '';
      try {
        selectedText = window.getSelection() ? window.getSelection().toString().trim() : '';
      } catch (e) {}

      if (selectedText) {
        const paragraphs = selectedText.split(/\n+/).map(p => p.trim()).filter(Boolean);
        const structured = paragraphs.map((p, idx) => ({
          type: 'text',
          content: p,
          position: idx
        }));
        const html = paragraphs.map(p => `<p>${p}</p>`).join('');
        return {
          html: html,
          text: selectedText,
          structured: structured
        };
      }

      return {
        html: '',
        text: '',
        structured: []
      };
    }

    try {
      const htmlContent = editor.innerHTML || '';
      const textContent = editor.innerText || editor.textContent || '';
      
      // 解析内容结构，按顺序提取文本和图片
      const structured = this.parseContentStructure(editor);
      
      return {
        html: htmlContent,
        text: textContent,
        structured: structured
      };
    } catch (error) {
      return {
        html: '',
        text: '',
        structured: []
      };
    }
  }

  // 解析内容结构，按顺序提取文本和图片
  parseContentStructure(editor) {
    const structured = [];
    const processedElements = new Set(); // 用于跟踪已处理的元素，避免重复
    
    try {
      // 遍历编辑器的所有子节点，按顺序处理
      const walker = document.createTreeWalker(
        editor,
        NodeFilter.SHOW_ELEMENT | NodeFilter.SHOW_TEXT,
        {
          acceptNode: (node) => {
            // 接受文本节点和特定元素节点
            if (node.nodeType === Node.TEXT_NODE) {
              return node.textContent.trim() ? NodeFilter.FILTER_ACCEPT : NodeFilter.FILTER_REJECT;
            }
            if (node.nodeType === Node.ELEMENT_NODE) {
              // 接受图片、视频、段落、section等有意义的元素
              const tagName = node.tagName.toLowerCase();
              if (tagName === 'img' || tagName === 'iframe' || tagName === 'p' || tagName === 'section' || tagName === 'div') {
                return NodeFilter.FILTER_ACCEPT;
              }
            }
            return NodeFilter.FILTER_SKIP;
          }
        }
      );

      let node;
      while (node = walker.nextNode()) {
        if (node.nodeType === Node.TEXT_NODE) {
          // 文本节点
          const text = node.textContent.trim();
          if (text) {
            structured.push({
              type: 'text',
              content: text,
              position: structured.length
            });
          }
        } else if (node.nodeType === Node.ELEMENT_NODE) {
          const tagName = node.tagName.toLowerCase();
          
          if (tagName === 'img') {
            // 图片元素 - 检查是否已处理过
            if (!processedElements.has(node)) {
              const imgData = this.extractImageData(node);
              if (imgData) {
                structured.push({
                  type: 'image',
                  content: imgData,
                  position: structured.length
                });
                processedElements.add(node); // 标记为已处理
              }
            }
          } else if (tagName === 'iframe') {
            // 视频元素 - 检查是否已处理过
            if (!processedElements.has(node)) {
              const videoData = this.extractVideoData(node);
              if (videoData) {
                structured.push({
                  type: 'video',
                  content: videoData,
                  position: structured.length
                });
                processedElements.add(node); // 标记为已处理
              }
            }
          } else if (tagName === 'p' || tagName === 'section' || tagName === 'div') {
            // 检查容器元素中是否包含图片（排除已处理的）
            const images = node.querySelectorAll('img');
            const containerImageUrls = new Set(); // 当前容器内的图片URL集合
            
            if (images.length > 0) {
              images.forEach(img => {
                if (!processedElements.has(img)) {
                  const imgData = this.extractImageData(img);
                  if (imgData) {
                    const imageUrl = imgData.url;
                    // 检查当前容器内是否已有相同URL的图片
                    if (!containerImageUrls.has(imageUrl)) {
                      structured.push({
                        type: 'image',
                        content: imgData,
                        position: structured.length
                      });
                      processedElements.add(img); // 标记为已处理
                      containerImageUrls.add(imageUrl); // 添加到容器URL集合
                    }
                  }
                }
              });
            }
            
            // 检查容器元素中是否包含视频（排除已处理的）
            const videos = node.querySelectorAll('iframe[data-mpvid], .videoWrapper iframe, iframe[src*="video"]');
            const containerVideoUrls = new Set(); // 当前容器内的视频URL集合
            
            if (videos.length > 0) {
              videos.forEach(video => {
                if (!processedElements.has(video)) {
                  const videoData = this.extractVideoData(video);
                  if (videoData) {
                    const videoUrl = videoData.url;
                    // 检查当前容器内是否已有相同URL的视频
                    if (!containerVideoUrls.has(videoUrl)) {
                      structured.push({
                        type: 'video',
                        content: videoData,
                        position: structured.length
                      });
                      processedElements.add(video); // 标记为已处理
                      containerVideoUrls.add(videoUrl); // 添加到容器URL集合
                    }
                  }
                }
              });
            }
            
            // 提取容器中的文本（排除图片、视频元素）
            const textContent = this.extractTextFromElement(node);
            if (textContent) {
              structured.push({
                type: 'text',
                content: textContent,
                position: structured.length
              });
            }
          }
        }
      }
    } catch (error) {
      // 静默处理错误
    }
    
    return structured;
  }

  // 提取图片数据
  extractImageData(imgElement) {
    try {
      const src = imgElement.src || imgElement.getAttribute('src');
      const dataSrc = imgElement.getAttribute('data-src');
      const alt = imgElement.alt || '';
      const className = imgElement.className || '';
      const style = imgElement.style.cssText || '';
      
      // 检查是否为微信公众号规范的图片
      if (!this.isWeChatImage(src, dataSrc, imgElement)) {
        return null; // 不是微信规范的图片，不计入统计
      }
      
      // 获取图片的完整HTML
      const outerHTML = imgElement.outerHTML;
      
      const imageData = {
        src: src,
        dataSrc: dataSrc,
        alt: alt,
        className: className,
        style: style,
        element: outerHTML,
        url: dataSrc || src // 优先使用data-src
      };
      return imageData;
    } catch (error) {
      return null;
    }
  }

  // 提取视频数据
  extractVideoData(videoElement) {
    try {
      const src = videoElement.src || videoElement.getAttribute('src');
      const dataMpvid = videoElement.getAttribute('data-mpvid');
      const dataVidtype = videoElement.getAttribute('data-vidtype');
      const dataCover = videoElement.getAttribute('data-cover');
      const className = videoElement.className || '';
      const style = videoElement.style.cssText || '';
      const width = videoElement.width || videoElement.getAttribute('width');
      const height = videoElement.height || videoElement.getAttribute('height');
      
      // 检查是否为微信公众号规范的视频
      if (!this.isWeChatVideo(src, dataMpvid, videoElement)) {
        return null; // 不是微信规范的视频，不计入统计
      }
      
      // 获取视频的完整HTML（可能需要获取父容器）
      let outerHTML = videoElement.outerHTML;
      
      // 如果视频在videoWrapper容器中，获取完整的容器HTML
      const videoWrapper = videoElement.closest('.videoWrapper');
      if (videoWrapper) {
        outerHTML = videoWrapper.outerHTML;
      } else {
        // 检查是否在section容器中
        const sectionWrapper = videoElement.closest('section[nodeleaf]');
        if (sectionWrapper) {
          outerHTML = sectionWrapper.outerHTML;
        }
      }
      
      const videoData = {
        src: src,
        mpvid: dataMpvid,
        vidtype: dataVidtype,
        cover: dataCover ? decodeURIComponent(dataCover) : '',
        className: className,
        style: style,
        width: width,
        height: height,
        element: outerHTML,
        url: src // 视频源地址
      };
      return videoData;
    } catch (error) {
      return null;
    }
  }

  // 从元素中提取纯文本（排除图片、视频等子元素）
  extractTextFromElement(element) {
    try {
      // 克隆元素以避免修改原始DOM
      const clonedElement = element.cloneNode(true);
      
      // 移除所有图片、视频和其他非文本元素
      const nonTextElements = clonedElement.querySelectorAll('img, iframe, br, hr, .videoWrapper');
      nonTextElements.forEach(el => el.remove());
      
      // 获取纯文本内容
      const text = clonedElement.textContent || clonedElement.innerText || '';
      return text.trim();
    } catch (error) {
      return '';
    }
  }

  // 检查是否为微信公众号规范的图片
  isWeChatImage(src, dataSrc, imgElement) {
    try {
      // 检查图片是否具有微信公众号特征
      const finalUrl = dataSrc || src || '';
      
      // 1. 必须是微信域名的图片
      const isWeChatDomain = finalUrl.includes('mmbiz.qpic.cn') || 
                            finalUrl.includes('mmecoa.qpic.cn') || 
                            finalUrl.includes('mmbiz.qlogo.cn');
      
      // 2. 必须具有微信公众号的CSS类名
      const hasWeChatClass = imgElement.classList.contains('rich_pages') || 
                           imgElement.classList.contains('wxw-img') ||
                           imgElement.classList.contains('js_insertlocalimg');
      
      // 3. 检查是否在微信编辑器容器中
      const isInEditor = imgElement.closest('.rich_media_content') || 
                        imgElement.closest('[contenteditable="true"]') ||
                        imgElement.closest('.ProseMirror') ||
                        imgElement.closest('.mock-iframe-body');
      
      // 只有同时满足这些条件的图片才认为是微信公众号的正式图片
      const isWeChatImg = isWeChatDomain && (hasWeChatClass || isInEditor);
      
      return isWeChatImg;
    } catch (error) {
      return false;
    }
  }

  // 检查是否为微信公众号规范的视频
  isWeChatVideo(src, dataMpvid, videoElement) {
    try {
      // 1. 必须具有微信视频ID
      const hasValidMpvid = dataMpvid && dataMpvid.startsWith('wxv_');
      
      // 2. 必须是微信的视频模板地址
      const isWeChatVideoSrc = src && (src.includes('/cgi-bin/readtemplate') && src.includes('video_tmpl'));
      
      // 3. 必须具有微信视频的CSS类名
      const hasWeChatVideoClass = videoElement.classList.contains('video_iframe') || 
                                 videoElement.classList.contains('wx_video_iframe') || 
                                 videoElement.classList.contains('rich_pages');
      
      // 4. 必须在videoWrapper或section容器中
      const isInWrapper = videoElement.closest('.videoWrapper') || 
                         videoElement.closest('section[nodeleaf]');
      
      // 5. 检查是否在微信编辑器容器中
      const isInEditor = videoElement.closest('.rich_media_content') || 
                        videoElement.closest('[contenteditable="true"]') ||
                        videoElement.closest('.ProseMirror') ||
                        videoElement.closest('.mock-iframe-body');
      
      // 只有同时满足这些条件的视频才认为是微信公众号的正式视频
      const isWeChatVideo = (isWeChatVideoSrc || hasValidMpvid) && 
                           (hasWeChatVideoClass || isInWrapper || isInEditor);
      
      return isWeChatVideo;
    } catch (error) {
      return false;
    }
  }

  // 启动字数监控
  startWordCountMonitoring() {
    const wordCountElement = document.querySelector('#word_count_container .js_word_count');
    if (!wordCountElement || this.wordCountObserver) {
      return;
    }

    // 创建字数观察器
    this.wordCountObserver = new MutationObserver((mutations) => {
      this.debounceWordCountChange();
    });

    // 监控字数元素的文本变化
    this.wordCountObserver.observe(wordCountElement, {
      childList: true,
      subtree: true,
      characterData: true
    });

    // 初始化字数
    this.checkWordCountChange();
  }

  // 优化防抖处理字数变化 - 增加防抖时间以提高稳定性
  debounceWordCountChange() {
    clearTimeout(this.wordCountDebounceTimer);
    this.wordCountDebounceTimer = setTimeout(() => {
      this.checkWordCountChange();
    }, 500);
  }

  // 检查字数变化
  checkWordCountChange() {
    const currentWordCount = this.getCurrentWordCount();
    
    // 修复：只有当字数真正发生变化时才通知侧边栏
    if (currentWordCount !== this.lastWordCount) {
      this.lastWordCount = currentWordCount;
      
      // 通知侧边栏字数已更新
      this.notifySidePanel('WORD_COUNT_UPDATED', {
        count: currentWordCount
      });
    }
  }

  // 获取当前字数
  getCurrentWordCount() {
    try {
      let count = 0;
      const wc = document.querySelector('#word_count_container .js_word_count');
      if (wc && wc.textContent) {
        const parsed = parseInt(wc.textContent.replace(/\D+/g, ''), 10);
        if (!isNaN(parsed)) count = parsed;
      }

      if (!count) {
        // 回退方案：从编辑器内容计算（排除换行、空格、全角空格）
        const text = this.getPlainTextContent();
        const plain = (text || '').replace(/\s|\u3000/g, '');
        count = plain.length;
      }

      return count;
    } catch (error) {
      return 0;
    }
  }

  // 替换编辑器内容
  replaceContent(newContent) {
    const editor = document.querySelector(this.targetSelector);
    if (!editor) {
      throw new Error('编辑器不存在');
    }

    try {
      this.isProcessing = true;
      
      // 暂停观察器
      if (this.observer) {
        this.observer.disconnect();
      }

      // 保存当前光标位置
      const selection = window.getSelection();
      const range = selection.rangeCount > 0 ? selection.getRangeAt(0) : null;

      // 替换内容
      editor.innerHTML = newContent;

      // 触发输入事件通知编辑器
      const event = new Event('input', { bubbles: true });
      editor.dispatchEvent(event);

      // 重新启动观察器
      setTimeout(() => {
        this.observeEditor(editor);
        this.isProcessing = false;
        this.lastContent = newContent;
      }, 100);

      return true;
    } catch (error) {
      this.isProcessing = false;
      return false;
    }
  }

  // 消息处理
  onMessage(message, sender, sendResponse) {
    try {
      switch (message.type) {
        case 'PING':
          sendResponse({
            success: true,
            message: 'PONG',
            timestamp: Date.now()
          });
          return true;

        case 'GET_CONTENT':
          const contentData = {
            html: this.getEditorContent(),
            text: this.getPlainTextContent()
          };
          sendResponse({
            success: true,
            data: contentData
          });
          return true;

        case 'GET_STRUCTURED_CONTENT':
          // 获取包含文本和图片的结构化内容
          const structuredData = this.getStructuredContent();
          sendResponse({
            success: true,
            data: structuredData
          });
          return true;

        case 'REPLACE_CONTENT':
          const success = this.replaceContent(message.data.content);
          sendResponse({ success });
          return true;

        case 'GET_EDITOR_STATUS':
          const editor = document.querySelector(this.targetSelector);
          const statusData = {
            exists: !!editor,
            isActive: document.activeElement === editor
          };
          sendResponse({
            success: true,
            data: statusData
          });
          return true;

        case 'SHOW_PAGE_PREVIEW':
          
          this.showPagePreviewContent(message.data.templateData);
          sendResponse({ success: true });
          return true;

        case 'CLOSE_PAGE_PREVIEW':
          this.closePagePreviewPanel();
          sendResponse({ success: true });
          return true;

        case 'TOGGLE_PAGE_PREVIEW':
          this.togglePagePreviewPanel();
          sendResponse({ success: true });
          return true;

        case 'DISPLAY_PAGE_PREVIEW_CONTENT':
          
          this.displayPagePreviewContent(message.data.content);
          sendResponse({ success: true });
          return true;

        case 'GET_WORD_COUNT': {
          try {
            const count = this.getCurrentWordCount();
            sendResponse({ success: true, data: { count } });
          } catch (err) {
            sendResponse({ success: false, error: err.message });
          }
          return true;
        }

        case 'SHOW_PAGE_PREVIEW_ERROR':
          this.showPagePreviewError(message.data.errorMsg);
          sendResponse({ success: true });
          return true;

        default:
          sendResponse({ success: false, error: '未知消息类型' });
          return true;
      }
    } catch (error) {
      sendResponse({ success: false, error: error.message });
      return true;
    }
  }

  // 通知侧边栏
  notifySidePanel(type, data) {
    // 检查扩展上下文是否仍然有效
    if (!chrome.runtime) {
      return;
    }
    
    try {
      chrome.runtime.sendMessage({
        type: type,
        data: data,
        source: 'content-script'
      }).then(() => {
        // 静默处理成功
      }).catch(error => {
        // 忽略侧边栏未打开的错误
        if (!error.message.includes('Receiving end does not exist')) {
          // 静默处理错误
        }
      });
    } catch (error) {
      // 静默处理错误
    }
  }

  // 添加UI提示
  addUI() {
    // 检查是否已添加
    if (document.getElementById('wechat-assistant-indicator')) {
      return;
    }

    const indicator = document.createElement('div');
    indicator.id = 'wechat-assistant-indicator';
    indicator.textContent = '🤖 智能助手已启用';
    indicator.style.cssText = `
      position: fixed;
      top: 10px;
      right: 10px;
      background: #1976d2;
      color: white;
      padding: 8px 12px;
      border-radius: 6px;
      font-size: 12px;
      z-index: 10000;
      box-shadow: 0 2px 8px rgba(0,0,0,0.2);
      transition: opacity 0.3s;
    `;

    document.body.appendChild(indicator);

    // 3秒后自动隐藏
    setTimeout(() => {
      indicator.style.opacity = '0';
      setTimeout(() => {
        if (indicator.parentNode) {
          indicator.parentNode.removeChild(indicator);
        }
      }, 300);
    }, 3000);

    // 添加页面预览框
    this.addPagePreviewPanel();
  }

  // 添加页面预览面板
  addPagePreviewPanel() {
    // 检查是否已添加
    if (document.getElementById('wechat-assistant-preview-panel')) {
      return;
    }

    // 创建预览面板容器
    const previewPanel = document.createElement('div');
    previewPanel.id = 'wechat-assistant-preview-panel';
    previewPanel.className = 'wechat-assistant-preview-panel';
    
    // 安全地创建预览面板HTML结构
    const header = document.createElement('div');
    header.className = 'preview-panel-header';
    
    const title = document.createElement('h3');
    title.textContent = '模板预览';
    
    const toggleBtn = document.createElement('button');
    toggleBtn.className = 'preview-toggle-btn';
    toggleBtn.id = 'previewToggleBtn';
    toggleBtn.title = '收起预览';
    
    const toggleIcon = document.createElement('span');
    toggleIcon.className = 'toggle-icon';
    toggleIcon.textContent = '←';
    toggleBtn.appendChild(toggleIcon);
    
    header.appendChild(title);
    header.appendChild(toggleBtn);
    
    const content = document.createElement('div');
    content.className = 'preview-panel-content';
    content.id = 'previewPanelContent';
    
    const placeholder = document.createElement('div');
    placeholder.className = 'preview-placeholder';
    
    const placeholderIcon = document.createElement('div');
    placeholderIcon.className = 'placeholder-icon';
    placeholderIcon.textContent = '👁️';
    
    const placeholderText = document.createElement('p');
    placeholderText.textContent = '从扩展中选择模板查看预览';
    
    placeholder.appendChild(placeholderIcon);
    placeholder.appendChild(placeholderText);
    content.appendChild(placeholder);
    
    previewPanel.appendChild(header);
    previewPanel.appendChild(content);

    // 添加CSS样式
    this.addPreviewPanelStyles();

    // 插入到页面中
    document.body.appendChild(previewPanel);

    // 绑定事件
    this.bindPreviewPanelEvents();
  }

  // 添加预览面板样式
  addPreviewPanelStyles() {
    // 检查是否已添加样式
    if (document.getElementById('wechat-assistant-preview-styles')) {
      return;
    }

    const style = document.createElement('style');
    style.id = 'wechat-assistant-preview-styles';
    style.textContent = `
      .wechat-assistant-preview-panel {
        position: fixed;
        top: 0;
        left: 0;
        width: 400px;
        height: 100vh;
        background: #ffffff;
        border-right: 1px solid #e5e5e5;
        box-shadow: 2px 0 20px rgba(0, 0, 0, 0.15);
        z-index: 99999;
        transform: translateX(-100%);
        transition: transform 0.3s ease;
        display: flex;
        flex-direction: column;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
      }

      .wechat-assistant-preview-panel.open {
        transform: translateX(0);
      }

      /* 添加背景遮罩 */
      .wechat-assistant-preview-panel::after {
        content: '';
        position: fixed;
        top: 0;
        left: 0;
        width: 100vw;
        height: 100vh;
        background: rgba(0, 0, 0, 0.3);
        z-index: -1;
        opacity: 0;
        transition: opacity 0.3s ease;
        pointer-events: none;
      }

      .wechat-assistant-preview-panel.open::after {
        opacity: 1;
        pointer-events: auto;
      }

      /* 确保预览面板内容区域不响应遮罩点击 */
      .preview-panel-header,
      .preview-panel-content {
        position: relative;
        z-index: 1;
        pointer-events: auto;
      }

      .preview-panel-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 16px 20px;
        background: #f8f9fa;
        border-bottom: 1px solid #e5e5e5;
        flex-shrink: 0;
      }

      .preview-panel-header h3 {
        font-size: 16px;
        font-weight: 600;
        color: #333;
        margin: 0;
      }

      .preview-toggle-btn {
        background: none;
        border: none;
        color: #666;
        cursor: pointer;
        padding: 8px 12px;
        border-radius: 6px;
        transition: all 0.2s ease;
        font-size: 14px;
      }

      .preview-toggle-btn:hover {
        background: #e9ecef;
        color: #333;
      }

      .toggle-icon {
        display: inline-block;
        transition: transform 0.2s ease;
      }

      .preview-toggle-btn:hover .toggle-icon {
        transform: translateX(-2px);
      }

      .preview-panel-content {
        flex: 1;
        overflow-y: auto;
        overflow-x: hidden;
        background: #ffffff;
        position: relative;
      }

      .preview-placeholder {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        height: 100%;
        padding: 40px 20px;
        text-align: center;
        color: #999;
      }

      .placeholder-icon {
        font-size: 48px;
        margin-bottom: 16px;
        opacity: 0.6;
      }

      .preview-placeholder p {
        font-size: 14px;
        line-height: 1.5;
        margin: 0;
      }

      .preview-iframe {
        width: 100%;
        height: 100%;
        border: none;
        background: #ffffff;
        display: block;
      }

      .preview-loading {
        position: absolute;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 16px;
        color: #999;
      }

      .preview-loading .loading-spinner {
        width: 32px;
        height: 32px;
        border: 3px solid #e5e5e5;
        border-top: 3px solid #007AFF;
        border-radius: 50%;
        animation: spin 1s linear infinite;
      }

      @keyframes spin {
        0% { transform: rotate(0deg); }
        100% { transform: rotate(360deg); }
      }

      .preview-error {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        height: 100%;
        padding: 40px 20px;
        text-align: center;
        color: #ff3b30;
      }

      .preview-error .error-icon {
        font-size: 48px;
        margin-bottom: 16px;
      }

      .preview-error .error-text {
        font-size: 14px;
        line-height: 1.5;
      }

      /* 预览面板作为覆盖层，不推动页面内容 */
      /* 移除body的margin-left调整 */

      /* 响应式设计 */
      @media (max-width: 768px) {
        .wechat-assistant-preview-panel {
          width: 320px;
        }
      }
    `;

    document.head.appendChild(style);
  }

  // 绑定预览面板事件
  bindPreviewPanelEvents() {
    const toggleBtn = document.getElementById('previewToggleBtn');
    if (toggleBtn) {
      toggleBtn.addEventListener('click', () => {
        this.togglePagePreviewPanel();
      });
    }

    // 键盘快捷键支持
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && this.isPreviewPanelOpen) {
        this.closePagePreviewPanel();
      }
    });

    // 点击遮罩关闭预览面板
    document.addEventListener('click', (e) => {
      if (this.isPreviewPanelOpen) {
        const previewPanel = document.getElementById('wechat-assistant-preview-panel');
        const previewContent = previewPanel.querySelector('.preview-panel-content');
        const previewHeader = previewPanel.querySelector('.preview-panel-header');
        
        // 如果点击的不是预览面板的内容区域，则关闭面板
        if (!previewContent.contains(e.target) && !previewHeader.contains(e.target)) {
          this.closePagePreviewPanel();
        }
      }
    });
  }

  // 切换页面预览面板
  togglePagePreviewPanel() {
    const previewPanel = document.getElementById('wechat-assistant-preview-panel');
    const toggleIcon = document.querySelector('.toggle-icon');
    
    if (this.isPreviewPanelOpen) {
      // 关闭预览面板
      previewPanel.classList.remove('open');
      toggleIcon.textContent = '→';
      this.isPreviewPanelOpen = false;
    } else {
      // 打开预览面板
      previewPanel.classList.add('open');
      toggleIcon.textContent = '←';
      this.isPreviewPanelOpen = true;
    }
  }

  // 关闭页面预览面板
  closePagePreviewPanel() {
    if (this.isPreviewPanelOpen) {
      this.togglePagePreviewPanel();
    }
  }

  // 显示页面预览内容
  showPagePreviewContent(templateData) {
    
    const previewContent = document.getElementById('previewPanelContent');
    if (!previewContent) { return; }

    // 安全地显示加载状态
    previewContent.innerHTML = ''; // 清空内容
    
    const loadingDiv = document.createElement('div');
    loadingDiv.className = 'preview-loading';
    
    const spinner = document.createElement('div');
    spinner.className = 'loading-spinner';
    
    const loadingText = document.createElement('span');
    loadingText.textContent = '正在加载预览...';
    
    loadingDiv.appendChild(spinner);
    loadingDiv.appendChild(loadingText);
    previewContent.appendChild(loadingDiv);

    // 打开预览面板（即使认为已开，也强制设置为开启状态以防状态不同步）
    const previewPanel = document.getElementById('wechat-assistant-preview-panel');
    if (previewPanel && !previewPanel.classList.contains('open')) {
      this.togglePagePreviewPanel();
    }

    // 更新标题
    const header = document.querySelector('.preview-panel-header h3');
    if (header) {
      header.textContent = `模板预览 - ${templateData.name}`;
    }
  }

  // 显示页面预览错误
  showPagePreviewError(errorMsg) {
    const previewContent = document.getElementById('previewPanelContent');
    if (!previewContent) return;

    // 安全地显示错误状态
    previewContent.innerHTML = ''; // 清空内容
    
    const errorDiv = document.createElement('div');
    errorDiv.className = 'preview-error';
    
    const iconDiv = document.createElement('div');
    iconDiv.className = 'error-icon';
    iconDiv.textContent = '⚠️';
    
    const textDiv = document.createElement('div');
    textDiv.className = 'error-text';
    textDiv.textContent = errorMsg;
    
    errorDiv.appendChild(iconDiv);
    errorDiv.appendChild(textDiv);
    previewContent.appendChild(errorDiv);
  }

  // 显示页面预览内容（支持HTML或Base64图片）
  displayPagePreviewContent(content) {
    
    const previewContent = document.getElementById('previewPanelContent');
    if (!previewContent) { return; }
    
    // 如果是Base64图片，优先转换为blob: URL 以绕过页面img-src对data:的限制
    // 方案A：storage_key 模式，通过 storage 读取后台准备好的预览图
    if (content && typeof content === 'object' && content.mode === 'storage_key') {
      const key = content.key;
      if (!key) { this.showPagePreviewError('预览数据缺少key'); return; }
      try {
        chrome.storage.local.get(key, (items) => {
          const dataUrl = items ? items[key] : null;
          if (dataUrl && typeof dataUrl === 'string') {
            this.displayPagePreviewContent(dataUrl);
          } else {
            this.showPagePreviewError('预览图不存在');
          }
        });
      } catch (e) {
        this.showPagePreviewError('读取预览图失败');
      }
      return;
    }

    if (typeof content === 'string' && content.startsWith('data:image/')) {
      const img = document.createElement('img');
      img.alt = '模板预览图';
      img.style.width = '100%';
      img.style.height = 'auto';
      img.style.display = 'block';
      img.style.background = 'white';
      img.referrerPolicy = 'no-referrer';

      let objectUrl = null;

      const setSrcToBlobUrl = async () => {
        try {
          const t0 = performance.now();
          // 使用 fetch(dataURL) 更稳健地转换为 Blob（兼容大体积并避免手写 atob）
          const resp = await fetch(content);
          const blob = await resp.blob();
          objectUrl = URL.createObjectURL(blob);
          img.src = objectUrl;
        } catch (err) {
          // 回退：直接使用 data: URL
          img.src = content;
        }
      };

      img.onload = () => {
        if (objectUrl) {
          try { URL.revokeObjectURL(objectUrl); } catch (e) {}
        }
        const header = document.querySelector('.preview-panel-header h3');
        if (header) { header.textContent = '模板预览'; }
      };
      img.onerror = () => {
        if (objectUrl) {
          try { URL.revokeObjectURL(objectUrl); } catch (e) {}
        }
        this.showPagePreviewError('图片加载失败');
      };

      // 安全地清空内容
      while (previewContent.firstChild) {
        previewContent.removeChild(previewContent.firstChild);
      }
      previewContent.appendChild(img);
      // 异步设置src，避免在DOM未就绪时阻塞
      setSrcToBlobUrl();
      return;
    }

    // 否则按HTML内容渲染到iframe
    const iframe = document.createElement('iframe');
    iframe.className = 'preview-iframe';
    iframe.style.width = '100%';
    iframe.style.height = '100%';
    iframe.style.border = 'none';
    iframe.style.background = 'white';
    iframe.sandbox = 'allow-same-origin';

    iframe.onload = () => {
      try {
        const iframeDoc = iframe.contentDocument || iframe.contentWindow.document;
        const style = iframeDoc.createElement('style');
        style.textContent = `
          html, body { margin:0; padding:0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: white; width:auto; overflow-x:hidden; }
          body { padding: 20px; }
          img { max-width:100%; height:auto; display:block; }
          * { box-sizing: border-box; }
        `;
        const container = iframeDoc.createElement('div');
        container.className = 'template-container';
        const cleanContent = content.replace(/<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>/gi, '');
        // 安全地设置内容
        container.textContent = ''; // 清空容器
        // 使用安全的方式设置HTML内容
        if (window.domSanitizer) {
          window.domSanitizer.safeSetInnerHTML(container, cleanContent);
        } else {
          // 降级处理：只设置文本内容
          container.textContent = cleanContent;
        }
        
        // 安全地清空iframe文档
        while (iframeDoc.head.firstChild) {
          iframeDoc.head.removeChild(iframeDoc.head.firstChild);
        }
        while (iframeDoc.body.firstChild) {
          iframeDoc.body.removeChild(iframeDoc.body.firstChild);
        }
        iframeDoc.head.appendChild(style);
        iframeDoc.body.appendChild(container);
      } catch (error) {
        this.showPagePreviewError('预览加载失败');
      }
    };

    iframe.onerror = () => {
      this.showPagePreviewError('iframe加载失败');
    };

    // 安全地清空内容并添加iframe
    while (previewContent.firstChild) {
      previewContent.removeChild(previewContent.firstChild);
    }
    previewContent.appendChild(iframe);
  }
}

// 初始化内容监听器
new WeChatContentMonitor();