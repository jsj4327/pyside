// 定义一个常量标识，用于标记当前脚本的主世界版本或名称
const mainworld = "LIYIN"

// 在浏览器的开发者工具控制台中打印日志，确认脚本已经被成功注入并开始执行
console.log("【排查日志】content-script.js 开始执行");

// 使用立即执行函数表达式 (IIFE) 将整段代码包裹起来
// 这样做可以形成一个独立的作用域，避免脚本内部的变量和函数污染网页原本的全局环境
(function () {
  
  // 1. 防重复注入检查：检查当前网页中是否已经存在 ID 为 'ai-assistant-floating-panel' 的元素
  const existingPanel = document.getElementById('ai-assistant-floating-panel');
  if (existingPanel) {
    // 如果面板已经存在，说明之前已经注入过了，直接打印提示并终止后续代码执行，防止出现多个重复面板
    console.log("提示：面板已存在");
    return;
  }

  // 2. 创建悬浮面板的 DOM 容器元素 (div)
  const panel = document.createElement('div');
  panel.id = 'ai-assistant-floating-panel'; // 给面板赋予一个唯一的 ID
  
  // 使用模板字符串为面板内部填充详细的 HTML 结构（包含标题、状态栏、连接输入框、指令输入框、各种功能按钮和文本预览区）
  panel.innerHTML = `
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

  // 将创建好的整个悬浮面板追加到当前网页的 body 标签最后，使其显示在网页上
  document.body.appendChild(panel);

  // 定义核心变量
  let ws = null;                  // 用于保存 WebSocket 对象的变量
  let answerDebounceTimer = null; // 用于防抖的定时器变量
  let observer = null;            // 用于监听网页 DOM 变化的 MutationObserver 对象

  // 3. 手动连接 WebSocket 的核心函数
  function connectWebSocket() {
    // 获取用户在输入框中填写的 WebSocket 地址并去除前后空格
    const urlInput = document.getElementById('wsUrlInput').value.trim();
    // 获取显示连接状态的 span 标签
    const statusSpan = document.getElementById('wsStatus');

    // 如果地址为空，弹出提示并终止
    if (!urlInput) {
      alert("请输入有效的 WebSocket 地址");
      return;
    }

    // 如果之前已经存在一个连接实例，先尝试安全关闭它
    if (ws) {
      try { ws.close(); } catch (e) {}
    }

    // 改变状态显示为“连接中...”颜色变橙色
    statusSpan.style.color = 'orange';
    statusSpan.innerText = '[WebSocket: 连接中...]';

    try {
      // 实例化一个新的 WebSocket 连接，连向目标地址
      ws = new WebSocket(urlInput);

      // 当 WebSocket 连接成功建立时触发的回调函数
      ws.onopen = () => {
        statusSpan.style.color = 'limegreen';
        statusSpan.innerText = '[WebSocket: 已连接]';
      };

     // 当收到从 Python 端发来的消息时触发的回调函数
      ws.onmessage = (event) => {
        try {
          // 将收到的文本数据解析为 JSON 对象（确保格式正确）
          const data = JSON.parse(event.data);
          
          // 1. 将收到的完整 JSON 数据包格式化展示在面板的输入框中供预览
          const jsonString = typeof data === 'string' ? data : JSON.stringify(data, null, 2);
          document.getElementById('aiCommandInput').value = jsonString;

          // 2. 直接将整个 JSON 字符串（或你希望转发的内容）交给发送函数，不做任何子字段解析
          if (jsonString) {
            console.log("[WebSocket] 收到完整 JSON，直接转发给输入框并发送");
            executeSendAndMonitor(jsonString);
          }

        } catch (e) {
          console.error("[WebSocket] 解析消息失败:", e);
        }
      };

      // 当 WebSocket 连接断开时触发的回调函数
      ws.onclose = () => {
        statusSpan.style.color = 'red';
        statusSpan.innerText = '[WebSocket: 未连接]';
      };

      // 当 WebSocket 发生错误时触发的回调函数
      ws.onerror = (err) => {
        statusSpan.style.color = 'red';
        statusSpan.innerText = '[WebSocket: 连接错误]';
      };
    } catch (e) {
      statusSpan.style.color = 'red';
      statusSpan.innerText = '[WebSocket: 连接异常]';
    }
  }

  // 为面板上的“手动连接”按钮绑定点击事件，点击时调用 connectWebSocket 函数
  document.getElementById('wsConnectBtn').addEventListener('click', connectWebSocket);

  // 4. 悬浮窗拖拽移动功能的实现
  const header = document.getElementById('ai-panel-header'); // 获取面板头部作为拖拽手柄
  let isDragging = false, startX, startY, initialLeft, initialTop; // 定义拖拽状态和坐标变量
  
  // 鼠标移动时的处理函数
  function onMouseMove(e) {
    if (!isDragging) return; // 如果没有处于拖拽状态，直接返回
    // 根据鼠标移动的距离，实时计算并更新面板的新坐标位置
    panel.style.left = (initialLeft + (e.clientX - startX)) + 'px';
    panel.style.top = (initialTop + (e.clientY - startY)) + 'px';
  }
  
  // 鼠标松开时的处理函数
  function onMouseUp() {
    isDragging = false; // 结束拖拽状态
    // 移除全局的鼠标移动和松开监听器
    document.removeEventListener('mousemove', onMouseMove);
    document.removeEventListener('mouseup', onMouseUp);
  }

  // 当鼠标在面板头部按下时触发
  header.addEventListener('mousedown', (e) => {
    if (e.target.id === 'ai-close-btn') return; // 如果点击的是关闭按钮，不触发拖拽
    isDragging = true;                          // 标记开始拖拽
    startX = e.clientX; startY = e.clientY;     // 记录当前鼠标的初始屏幕坐标
    const rect = panel.getBoundingClientRect(); // 获取面板当前的矩形边界信息
    initialLeft = rect.left; initialTop = rect.top; // 记录面板当前的初始位置
    panel.style.position = 'fixed';             // 确保面板定位方式为 fixed
    panel.style.left = initialLeft + 'px';
    panel.style.top = initialTop + 'px';
    panel.style.right = 'auto';
    // 在整个文档上注册鼠标移动和松开事件，确保拖拽流畅
    document.addEventListener('mousemove', onMouseMove);
    document.addEventListener('mouseup', onMouseUp);
  });

  // 5. 点击关闭按钮的逻辑：执行彻底清理与卸载
  document.getElementById('ai-close-btn').addEventListener('click', () => {
    // 第一步：如果 WebSocket 正在连接，主动关闭它
    if (ws) {
      try { ws.close(); } catch (e) {}
    }

    // 第二步：断开并销毁 DOM 变动监听器
    if (observer) {
      observer.disconnect();
      observer = null;
    }

    // 第三步：清除可能残存的防抖定时器
    if (answerDebounceTimer) {
      clearTimeout(answerDebounceTimer);
    }

    // 第四步：从全局文档中移除残留的鼠标事件监听，防止内存泄漏
    document.removeEventListener('mousemove', onMouseMove);
    document.removeEventListener('mouseup', onMouseUp);

    // 第五步：将整个面板元素从网页 DOM 中彻底删除
    panel.remove();
    console.log("【排查日志】AI 助手面板已彻底卸载清理");
  });

  // 6. 自动操控网页输入与发送的函数
  function executeSendAndMonitor(textToSend) {
    // 精准定位网页中 DeepSeek 的聊天输入框
    const textarea = document.querySelector('textarea[name="search"][placeholder*="给 DeepSeek 发送消息"]');
    if (!textarea) return;

    textarea.focus(); // 让输入框获取焦点
    
    // 获取原生 textarea 的 value 属性设置器（用于绕过 React/Vue 等前端框架的劫持）
    const setter = Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, "value").set;
    if (setter) setter.call(textarea, textToSend); // 使用原生 setter 赋值
    else textarea.value = textToSend;

    // 派发一个浏览器的 input 事件，让网页前端框架“误以为”是用户在手动打字输入
    textarea.dispatchEvent(new InputEvent('input', { bubbles: true, cancelable: true, inputType: 'insertText', data: textToSend }));

    // 延迟 200 毫秒后执行提交动作
    setTimeout(() => {
      // 寻找网页的发送按钮
      const sendButton = document.querySelector('button[type="submit"]') || textarea.closest('form')?.querySelector('button');
      if (sendButton) {
        sendButton.click(); // 点击发送按钮
        startMonitoringAIAnswer(); // 开始监控 AI 的回复
      } else {
        // 如果找不到按钮，模拟触发键盘回车键 (Enter)
        textarea.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', code: 'Enter', keyCode: 13, which: 13, bubbles: true }));
        startMonitoringAIAnswer(); // 开始监控 AI 的回复
      }
    }, 200);
  }

  // 7. 核心解析函数：直接从网页渲染的文本段落中提取 files 数据（严格保留原始空白与格式，不做任何 trim 处理）
  function extractFilesData(rootElement) {
    let filesList = []; // 用于存放解析出来的文件对象数组

    try {
      // 优先寻找代码块 <pre> 或 <code>，因为它们最能完整保留 JSON 原始格式和空格/换行
      const codeBlocks = rootElement.querySelectorAll('pre, code, p.ds-markdown-paragraph, div.ds-markdown-paragraph');
      
      for (const block of codeBlocks) {
        // 使用 textContent 完整获取原始文本，不作任何 trim 或空白过滤
        let textContent = block.textContent;
        
        // 检查是否包含 "files" 关键字且结构符合 JSON
        if (textContent.includes('"files"') && textContent.includes('{')) {
          try {
            // 寻找文本中的 JSON 边界（截取从第一个 '{' 到最后一个 '}' 的原始内容）
            const firstIndex = textContent.indexOf('{');
            const lastIndex = textContent.lastIndexOf('}');
            if (firstIndex !== -1 && lastIndex !== -1 && lastIndex > firstIndex) {
              const jsonCandidate = textContent.substring(firstIndex, lastIndex + 1);
              
              const parsedData = JSON.parse(jsonCandidate);
              if (parsedData && Array.isArray(parsedData.files)) {
                filesList = parsedData.files;
                console.log("[Extension] 成功从文本段落中解析出 files 结构:", filesList.length, "个文件");
                break; // 成功解析一个完整 JSON 即可退出循环
              }
            }
          } catch (innerErr) {
            // 如果当前块解析失败，继续尝试下一个块
            continue;
          }
        }
      }

      // 兜底方案：如果从局部块没找到，直接在整个 rootElement 的 textContent 中进行匹配
      if (filesList.length === 0) {
        const fullText = rootElement.textContent; // 使用 textContent 保留原始转义和空白
        const jsonMatch = fullText.match(/\{[\s\S]*"files"\s*:\s*\[[\s\S]*\]\s*\}/);
        if (jsonMatch) {
          try {
            const parsedData = JSON.parse(jsonMatch[0]);
            if (parsedData && Array.isArray(parsedData.files)) {
              filesList = parsedData.files;
              console.log("[Extension] 通过正则兜底成功解析出 files 结构:", filesList.length, "个文件");
            }
          } catch (e) {
            console.error("[Extension] 兜底 JSON 解析失败:", e);
          }
        }
      }

    } catch (err) {
      console.error("[Extension] extractFilesData 执行异常:", err);
    }

    return filesList; // 返回的文件对象中包含的 code 字符串将完全保留其原样的换行与缩进
  }

  // 8. 实时监控 AI 回答的函数（使用 MutationObserver 变动观察器）
  function startMonitoringAIAnswer() {
    // 寻找网页聊天的虚拟列表容器
    const virtualList = document.querySelector('div.ds-virtual-list-visible-items');
    if (!virtualList) {
      // 如果还没加载出来，每隔 1 秒重试一次
      setTimeout(startMonitoringAIAnswer, 1000);
      return;
    }

    // 如果之前有旧的 observer，先断开它
    if (observer) observer.disconnect();

    // 创建一个新的变动观察器，当网页内容发生变化（AI 正在打字输出）时触发
    observer = new MutationObserver(() => {
      // 每次内容变动时，先清除上一次的防抖定时器，实现“停止输出 800ms 后才触发”
      if (answerDebounceTimer) clearTimeout(answerDebounceTimer);

      answerDebounceTimer = setTimeout(() => {
        // 获取所有 AI 回答的消息块
        const allAnswers = virtualList.querySelectorAll('div.ds-message._63c77b1');
        if (allAnswers.length > 0) {
          // 获取最新的一条回答
          const latestAnswer = allAnswers[allAnswers.length - 1];
          // 直接使用 textContent 保持原始文本的完整空格和缩进
          const rawAnswerText = latestAnswer.textContent;
          // 调用解析函数提取代码和文件名
          const filesData = extractFilesData(latestAnswer);

          // 拼接显示文本，展示在面板的预览区
          let summaryDisplay = rawAnswerText + "\n\n--- 【已解析的文件列表】 ---\n";
          filesData.forEach(f => {
            summaryDisplay += `文件: ${f.filename} (代码长度: ${f.code.length})\n`;
          });
          
          const answerArea = document.getElementById('aiAnswerArea');
          if (answerArea) answerArea.value = summaryDisplay;

          // 如果 WebSocket 处于连接状态，并且成功解析出了文件，则自动通过网络发送给 PySide 端
          if (ws && ws.readyState === WebSocket.OPEN && filesData.length > 0) {
            const payload = {
              action: "save_files_batch",
              files: filesData
            };
            ws.send(JSON.stringify(payload));
          }
        }
      }, 800); // 800 毫秒的防抖延迟
    });

    // 启动观察器，监听子节点、子树以及文本内容的变化
    observer.observe(virtualList, { childList: true, subtree: true, characterData: true });
  }

  // 9. 为面板上的“发送运行”按钮绑定点击事件
  document.getElementById('aiSendBtn').addEventListener('click', () => {
    const textInput = document.getElementById('aiCommandInput');
    if (!textInput) return;
    const textToSend = textInput.value.trim();
    if (!textToSend) return;
    executeSendAndMonitor(textToSend); // 触发发送和监控
  });

  // 10. 为面板上的“手动解析并发送代码文件”按钮绑定点击事件
  document.getElementById('aiFetchBtn').addEventListener('click', () => {
    const allAnswers = document.querySelectorAll('div.ds-message._63c77b1');
    if (allAnswers.length > 0) {
      const latestAnswer = allAnswers[allAnswers.length - 1];
      const filesData = extractFilesData(latestAnswer);
      
      const answerArea = document.getElementById('aiAnswerArea');
      if (answerArea) answerArea.value = JSON.stringify(filesData, null, 2);

      // 如果连接正常，手动发送给 PySide
      if (ws && ws.readyState === WebSocket.OPEN && filesData.length > 0) {
        ws.send(JSON.stringify({
          action: "save_files_batch",
          files: filesData
        }));
      }
    }
  });

})(); // 立即执行函数结束