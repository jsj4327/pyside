// 定义一个常量标识，用于标记当前脚本的版本或名称
const mainworld = "LIYIN";

console.log("【排查日志】content-script.js 开始加载执行");

(function () {
  // ==========================================
  // 1. 防重复注入拦截检查
  // ==========================================
  if (document.getElementById('ai-assistant-floating-panel')) {
    console.log("【排查日志】检测到面板已存在，终止脚本二次初始化");
    return;
  }

  if (window.__AI_ASSISTANT_INJECTED__) {
    console.log("【排查日志】检测到脚本全局标记存在，终止重复执行");
    return;
  }
  window.__AI_ASSISTANT_INJECTED__ = true;

  // ==========================================
  // 2. Trusted Types 安全策略兼容（防止 innerHTML 报错）
  // ==========================================
  const escapeHTMLPolicy = window.trustedTypes && window.trustedTypes.createPolicy
    ? window.trustedTypes.createPolicy('aiAssistantPolicy', { createHTML: (string) => string })
    : { createHTML: (string) => string };

  // ==========================================
  // 3. 构建悬浮面板 DOM 结构
  // ==========================================
  const panel = document.createElement('div');
  panel.id = 'ai-assistant-floating-panel';
  
  const panelHTML = `
    <div id="ai-panel-header">
      <span>AI 助手 (PySide 文件同步版)</span>
      <span id="wsStatus" style="font-size: 11px; color: orange; margin-left: 8px;">[WebSocket: 未连接]</span>
      <button id="ai-close-btn" style="background:none; border:none; font-size:18px; cursor:pointer; color:#666;">&times;</button>
    </div>
    <div id="ai-panel-body">
      <!-- WebSocket 地址输入与手动连接区域 -->
      <div class="input-group" style="display: flex; gap: 6px; margin-bottom: 8px;">
        <input type="text" id="wsUrlInput" value="ws://localhost:9002" style="flex: 1; padding: 4px; font-size: 12px;" />
        <button id="wsConnectBtn" style="background-color: #007bff; color: white; border: none; padding: 4px 8px; cursor: pointer; border-radius: 4px;">手动连接</button>
      </div>

      <!-- 发送指令给 AI 的输入框区域 -->
      <div class="input-group">
        <textarea id="aiCommandInput" placeholder="请输入要发送给 AI 的指令..." rows="3"></textarea>
      </div>
      <button id="aiSendBtn">发送运行</button>
      
      <hr style="margin: 12px 0; border: none; border-top: 1px solid #ddd; flex-shrink: 0;">

      <!-- 手动触发解析代码文件的按钮 -->
      <button id="aiFetchBtn" style="background-color: #28a745; margin-bottom: 8px; width: 100%; color: white; border: none; padding: 6px; cursor: pointer; border-radius: 4px; flex-shrink: 0;">手动解析并发送代码文件</button>
      
      <!-- 状态与解析内容预览文本框 -->
      <div class="input-group" style="flex: 1; display: flex; flex-direction: column; overflow: hidden;">
        <textarea id="aiAnswerArea" placeholder="解析出的文件与状态将显示在这里..." readonly></textarea>
      </div>
    </div>
  `;

  panel.innerHTML = escapeHTMLPolicy.createHTML(panelHTML);
  document.body.appendChild(panel);

  // 定义状态变量
  let answerDebounceTimer = null; 
  let observer = null;            

  // ==========================================
  // 4. WebSocket 连接与消息收发（委派 Service Worker）
  // ==========================================
  function connectWebSocket() {
    const urlInput = document.getElementById('wsUrlInput').value.trim();
    const statusSpan = document.getElementById('wsStatus');

    if (!urlInput) {
      alert("请输入有效的 WebSocket 地址");
      return;
    }

    statusSpan.style.color = 'orange';
    statusSpan.innerText = '[WebSocket: 连接中...]';

    // 向 Service Worker (background/service-worker.js) 发起连接请求，绕过 CSP
    chrome.runtime.sendMessage({ type: "CONNECT_WS", url: urlInput });
  }

  document.getElementById('wsConnectBtn').addEventListener('click', connectWebSocket);

  // 监听来自 Background (Service Worker) 的状态推送和服务端指令
  chrome.runtime.onMessage.addListener((request) => {
    const statusSpan = document.getElementById('wsStatus');

    if (request.type === "WS_STATUS") {
      if (request.status === "connected") {
        statusSpan.style.color = 'limegreen';
        statusSpan.innerText = '[WebSocket: 已连接]';
      } else if (request.status === "disconnected") {
        statusSpan.style.color = 'red';
        statusSpan.innerText = '[WebSocket: 未连接]';
      } else {
        statusSpan.style.color = 'red';
        statusSpan.innerText = '[WebSocket: 连接异常]';
      }
    } 
    else if (request.type === "WS_RECEIVED_DATA") {
      try {
        const data = JSON.parse(request.data);
        const jsonString = typeof data === 'string' ? data : JSON.stringify(data, null, 2);
        
        const inputEl = document.getElementById('aiCommandInput');
        if (inputEl) inputEl.value = jsonString;

        if (jsonString) {
          console.log("[Extension] 收到 PySide 完整 JSON 指令，转发给 AI 输入框");
          executeSendAndMonitor(jsonString);
        }
      } catch (e) {
        console.error("[Extension] 解析数据失败:", e);
      }
    }
  });

  // 通过 Service Worker 转发数据给 PySide 服务端
  function sendFilesToPySide(filesData) {
    if (Array.isArray(filesData) && filesData.length > 0) {
      chrome.runtime.sendMessage({
        type: "SEND_WS_DATA",
        payload: {
          action: "save_files_batch",
          files: filesData
        }
      }, (res) => {
        if (res && res.status === "error") {
          console.warn("[Extension] 发送数据失败:", res.message);
        }
      });
    }
  }

  // ==========================================
  // 5. 悬浮窗面板拖拽逻辑
  // ==========================================
  const header = document.getElementById('ai-panel-header');
  let isDragging = false, startX, startY, initialLeft, initialTop;
  
  function onMouseMove(e) {
    if (!isDragging) return;
    panel.style.left = (initialLeft + (e.clientX - startX)) + 'px';
    panel.style.top = (initialTop + (e.clientY - startY)) + 'px';
  }
  
  function onMouseUp() {
    isDragging = false;
    document.removeEventListener('mousemove', onMouseMove);
    document.removeEventListener('mouseup', onMouseUp);
  }

  header.addEventListener('mousedown', (e) => {
    if (e.target.id === 'ai-close-btn') return;
    isDragging = true;
    startX = e.clientX; startY = e.clientY;
    const rect = panel.getBoundingClientRect();
    initialLeft = rect.left; initialTop = rect.top;
    panel.style.position = 'fixed';
    panel.style.left = initialLeft + 'px';
    panel.style.top = initialTop + 'px';
    panel.style.right = 'auto';
    document.addEventListener('mousemove', onMouseMove);
    document.addEventListener('mouseup', onMouseUp);
  });

  // ==========================================
  // 6. 关闭与彻底清理逻辑
  // ==========================================
  document.getElementById('ai-close-btn').addEventListener('click', () => {
    if (observer) { observer.disconnect(); observer = null; }
    if (answerDebounceTimer) { clearTimeout(answerDebounceTimer); }
    document.removeEventListener('mousemove', onMouseMove);
    document.removeEventListener('mouseup', onMouseUp);
    
    // 清除防重复标志
    delete window.__AI_ASSISTANT_INJECTED__;
    panel.remove();
    console.log("【排查日志】AI 助手面板已彻底卸载清理");
  });

  // ==========================================
  // 7. 文本填充与自动发送控制
  // ==========================================
  function executeSendAndMonitor(textToSend) {
    const textarea = document.querySelector(
      'div[contenteditable="true"][role="textbox"], textarea[aria-label*="Gemini"], div.rich-textarea, textarea'
    );

    if (!textarea) {
      console.log("没有找到有效的 AI 输入框");
      return;
    }

    textarea.focus();

    if (textarea.tagName === 'TEXTAREA') {
      textarea.value = textToSend;
      textarea.dispatchEvent(new Event('input', { bubbles: true }));
    } else {
      document.execCommand('selectAll', false, null);
      if (!document.execCommand('insertText', false, textToSend)) {
        textarea.textContent = textToSend;
      }
      textarea.dispatchEvent(new Event('input', { bubbles: true }));
    }

    setTimeout(() => {
      const sendButton = document.querySelector(
        'button[aria-label*="发送"], button[aria-label*="Send"], button.send-button'
      );

      if (sendButton && !sendButton.disabled) {
        sendButton.click();
        startMonitoringAIAnswer();
      } else {
        textarea.dispatchEvent(new KeyboardEvent('keydown', {
          key: 'Enter',
          code: 'Enter',
          keyCode: 13,
          which: 13,
          bubbles: true
        }));
        startMonitoringAIAnswer();
      }
    }, 500);
  }

  // ==========================================
  // 8. 解析回答中的文件数据 (修复 JSON 语法报错的核心算法)
  // ==========================================
  function extractFilesData(rootElement) {
    let filesList = []; 
    if (!rootElement) return filesList;

    // 严谨的 JSON 提取与修复清洗函数
    const safeParseJSON = (rawStr) => {
      if (!rawStr || typeof rawStr !== 'string') return null;

      // 1. 剥离 Markdown 代码块标志 (如 ```json ... ```)
      let cleaned = rawStr.trim()
        .replace(/^```[a-zA-Z]*\n?/g, '')
        .replace(/```$/g, '')
        .trim();

      // 2. 截取最外层的 { ... } 闭合结构，抛弃前后的自由文本
      const firstBrace = cleaned.indexOf('{');
      const lastBrace = cleaned.lastIndexOf('}');
      if (firstBrace === -1 || lastBrace === -1 || lastBrace <= firstBrace) {
        return null;
      }
      cleaned = cleaned.substring(firstBrace, lastBrace + 1);

      // 3. 尝试直接解析
      try {
        const obj = JSON.parse(cleaned);
        if (obj && Array.isArray(obj.files)) return obj.files;
      } catch (e) {
        // 直接解析失败，进入容错修复程序（处理未转义的真实换行符）
      }

      // 4. 修复未转义换行与控制字符
      try {
        const fixedStr = cleaned.replace(/"code"\s*:\s*"([\s\S]*?)"(?=\s*,\s*"|\s*\}|\s*\])/g, (match, codeGroup) => {
          const escapedCode = codeGroup
            .replace(/\\/g, '\\\\')
            .replace(/"/g, '\\"')
            .replace(/\n/g, '\\n')
            .replace(/\r/g, '\\r')
            .replace(/\t/g, '\\t');
          return `"code": "${escapedCode}"`;
        });

        const obj = JSON.parse(fixedStr);
        if (obj && Array.isArray(obj.files)) return obj.files;
      } catch (e2) {
        console.warn("[Extension] 尝试修复换行符后依然解析失败:", e2.message);
      }

      return null;
    };

    try {
      // 策略 1：遍历 pre / code 节点（最精准的底层代码块）
      const codeBlocks = rootElement.querySelectorAll('pre, code, div.code-block');
      for (const block of codeBlocks) {
        const text = block.textContent || "";
        if (text.includes('"files"')) {
          const res = safeParseJSON(text);
          if (res) {
            console.log("[Extension] 成功从 code 节点提取文件:", res.length, "个");
            return res;
          }
        }
      }

      // 策略 2：对元素完整 textContent 进行全域解析
      const fullText = rootElement.textContent || "";
      if (fullText.includes('"files"')) {
        const res = safeParseJSON(fullText);
        if (res) {
          console.log("[Extension] 成功从全文本提取文件:", res.length, "个");
          return res;
        }
      }

      // 策略 3：采用正向与反向匹配正则提取 {"files": [...]} 区块
      const jsonRegex = /\{[\s\S]*?"files"\s*:\s*\[[\s\S]*?\][\s\S]*?\}/g;
      const matches = fullText.match(jsonRegex);
      if (matches) {
        for (const matchStr of matches) {
          const res = safeParseJSON(matchStr);
          if (res) {
            console.log("[Extension] 成功从正则匹配提取文件:", res.length, "个");
            return res;
          }
        }
      }

    } catch (err) {
      console.error("[Extension] extractFilesData 运行时错误:", err);
    }

    return [];
  }

  // ==========================================
  // 9. 监听 AI 回答生成（DOM 变动监听）
  // ==========================================
  function startMonitoringAIAnswer() {
    const chatContainer = document.querySelector(
      'main, conversation-container, div.ds-virtual-list-visible-items, div[role="main"]'
    ) || document.body;

    if (observer) observer.disconnect();

    observer = new MutationObserver(() => {
      if (answerDebounceTimer) clearTimeout(answerDebounceTimer);

      // 防抖等待 AI 停止流式打字输出 (800ms)
      answerDebounceTimer = setTimeout(() => {
        const allAnswers = chatContainer.querySelectorAll(
          'message-content, model-response, div.response-container, div.ds-message, div.markdown-body'
        );

        if (allAnswers.length > 0) {
          const latestAnswer = allAnswers[allAnswers.length - 1];
          const rawAnswerText = latestAnswer.textContent || "";
          const filesData = extractFilesData(latestAnswer);

          let summaryDisplay = rawAnswerText + "\n\n--- 【已解析的文件列表】 ---\n";
          
          if (Array.isArray(filesData) && filesData.length > 0) {
            filesData.forEach(f => {
              if (f && f.filename) {
                summaryDisplay += `文件: ${f.filename} (代码长度: ${f.code ? f.code.length : 0})\n`;
              }
            });
          } else {
            summaryDisplay += "未检测到符合格式的文件数据\n";
          }
          
          const answerArea = document.getElementById('aiAnswerArea');
          if (answerArea) answerArea.value = summaryDisplay;

          // 自动同步文件回 PySide
          sendFilesToPySide(filesData);
        }
      }, 800);
    });

    observer.observe(chatContainer, { childList: true, subtree: true, characterData: true });
  }

  // ==========================================
  // 10. 面板按钮绑定
  // ==========================================
  document.getElementById('aiSendBtn').addEventListener('click', () => {
    const textInput = document.getElementById('aiCommandInput');
    if (!textInput) return;
    const textToSend = textInput.value.trim();
    if (!textToSend) return;
    executeSendAndMonitor(textToSend);
  });

  // 手动触发解析并发送逻辑
  document.getElementById('aiFetchBtn').addEventListener('click', () => {
    const answerArea = document.getElementById('aiAnswerArea');
    
    const selectors = [
      'message-content', 
      'model-response', 
      'div.response-container', 
      'div.ds-message',
      'div.markdown-body'
    ];
    
    let allAnswers = [];
    for (const sel of selectors) {
      const found = document.querySelectorAll(sel);
      if (found && found.length > 0) {
        allAnswers = found;
      }
    }

    if (allAnswers.length === 0) {
      allAnswers = document.querySelectorAll('main, conversation-container, [role="main"]');
    }

    if (allAnswers.length === 0) {
      if (answerArea) answerArea.value = "❌ 错误：未找到任何 AI 消息容器节点";
      console.warn("[Extension] 未找到回答元素");
      return;
    }

    const latestAnswer = allAnswers[allAnswers.length - 1];
    console.log("【排查日志】开始手动提取最新回答节点:", latestAnswer);

    const filesData = extractFilesData(latestAnswer);

    if (Array.isArray(filesData) && filesData.length > 0) {
      const summary = `✅ 成功解析并发送 ${filesData.length} 个文件！\n` + 
                      JSON.stringify(filesData, null, 2);
      if (answerArea) answerArea.value = summary;

      console.log("【排查日志】准备发送提取出的文件给 PySide:", filesData);
      sendFilesToPySide(filesData);
    } else {
      const rawTextSnippet = (latestAnswer.textContent || "").substring(0, 300);
      if (answerArea) {
        answerArea.value = `⚠️ 解析失败：未能找到合法的 {"files": [...]} 格式 JSON。\n\n【最新抓取到的前 300 字符预览】:\n${rawTextSnippet}`;
      }
      console.warn("【排查日志】未能解析出有效的文件数据");
    }
  });

})();