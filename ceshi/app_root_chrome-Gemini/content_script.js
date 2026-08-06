// content_script.js - 精准定位最新问题与流式接收 AI 回复（完整版 + 自动捕获 + port 重连）

let visible = false, panel = null, port = null;
let observer = null;
let isWaitingForAnswer = false;
let answerCheckTimer = null;
let processedAnswerId = null;
let submittedText = '';

let pollingTimer = null;
let currentAnswerElement = null;
let lastExtractedText = '';
let stabilityTimer = null;

// ============================================
// 创建面板（使用事件委托处理所有按钮）
// ============================================
function createPanel() {
  if (panel) return;
  const c = document.createElement('div');
  c.id = 'bridge-panel';
  c.style.cssText = `
    position: fixed;
    top: 80px;
    right: 20px;
    width: 380px;
    max-height: 700px;
    background: #ffffff;
    border-radius: 12px;
    box-shadow: 0 4px 20px rgba(0,0,0,0.15);
    z-index: 999999;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    font-size: 13px;
    display: none;
    overflow: hidden;
    border: 1px solid #e8e8e8;
  `;

  const h = document.createElement('div');
  h.style.cssText = `
    background: #f5f5f5;
    color: #333;
    padding: 10px 16px;
    cursor: move;
    display: flex;
    justify-content: space-between;
    align-items: center;
    user-select: none;
    border-bottom: 1px solid #e8e8e8;
  `;
  h.innerHTML = `
    <span style="font-weight:600;font-size:14px;color:#1a1a1a;">Chat Bridge Injector</span>
    <div style="display:flex;align-items:center;gap:8px;">
      <span id="dot" style="display:inline-block;width:8px;height:8px;border-radius:50%;background:#ccc;"></span>
      <span id="toggle" style="cursor:pointer;font-size:16px;color:#888;">−</span>
      <span id="close" style="cursor:pointer;font-size:16px;color:#888;">✕</span>
    </div>
  `;
  c.appendChild(h);

  const b = document.createElement('div');
  b.style.cssText = `padding:14px 16px 16px 16px;background:#fafafa;max-height:620px;overflow-y:auto;`;
  b.id = 'body';
  b.innerHTML = `
    <div style="font-size:12px;font-weight:500;color:#888;margin-bottom:6px;">请求</div>
    <textarea id="content" style="width:100%;height:80px;padding:8px 10px;border:1px solid #ddd;border-radius:6px;font-family:monospace;font-size:13px;resize:vertical;background:#fff;color:#333;box-sizing:border-box;outline:none;">等待接收请求...</textarea>
    <div style="display:flex;gap:8px;margin-top:8px;margin-bottom:8px;">
      <button id="send-page" style="flex:1;padding:8px 0;background:#4CAF50;color:#fff;border:none;border-radius:6px;cursor:pointer;font-weight:500;font-size:13px;">📤 发送到页面</button>
      <button id="send-client" style="flex:1;padding:8px 0;background:#2196F3;color:#fff;border:none;border-radius:6px;cursor:pointer;font-weight:500;font-size:13px;">📤 发回到客户端</button>
    </div>
    <div style="font-size:12px;font-weight:500;color:#888;margin-top:6px;margin-bottom:4px;">AI 反馈 (支持自动捕获)</div>
    <textarea id="ai-feedback" readonly style="width:100%;height:300px;padding:8px 10px;border:1px solid #ddd;border-radius:6px;font-family:monospace;font-size:13px;resize:vertical;background:#f9f9f9;color:#333;box-sizing:border-box;outline:none;">等待 AI 反馈...</textarea>
    <div style="display:flex;align-items:center;gap:8px;font-size:12px;color:#888;border-top:1px solid #eee;padding-top:10px;margin-top:8px;">
      <span style="font-weight:500;">反馈</span>
      <span id="fb" style="color:#999;">就绪</span>
    </div>
  `;
  c.appendChild(b);
  document.body.appendChild(c);
  panel = c;

  // ---- 拖拽 ----
  let dragging = false, ox = 0, oy = 0;
  h.addEventListener('mousedown', (e) => {
    if (e.target.closest('div')) {
      dragging = true;
      const r = c.getBoundingClientRect();
      ox = e.clientX - r.left;
      oy = e.clientY - r.top;
      c.style.cursor = 'grabbing';
    }
  });
  document.addEventListener('mousemove', (e) => {
    if (!dragging) return;
    let x = e.clientX - ox, y = e.clientY - oy;
    x = Math.max(0, Math.min(window.innerWidth - c.offsetWidth, x));
    y = Math.max(0, Math.min(window.innerHeight - c.offsetHeight, y));
    c.style.left = x + 'px';
    c.style.top = y + 'px';
    c.style.right = 'auto';
  });
  document.addEventListener('mouseup', () => { dragging = false; c.style.cursor = 'default'; });

  // ---- 事件委托：处理所有按钮点击（toggle, close, send-page, send-client） ----
  c.addEventListener('click', function(e) {
    const btn = e.target.closest('button');
    if (!btn) return;

    // 最小化/展开
    if (btn.id === 'toggle') {
      const bb = document.getElementById('body');
      const t = document.getElementById('toggle');
      if (bb.style.display === 'none') {
        bb.style.display = 'block';
        t.textContent = '−';
        c.style.maxHeight = '700px';
      } else {
        bb.style.display = 'none';
        t.textContent = '+';
        c.style.maxHeight = '44px';
      }
      return;
    }

    // 关闭
    if (btn.id === 'close') {
      hidePanel();
      return;
    }

    // 发送到页面
    if (btn.id === 'send-page') {
      console.log("document.getElementById('send-page').addEventListener====================");
      const fb = document.getElementById('fb');
      const text = document.getElementById('content').value.trim();
      if (!text || text === '等待接收请求...') {
        fb.textContent = '⚠️ 请输入内容';
        fb.style.color = '#e67e22';
        return;
      }
      submittedText = text;
      if (injectToPage(text)) {
        startListeningForAnswer(text);
      } else {
        fb.textContent = '❌ 未找到输入框';
        fb.style.color = '#e74c3c';
      }
      return;
    }

    // 发回到客户端
    if (btn.id === 'send-client') {
      const fb = document.getElementById('fb');
      const text = document.getElementById('ai-feedback').value.trim();
      if (!text || text === '等待 AI 反馈...') {
        fb.textContent = '⚠️ 请输入内容';
        fb.style.color = '#e67e22';
        return;
      }
      const payload = { type: 'AI_RESULT', text: text, timestamp: Date.now() };
      chrome.runtime.sendMessage({ action: 'sendToClient', payload }, (resp) => {
        if (resp && resp.success) {
          fb.textContent = '✅ 已发送给客户端';
          fb.style.color = '#27ae60';
        } else {
          fb.textContent = '❌ 发送失败: ' + (resp?.error || 'WS未连接');
          fb.style.color = '#e74c3c';
        }
      });
    }
  });
}

// ============================================
// AI 回复监听与流式接收
// ============================================
function startListeningForAnswer(questionText = '') {
  isWaitingForAnswer = true;
  processedAnswerId = null;
  lastExtractedText = '';

  stopListening();

  const statusEl = document.getElementById('fb');
  const feedbackEl = document.getElementById('ai-feedback');

  statusEl.textContent = '⏳ 正在监听 AI 响应...';
  statusEl.style.color = '#f39c12';

  observer = new MutationObserver((mutations) => {
    if (!isWaitingForAnswer) return;

    if (!currentAnswerElement || !document.body.contains(currentAnswerElement)) {
      currentAnswerElement = findAnswerElement(document.body, questionText);
    }

    if (currentAnswerElement) {
      const textContent = extractAnswerText(currentAnswerElement);

      if (textContent && textContent.trim().length > 0) {
        feedbackEl.value = textContent;
        statusEl.textContent = '🔄 AI 正在流式输出...';
        statusEl.style.color = '#3498db';

        if (textContent !== lastExtractedText) {
          lastExtractedText = textContent;

          if (stabilityTimer) clearTimeout(stabilityTimer);

          stabilityTimer = setTimeout(() => {
            if (isWaitingForAnswer) {
              finishReceivingAnswer(textContent);
            }
          }, 1500);
        }
      }
    }
  });

  observer.observe(document.body, {
    childList: true,
    subtree: true,
    characterData: true,
    attributes: true
  });

  answerCheckTimer = setTimeout(() => {
    if (isWaitingForAnswer) {
      if (lastExtractedText.trim().length > 0) {
        finishReceivingAnswer(lastExtractedText);
      } else {
        statusEl.textContent = '⏰ AI 回复超时（60秒）';
        statusEl.style.color = '#e67e22';
        isWaitingForAnswer = false;
        stopListening();
      }
    }
  }, 60000);

  startPolling(questionText);
}

function finishReceivingAnswer(finalText) {
  isWaitingForAnswer = false;
  stopListening();

  const statusEl = document.getElementById('fb');
  const feedbackEl = document.getElementById('ai-feedback');

  feedbackEl.value = finalText;
  statusEl.textContent = '✅ AI 回复接收完成';
  statusEl.style.color = '#27ae60';

  console.log('[Content] AI 回复已成功完整捕获，长度:', finalText.length);
}

function stopListening() {
  if (observer) {
    observer.disconnect();
    observer = null;
  }
  if (answerCheckTimer) {
    clearTimeout(answerCheckTimer);
    answerCheckTimer = null;
  }
  if (stabilityTimer) {
    clearTimeout(stabilityTimer);
    stabilityTimer = null;
  }
  if (pollingTimer) {
    clearInterval(pollingTimer);
    pollingTimer = null;
  }
  currentAnswerElement = null;
}

function startPolling(questionText) {
  if (pollingTimer) clearInterval(pollingTimer);

  pollingTimer = setInterval(() => {
    if (!isWaitingForAnswer) {
      clearInterval(pollingTimer);
      pollingTimer = null;
      return;
    }

    if (!currentAnswerElement || !document.body.contains(currentAnswerElement)) {
      currentAnswerElement = findAnswerElement(document.body, questionText);
    }

    if (currentAnswerElement) {
      const textContent = extractAnswerText(currentAnswerElement);
      if (textContent && textContent !== lastExtractedText) {
        lastExtractedText = textContent;
        document.getElementById('ai-feedback').value = textContent;

        if (stabilityTimer) clearTimeout(stabilityTimer);
        stabilityTimer = setTimeout(() => {
          if (isWaitingForAnswer) {
            finishReceivingAnswer(textContent);
          }
        }, 1500);
      }
    }
  }, 800);
}

// ============================================
// 查找答案元素（增强版：精准匹配 Gemini 最新答案）
// ============================================
function findAnswerElement(root, questionText) {
  // 第一优先级：带有 model-response-message-content 开头的 .markdown（最精准）
  const idCandidates = root.querySelectorAll('.markdown[id^="model-response-message-content"]');
  if (idCandidates.length > 0) {
    const latest = idCandidates[idCandidates.length - 1];
    console.log('[FindAnswer] ✅ 通过 id^="model-response-message-content" 找到最新答案');
    return latest;
  }

  // 第二优先级：structured-content-container .markdown
  const structured = root.querySelectorAll('structured-content-container .markdown');
  if (structured.length > 0) {
    const latest = structured[structured.length - 1];
    console.log('[FindAnswer] ✅ 通过 structured-content-container .markdown 找到最新答案');
    return latest;
  }

  // 第三优先级：message-content .markdown
  const message = root.querySelectorAll('message-content .markdown');
  if (message.length > 0) {
    const latest = message[message.length - 1];
    console.log('[FindAnswer] ✅ 通过 message-content .markdown 找到最新答案');
    return latest;
  }

  // 第四优先级：任何 .markdown（兜底）
  const all = root.querySelectorAll('.markdown');
  if (all.length > 0) {
    const latest = all[all.length - 1];
    console.log('[FindAnswer] ⚠️ 通过通用 .markdown 找到元素（可能是问题或旧答案）');
    return latest;
  }

  console.warn('[FindAnswer] ❌ 未找到任何答案元素');
  return null;
}

// ============================================
// 提取答案文本（优先提取代码块原始文本，保留所有字符）
// ============================================
function extractAnswerText(element) {
  if (!element) return '';

  // 如果传入的是 .markdown 元素
  if (element.classList && element.classList.contains('markdown')) {
    // 1. 优先提取代码块内容（使用 textContent 保留原始转义）
    const codeBlock = element.querySelector('code-block code');
    if (codeBlock) {
      let codeText = codeBlock.textContent || '';
      // 去掉首尾多余的换行（但保留内部缩进）
      codeText = codeText.trim();
      console.log('[Extract] 提取代码块原始文本 (textContent)，长度:', codeText.length);
      return codeText;
    }

    // 2. 无代码块，提取普通文本（清理干扰元素）
    const clone = element.cloneNode(true);
    // 移除所有干扰元素：引用标记、按钮等
    const removals = clone.querySelectorAll(
      'source-footnote, sources-carousel-inline, response-element, button, [role="button"]'
    );
    for (const el of removals) {
      el.remove();
    }
    let text = clone.innerText || '';
    text = text.replace(/\n{3,}/g, '\n\n').trim();
    console.log('[Extract] 提取普通文本 (innerText)，长度:', text.length);
    return text;
  }

  // 若传入的是父容器，尝试找内部的 .markdown
  const markdown = element.querySelector('.markdown');
  if (markdown) {
    return extractAnswerText(markdown);
  }

  // 最终兜底
  let text = element.innerText || element.textContent || '';
  text = text.trim();
  console.warn('[Extract] 兜底提取，长度:', text.length);
  return text;
}

// ============================================
// 全局自动捕获
// ============================================
function initGlobalAutoCapture() {
  let globalObserver = new MutationObserver((mutations) => {
    if (!isWaitingForAnswer) {
      for (const mutation of mutations) {
        if (mutation.addedNodes.length > 0) {
          const latestCard = findAnswerElement(document.body, '');
          if (latestCard && latestCard !== currentAnswerElement) {
            console.log('[AutoCapture] 检测到新生成的答案卡片，自动开始捕获...');
            startListeningForAnswer('');
            break;
          }
        }
      }
    }
  });

  globalObserver.observe(document.body, { childList: true, subtree: true });
}

// ============================================
// 注入函数（含重试机制，专为 Gemini 输入框优化）
// ============================================
function injectToPage(text) {
  console.log('[Inject] 开始注入文本:', text);

  // 优先使用 Gemini 专属输入框选择器
  const selectors = [
    'div.ql-editor',                      // Gemini 最新输入框
    'rich-textarea .ql-editor',           // 备用
    '.ql-editor',                         // 通用 ql-editor
    '#prompt-textarea',                   // 旧版备用
    'div[contenteditable="true"]',        // 通用 contenteditable
    'div[role="textbox"]',                // 通用 role
    'textarea'                            // 最终兜底
  ];

  let attempts = 0;
  const maxAttempts = 5;
  let input = null;
  let resolved = false;

  function tryFindInput() {
    if (resolved) return;
    console.log(`[Inject] 第 ${attempts + 1} 次尝试查找输入框...`);
    for (const sel of selectors) {
      const el = document.querySelector(sel);
      if (el) {
        input = el;
        console.log(`[Inject] 选择器 "${sel}" 匹配到元素`);
        break;
      }
    }

    if (input) {
      console.log('[Inject] ✅ 找到输入框');
      resolved = true;
      doInject(input);
      return;
    }

    attempts++;
    if (attempts < maxAttempts) {
      console.log(`[Inject] 未找到输入框，${500}ms 后重试...`);
      setTimeout(tryFindInput, 500);
    } else {
      console.error('[Inject] ❌ 重试 5 次仍未找到输入框');
      const fb = document.getElementById('fb');
      if (fb) {
        fb.textContent = '❌ 未找到输入框，请刷新页面重试';
        fb.style.color = '#e74c3c';
      }
    }
  }

  function doInject(inputEl) {
    inputEl.focus();

    if (inputEl.tagName === 'TEXTAREA' || inputEl.tagName === 'INPUT') {
      inputEl.value = text;
    } else if (inputEl.hasAttribute('contenteditable') || inputEl.getAttribute('role') === 'textbox') {
      inputEl.innerText = text;
    } else {
      inputEl.value = text;
    }

    const events = ['input', 'change', 'keydown', 'keyup', 'paste'];
    events.forEach(evtType => {
      inputEl.dispatchEvent(new Event(evtType, { bubbles: true, cancelable: true }));
    });

    const compositionStart = new CompositionEvent('compositionstart', { bubbles: true });
    inputEl.dispatchEvent(compositionStart);
    const compositionEnd = new CompositionEvent('compositionend', { bubbles: true });
    inputEl.dispatchEvent(compositionEnd);

    // 查找发送按钮
    const btnSelectors = [
      'button[data-test-id="send-button"]',
      'button[aria-label="Send message"]',
      'button[aria-label="发送消息"]',
      'button[type="submit"]',
      '[data-testid="send-button"]',
      'button[aria-label*="Send"]',
      'button[aria-label*="发送"]',
      'button[class*="send"]',
      'div[role="button"][aria-label*="Send"]',
      'div[role="button"][aria-label*="发送"]'
    ];

    let sendBtn = null;
    for (const sel of btnSelectors) {
      const btn = document.querySelector(sel);
      if (btn && btn.offsetParent !== null) {
        sendBtn = btn;
        console.log(`[Inject] 找到发送按钮:`, btn);
        break;
      }
    }

    if (sendBtn) {
      if (sendBtn.hasAttribute('disabled')) sendBtn.removeAttribute('disabled');
      sendBtn.style.cursor = 'pointer';
      sendBtn.style.opacity = '1';
      setTimeout(() => { sendBtn.click(); }, 300);
    } else {
      console.warn('[Inject] ⚠️ 未找到发送按钮，将在 300ms 后模拟 Enter 键');
      setTimeout(() => {
        inputEl.dispatchEvent(new KeyboardEvent('keydown', {
          key: 'Enter', code: 'Enter', keyCode: 13, which: 13,
          bubbles: true, cancelable: true
        }));
      }, 300);
    }
  }

  tryFindInput();
  return true;
}

// ============================================
// 面板控制
// ============================================
function showPanel() {
  if (!panel) createPanel();
  panel.style.display = 'block';
  visible = true;
  connectPort();
}
function hidePanel() {
  if (panel) {
    panel.style.display = 'none';
    visible = false;
  }
}
function togglePanel() {
  visible ? hidePanel() : showPanel();
}

// ============================================
// 与 background 通信（带自动重连）
// ============================================
function connectPort() {
  if (port) {
    try { port.disconnect(); } catch (e) {}
    port = null;
  }

  port = chrome.runtime.connect({ name: 'panel' });

  port.onDisconnect.addListener(() => {
    console.log('[Content] Port 断开，尝试重连...');
    port = null;
    setTimeout(connectPort, 1000);
  });

  port.onMessage.addListener((msg) => {
    if (msg.type === 'init') {
      updateStatus(msg.connected);
      if (msg.history && msg.history.length > 0) {
        const last = msg.history[msg.history.length - 1];
        const text = typeof last === 'string' ? last : JSON.stringify(last);
        if (last && last.type === 'AI_RESULT') {
          document.getElementById('ai-feedback').value = text;
        } else {
          document.getElementById('content').value = text;
        }
      }
    } else if (msg.type === 'status') {
      updateStatus(msg.connected);
    } else if (msg.type === 'message') {
      const data = msg.data;
      const text = typeof data === 'string' ? data : JSON.stringify(data);
      if (data && data.type === 'AI_RESULT') {
        document.getElementById('ai-feedback').value = text;
      } else {
        document.getElementById('content').value = text;
      }
    }
  });

  chrome.runtime.sendMessage({ action: 'getStatus' }, (resp) => {
    if (resp) {
      updateStatus(resp.connected);
      if (resp.history && resp.history.length > 0) {
        const last = resp.history[resp.history.length - 1];
        const text = typeof last === 'string' ? last : JSON.stringify(last);
        if (last && last.type === 'AI_RESULT') {
          document.getElementById('ai-feedback').value = text;
        } else {
          document.getElementById('content').value = text;
        }
      }
    }
  });
}

function updateStatus(conn) {
  const dot = document.getElementById('dot');
  if (dot) {
    dot.style.background = conn ? '#4CAF50' : '#ccc';
  }
}

document.addEventListener('keydown', (e) => {
  if (e.ctrlKey && e.shiftKey && e.key === 'B') {
    e.preventDefault();
    togglePanel();
  }
});

chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (msg.type === 'togglePanel') {
    togglePanel();
    sendResponse({ success: true });
  }
});

createPanel();
initGlobalAutoCapture();
console.log('[Content] 智能桥接面板已加载（支持自动捕获 + port 自动重连），按 Ctrl+Shift+B 切换');