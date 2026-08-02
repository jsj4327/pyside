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
<button id="aiFetchBtn" style="background-color: #28a745; margin-bottom: 8px; width: 100%; color: white; border: none; padding: 6px; cursor: pointer; border-radius: 4px; flex-shrink: 0;">手动获取并发送原始内容</button>

<!-- 状态与内容预览文本框 -->
<div class="input-group" style="flex: 1; display: flex; flex-direction: column; overflow: hidden;">
<textarea id="aiAnswerArea" placeholder="从 DOM 获取的原始内容将显示在这里..." readonly></textarea>
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

  // ==========================================
  // 监听来自 Background 的消息
  // ==========================================
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
    } else if (request.type === "WS_RECEIVED_DATA") {
      try {
        console.log("收到原始数据:", request.data);

        // 直接获取原始数据，不进行 JSON 解析
        const rawData = request.data;

        // 直接填入输入框
        const inputEl = document.getElementById('aiCommandInput');
        if (inputEl) {
          inputEl.value = rawData;
        }

        // 直接发送到 AI 输入框
        if (rawData) {
          console.log("[Extension] 收到 PySide 原始数据，直接转发给 AI 输入框");
          executeSendAndMonitor(rawData);
        }
      } catch (e) {
        console.error("[Extension] 处理数据失败:", e);
      }
    }
  });

  // ==========================================
  // 直接透传原始数据给 PySide 服务端
  // ==========================================
  function sendFilesToPySide(rawData) {
    // 打印发送内容日志，方便观察
    console.log("【发送日志】即将发送给 PySide 的原始内容 ↓↓↓");
    console.log(rawData);
    console.log("【发送日志】内容长度:", typeof rawData === 'string' ? rawData.length : 0);

    chrome.runtime.sendMessage({
      type: "SEND_WS_DATA",
      payload: rawData
    }, (res) => {
      if (chrome.runtime.lastError) {
        console.warn("[Extension] 消息发送失败:", chrome.runtime.lastError.message);
      } else if (res && res.status === "error") {
        console.warn("[Extension] PySide 返回错误:", res.message);
      } else {
        console.log("[Extension] 原始内容已成功发送给 PySide");
      }
    });
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
    startX = e.clientX;
    startY = e.clientY;
    const rect = panel.getBoundingClientRect();
    initialLeft = rect.left;
    initialTop = rect.top;
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
    if (observer) {
      observer.disconnect();
      observer = null;
    }
    if (answerDebounceTimer) {
      clearTimeout(answerDebounceTimer);
    }
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
    // 确保 textToSend 是字符串
    const sendText = typeof textToSend === 'string' ? textToSend : String(textToSend);

    const textarea = document.querySelector(
      'div[contenteditable="true"][role="textbox"], textarea[aria-label*="Gemini"], div.rich-textarea, textarea'
    );

    if (!textarea) {
      console.log("没有找到有效的 AI 输入框");
      return;
    }

    textarea.focus();

    if (textarea.tagName === 'TEXTAREA') {
      textarea.value = sendText;
      textarea.dispatchEvent(new Event('input', { bubbles: true }));
    } else {
      document.execCommand('selectAll', false, null);
      if (!document.execCommand('insertText', false, sendText)) {
        textarea.textContent = sendText;
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
  // 8. 监听 AI 回答生成 - 直接发送原始文本（无任何 JSON 解析）
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

          // 本地预览显示原始内容
          const answerArea = document.getElementById('aiAnswerArea');
          if (answerArea) {
            answerArea.value = rawAnswerText;
          }

          // ★ 直接发送原始文本给 PySide，不做任何解析
          console.log("[Extension] 检测到 AI 最新回答，准备直接发送原始文本");
          sendFilesToPySide(rawAnswerText);
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

  // 手动触发按钮：直接获取最新回答的原始文本并发送
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
    const rawAnswerText = latestAnswer.textContent || "";

    console.log("【排查日志】手动获取最新回答原始内容，长度:", rawAnswerText.length);

    // 本地预览显示原始内容
    if (answerArea) {
      answerArea.value = rawAnswerText;
    }

    // ★ 直接发送原始文本给 PySide，不做任何解析
    sendFilesToPySide(rawAnswerText);
  });

})();