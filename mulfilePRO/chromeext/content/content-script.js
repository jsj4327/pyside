console.log("【排查日志】content-script.js 开始执行");

(function () {
  if (document.getElementById('ai-assistant-floating-panel')) {
    console.log("提示：面板已存在，请勿重复创建");
    return;
  }

  const panel = document.createElement('div');
  panel.id = 'ai-assistant-floating-panel';
  panel.innerHTML = `
    <div id="ai-panel-header">
      <span>AI 助手 (PySide 文件同步版)</span>
      <span id="wsStatus" style="font-size: 11px; color: orange; margin-left: 8px;">[WebSocket: 连接中...]</span>
      <button id="ai-close-btn" style="background:none; border:none; font-size:18px; cursor:pointer; color:#666;">&times;</button>
    </div>
    <div id="ai-panel-body">
      <div class="input-group">
        <textarea id="aiCommandInput" placeholder="请输入要发送给 AI 的指令..." rows="3"></textarea>
      </div>
      <button id="aiSendBtn">发送运行</button>
      
      <hr style="margin: 12px 0; border: none; border-top: 1px solid #ddd; flex-shrink: 0;">

      <button id="aiFetchBtn" style="background-color: #28a745; margin-bottom: 8px; width: 100%; color: white; border: none; padding: 6px; cursor: pointer; border-radius: 4px; flex-shrink: 0;">手动解析并发送代码文件</button>
      <div class="input-group" style="flex: 1; display: flex; flex-direction: column; overflow: hidden;">
        <textarea id="aiAnswerArea" placeholder="解析出的文件与状态将显示在这里..." readonly></textarea>
      </div>
    </div>
  `;

  document.body.appendChild(panel);

  let ws = null;
  function initWebSocket() {
    ws = new WebSocket('ws://localhost:9002');
    const statusSpan = document.getElementById('wsStatus');

    ws.onopen = () => {
      if (statusSpan) {
        statusSpan.style.color = 'limegreen';
        statusSpan.innerText = '[WebSocket: 已连接]';
      }
    };

    ws.onmessage = (event) => {
      try {
        // 【核心修改】接收端不做内部字段提取，直接解析完整的 JSON 结构
        const data = JSON.parse(event.data);
        console.log("收到完整的消息结构:", data);

        // 如果你需要将收到的完整 JSON 或内容展示在文本框中，可按需处理
        // 例如：若你想把整个结构以 JSON 文本形式预览
        document.getElementById('aiCommandInput').value = typeof data === 'string' ? data : JSON.stringify(data, null, 2);

        // 如果标准 API 结构中包含 messages 且需要触发自动发送，可直接定位到对应的用户文本
        if (data.messages && Array.isArray(data.messages) && data.messages.length > 1) {
          const userMsg = data.messages.find(m => m.role === "user");
          if (userMsg && userMsg.content) {
            executeSendAndMonitor(userMsg.content);
          }
        } else if (data.content) {
          // 兼容纯文本或简易结构
          executeSendAndMonitor(data.content);
        }

      } catch (e) {
        console.error("[WebSocket] 解析消息失败:", e);
      }
    };

    ws.onclose = () => {
      if (statusSpan) {
        statusSpan.style.color = 'red';
        statusSpan.innerText = '[WebSocket: 未连接]';
      }
      setTimeout(initWebSocket, 3000);
    };

    ws.onerror = () => { ws.close(); };
  }

  initWebSocket();

  // 拖拽移动
  const header = document.getElementById('ai-panel-header');
  let isDragging = false, startX, startY, initialLeft, initialTop;
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

  document.getElementById('ai-close-btn').addEventListener('click', () => {
    if (ws) ws.close();
    panel.remove();
  });

  let answerDebounceTimer = null;
  let observer = null;

  function executeSendAndMonitor(textToSend) {
    const textarea = document.querySelector('textarea[name="search"][placeholder*="给 DeepSeek 发送消息"]');
    if (!textarea) return;

    textarea.focus();
    const setter = Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, "value").set;
    if (setter) setter.call(textarea, textToSend);
    else textarea.value = textToSend;

    textarea.dispatchEvent(new InputEvent('input', { bubbles: true, cancelable: true, inputType: 'insertText', data: textToSend }));

    setTimeout(() => {
      const sendButton = document.querySelector('button[type="submit"]') || textarea.closest('form')?.querySelector('button');
      if (sendButton) {
        sendButton.click();
        startMonitoringAIAnswer();
      } else {
        textarea.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', code: 'Enter', keyCode: 13, which: 13, bubbles: true }));
        startMonitoringAIAnswer();
      }
    }, 200);
  }

  // 核心：提取代码块与文件名并结构化打包
  function extractFilesData(rootElement) {
    const codeBlocks = rootElement.querySelectorAll('div.md-code-block.md-code-block-light');
    let filesList = [];

    codeBlocks.forEach((block, index) => {
      let fileName = `unnamed_file_${index + 1}.py`;
      
      // 寻找对应的 h3 文件名
      let current = block.previousElementSibling;
      while (current) {
        if (current.tagName === 'H3') {
          fileName = current.innerText.trim();
          break;
        }
        const h3Inside = current.querySelector('h3');
        if (h3Inside) {
          fileName = h3Inside.innerText.trim();
          break;
        }
        current = current.previousElementSibling;
      }

      if (fileName === `unnamed_file_${index + 1}.py`) {
        const parentContainer = block.closest('div.ds-message._63c77b1') || rootElement;
        const allH3 = parentContainer.querySelectorAll('h3');
        if (allH3.length > 0) {
          fileName = allH3[allH3.length > index ? index : allH3.length - 1].innerText.trim();
        }
      }

      const codeContent = block.innerText.trim();
      filesList.push({
        filename: fileName,
        code: codeContent
      });
    });

    return filesList;
  }

  function startMonitoringAIAnswer() {
    const virtualList = document.querySelector('div.ds-virtual-list-visible-items');
    if (!virtualList) {
      setTimeout(startMonitoringAIAnswer, 1000);
      return;
    }

    if (observer) observer.disconnect();

    observer = new MutationObserver(() => {
      if (answerDebounceTimer) clearTimeout(answerDebounceTimer);

      answerDebounceTimer = setTimeout(() => {
        const allAnswers = virtualList.querySelectorAll('div.ds-message._63c77b1');
        if (allAnswers.length > 0) {
          const latestAnswer = allAnswers[allAnswers.length - 1];
          const rawAnswerText = latestAnswer.innerText.trim();
          const filesData = extractFilesData(latestAnswer);

          // 显示在面板文本框
          let summaryDisplay = rawAnswerText + "\n\n--- 【已解析的文件列表】 ---\n";
          filesData.forEach(f => {
            summaryDisplay += `文件: ${f.filename} (代码长度: ${f.code.length})\n`;
          });
          document.getElementById('aiAnswerArea').value = summaryDisplay;

          // 通过专属协议发送给 PySide 端
          if (ws && ws.readyState === WebSocket.OPEN && filesData.length > 0) {
            const payload = {
              action: "save_files_batch",
              files: filesData
            };
            ws.send(JSON.stringify(payload));
            console.log("已通过 WebSocket 向 PySide 发送批量保存文件的指令", filesData);
          }
        }
      }, 800);
    });

    observer.observe(virtualList, { childList: true, subtree: true, characterData: true });
  }

  document.getElementById('aiSendBtn').addEventListener('click', () => {
    const textToSend = document.getElementById('aiCommandInput').value.trim();
    if (!textToSend) return;
    executeSendAndMonitor(textToSend);
  });

  document.getElementById('aiFetchBtn').addEventListener('click', () => {
    const allAnswers = document.querySelectorAll('div.ds-message._63c77b1');
    if (allAnswers.length > 0) {
      const latestAnswer = allAnswers[allAnswers.length - 1];
      const filesData = extractFilesData(latestAnswer);
      
      document.getElementById('aiAnswerArea').value = JSON.stringify(filesData, null, 2);

      if (ws && ws.readyState === WebSocket.OPEN && filesData.length > 0) {
        ws.send(JSON.stringify({
          action: "save_files_batch",
          files: filesData
        }));
      }
    }
  });

})();