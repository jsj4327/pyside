// content_script.js - 精准定位最新问题与流式接收 AI 回复（完整原版 + 自动捕获）

let visible = false, panel = null, port = null;
let observer = null;
let isWaitingForAnswer = false;
let answerCheckTimer = null;
let processedAnswerId = null;
let submittedText = ''; // 存储当前提交的问题文本

let pollingTimer = null;
let currentAnswerElement = null;
let lastExtractedText = '';
let stabilityTimer = null; // 用于检测流式输出是否结束的防抖定时器

// ============================================
// 创建面板
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

  // ---- 标题栏 ----
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

  // ---- 主体 ----
  const b = document.createElement('div');
  b.style.cssText = `padding:14px 16px 16px 16px;background:#fafafa;max-height:620px;overflow-y:auto;`;
  b.id = 'body';
  b.innerHTML = `
    <!-- 标签：请求 -->
    <div style="font-size:12px;font-weight:500;color:#888;margin-bottom:6px;">请求</div>

    <!-- 主文本框（请求） -->
    <textarea id="content" style="width:100%;height:80px;padding:8px 10px;border:1px solid #ddd;border-radius:6px;font-family:monospace;font-size:13px;resize:vertical;background:#fff;color:#333;box-sizing:border-box;outline:none;">等待接收请求...</textarea>

    <!-- 两个按钮 -->
    <div style="display:flex;gap:8px;margin-top:8px;margin-bottom:8px;">
      <button id="send-page" style="flex:1;padding:8px 0;background:#4CAF50;color:#fff;border:none;border-radius:6px;cursor:pointer;font-weight:500;font-size:13px;">📤 发送到页面</button>
      <button id="send-client" style="flex:1;padding:8px 0;background:#2196F3;color:#fff;border:none;border-radius:6px;cursor:pointer;font-weight:500;font-size:13px;">📤 发回到客户端</button>
    </div>

    <!-- ===== AI 反馈区域 ===== -->
    <div style="font-size:12px;font-weight:500;color:#888;margin-top:6px;margin-bottom:4px;">AI 反馈 (支持自动捕获)</div>
    <textarea id="ai-feedback" readonly style="width:100%;height:300px;padding:8px 10px;border:1px solid #ddd;border-radius:6px;font-family:monospace;font-size:13px;resize:vertical;background:#f9f9f9;color:#333;box-sizing:border-box;outline:none;">等待 AI 反馈...</textarea>

    <!-- 反馈 -->
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

  document.getElementById('toggle').addEventListener('click', () => {
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
  });

  document.getElementById('close').addEventListener('click', hidePanel);

  // ---- 发送到页面 ----
  document.getElementById('send-page').addEventListener('click', () => {
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
  });

  document.getElementById('send-client').addEventListener('click', () => {
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
  });
}

// ============================================
// 核心：AI 回复监听与流式接收（防抖与稳定性优化）
// ============================================

function startListeningForAnswer(questionText = '') {
  isWaitingForAnswer = true;
  processedAnswerId = null;
  lastExtractedText = '';

  // 清理旧的定时器与观察者
  stopListening();

  const statusEl = document.getElementById('fb');
  const feedbackEl = document.getElementById('ai-feedback');

  statusEl.textContent = '⏳ 正在监听 AI 响应...';
  statusEl.style.color = '#f39c12';

  // 创建 MutationObserver 实时捕获流式输出
  observer = new MutationObserver((mutations) => {
    if (!isWaitingForAnswer) return;

    // 尝试在页面中寻找或追踪当前的答案容器（支持问题匹配或自动抓取最新卡片）
    if (!currentAnswerElement || !document.body.contains(currentAnswerElement)) {
      currentAnswerElement = findAnswerElement(document.body, questionText);
    }

    if (currentAnswerElement) {
      const textContent = extractAnswerText(currentAnswerElement);
      
      // 如果提取到了有效内容
      if (textContent && textContent.trim().length > 0) {
        // 实时显示流式输出的内容
        feedbackEl.value = textContent;
        statusEl.textContent = '🔄 AI 正在流式输出...';
        statusEl.style.color = '#3498db';

        // 核心防抖逻辑：检测文本是否停止增长（即流式输出完毕）
        if (textContent !== lastExtractedText) {
          lastExtractedText = textContent;
          
          if (stabilityTimer) clearTimeout(stabilityTimer);
          
          // 如果 1.5 秒内文本没有再发生变化，则认为 AI 回复已完成
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

  // 超时处理（60秒未完成则强行收尾）
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

  // 启动辅助轮询
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
        
        // 重置防抖
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
// 核心：精准定位“刚发送的问题”或自动识别最新答案卡片
// ============================================

function findAnswerElement(root, questionText) {
  const answerSelectors = [
    '.answer-common-card',
    '[data-chat-answers-wrap]',
    '.chat-answers-card-wrap',
    '#qk-markdown-react'
  ];

  // 如果没有指定问题文本（例如用户在网页上直接手动发送），直接寻找页面中“最新生成”的答案卡片
  if (!questionText) {
    let allAnswers = [];
    for (const sel of answerSelectors) {
      const found = root.querySelectorAll ? root.querySelectorAll(sel) : [];
      if (found.length > 0) {
        allAnswers = Array.from(found);
        break;
      }
    }
    if (allAnswers.length > 0) {
      return allAnswers[allAnswers.length - 1]; // 返回最后一个（最新的）
    }
    return null;
  }

  // 1. 获取所有匹配的问题节点
  const questionSelectors = [
    '.chat-question-card-wrap',
    '.question-text-card'
  ];
  let matchedQuestions = [];

  for (const sel of questionSelectors) {
    const elements = root.querySelectorAll ? root.querySelectorAll(sel) : [];
    for (const el of elements) {
      const text = el.textContent.trim();
      if (text === questionText || text.includes(questionText) || questionText.includes(text)) {
        matchedQuestions.push(el);
      }
    }
  }

  if (matchedQuestions.length === 0) {
    // 降级：若未找到匹配问题，直接 fallback 到最新答案卡片
    return findAnswerElement(root, '');
  }

  // 2. 【关键】只取最后出现的一个（即刚刚最新发送的那条问题）
  const latestQuestion = matchedQuestions[matchedQuestions.length - 1];

  // 3. 从这个最新问题向上找到它的外层消息容器
  let container = latestQuestion.closest('.message-select-content-inner-QCE5NQ') ||
                  latestQuestion.closest('.message-select-content-MWGFKC');
  if (!container) {
    const questionWrap = latestQuestion.closest('.chat-question-wrap');
    if (questionWrap) {
      container = questionWrap.parentElement;
    }
  }

  // 定义在指定区域内提取答案的内部方法
  const extractFromContainer = (scopeNode) => {
    if (!scopeNode || !scopeNode.querySelector) return null;
    for (const sel of answerSelectors) {
      const answer = scopeNode.querySelector(sel);
      if (answer) {
        return answer;
      }
    }
    return null;
  };

  // 4. 优先在最新问题所属的容器内部或下方寻找答案
  if (container) {
    let ans = extractFromContainer(container);
    if (ans) return ans;

    let nextContainer = container.nextElementSibling;
    while (nextContainer) {
      ans = extractFromContainer(nextContainer);
      if (ans) return ans;
      nextContainer = nextContainer.nextElementSibling;
    }
  }

  // 5. 顺着最新问题的 DOM 节点往后遍历兄弟元素
  let sibling = latestQuestion.nextElementSibling;
  while (sibling) {
    const ans = extractFromContainer(sibling);
    if (ans) return ans;
    sibling = sibling.nextElementSibling;
  }

  // 6. 最终兜底
  return findAnswerElement(root, '');
}

// ============================================
// 全局自动捕获监听器（无需面板发送，网页新答案即自动捕获）
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
// 提取答案纯文本
// ============================================
function extractAnswerText(element) {
  if (!element) return '';
  let clone = element.cloneNode(true);

  const removeSelectors = [
    '.qk-md-table-action',
    '.qk-md-table-download-wrapper',
    '.qk-md-copy-icon',
    '[data-answer-feedback-toolbar]',
    '.share-selection-answer',
    '.message-select-wrapper-answer',
    'button',
    '[role="button"]',
    '.flex.items-center.gap-2',
    '.qk-md-table-action-bar',
    '.qk-md-table-download-menu'
  ];
  for (const sel of removeSelectors) {
    const items = clone.querySelectorAll ? clone.querySelectorAll(sel) : [];
    for (const item of items) {
      if (item.parentNode) {
        item.parentNode.removeChild(item);
      }
    }
  }

  // 处理代码块
  const codeBlocks = clone.querySelectorAll ? clone.querySelectorAll('.qw-md-code, .contain-layout-style') : [];
  for (const codeBlock of codeBlocks) {
    const langSpan = codeBlock.querySelector('.font-medium.mr-auto');
    const lang = langSpan ? langSpan.textContent.trim() : 'text';
    const codeElement = codeBlock.querySelector('code');
    let codeText = '';
    if (codeElement) {
      codeText = codeElement.textContent || '';
    }
    const wrapper = document.createElement('div');
    wrapper.textContent = `\n\n【代码块 ${lang}】\n${codeText.trim()}\n【代码块结束】\n\n`;
    codeBlock.parentNode.replaceChild(wrapper, codeBlock);
  }

  // 处理表格
  const tables = clone.querySelectorAll ? clone.querySelectorAll('.qk-md-table') : [];
  for (const table of tables) {
    let tableText = '\n';
    const rows = table.querySelectorAll('tr');
    for (const row of rows) {
      const cells = row.querySelectorAll('td, th');
      const cellTexts = [];
      for (const cell of cells) {
        cellTexts.push(cell.textContent.trim());
      }
      tableText += cellTexts.join(' | ') + '\n';
    }
    const wrapper = document.createElement('div');
    wrapper.textContent = '\n【表格】\n' + tableText + '【表格结束】\n';
    table.parentNode.replaceChild(wrapper, table);
  }

  let result = clone.textContent || '';
  result = result.replace(/\n{3,}/g, '\n\n');
  result = result.replace(/ {2,}/g, ' ');
  return result.trim();
}

// ============================================
// 注入函数
// ============================================
function injectToPage(text) {
  const selectors = [
    'div[role="textbox"][contenteditable="true"]',
    'div[role="textbox"]',
    '#prompt-textarea',
    'textarea',
    '[contenteditable="true"]'
  ];
  let input = null;
  for (const sel of selectors) {
    const el = document.querySelector(sel);
    if (el) { input = el; break; }
  }
  if (!input) {
    console.warn('[Inject] 未找到输入框');
    return false;
  }

  input.focus();

  if (input.tagName === 'TEXTAREA' || input.tagName === 'INPUT') {
    input.value = text;
  } else if (input.hasAttribute('contenteditable') || input.getAttribute('role') === 'textbox') {
    input.innerText = text;
  } else {
    input.value = text;
  }

  const events = ['input', 'change', 'keydown', 'keyup', 'paste'];
  events.forEach(evtType => {
    input.dispatchEvent(new Event(evtType, { bubbles: true, cancelable: true }));
  });

  const compositionStart = new CompositionEvent('compositionstart', { bubbles: true });
  input.dispatchEvent(compositionStart);
  const compositionEnd = new CompositionEvent('compositionend', { bubbles: true });
  input.dispatchEvent(compositionEnd);

  const btnSelectors = [
    'button[aria-label="发送消息"]',
    'button[type="submit"]',
    '[data-testid="send-button"]',
    'button[aria-label*="Send"]',
    'button[aria-label*="发送"]'
  ];
  let sendBtn = null;
  for (const sel of btnSelectors) {
    const btn = document.querySelector(sel);
    if (btn && btn.offsetParent !== null) {
      sendBtn = btn;
      break;
    }
  }

  if (sendBtn) {
    if (sendBtn.hasAttribute('disabled')) sendBtn.removeAttribute('disabled');
    sendBtn.style.cursor = 'pointer';
    sendBtn.style.opacity = '1';
    setTimeout(() => { sendBtn.click(); }, 300);
  } else {
    setTimeout(() => {
      input.dispatchEvent(new KeyboardEvent('keydown', {
        key: 'Enter', code: 'Enter', keyCode: 13, which: 13,
        bubbles: true, cancelable: true
      }));
    }, 300);
  }

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

function connectPort() {
  if (port) return;
  port = chrome.runtime.connect({ name: 'panel' });
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
  if (dot) dot.style.background = conn ? '#4CAF50' : '#ccc';
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
initGlobalAutoCapture(); // 启动全局自动捕获新卡片监听
console.log('[Content] 智能桥接面板已加载（支持自动捕获），按 Ctrl+Shift+B 切换');