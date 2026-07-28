// 1. 原有的发送逻辑
document.getElementById('sendBtn').addEventListener('click', () => {
  const textToSend = document.getElementById('commandInput').value.trim();
  if (!textToSend) {
    alert('请输入指令内容！');
    return;
  }

  chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
    if (!tabs || tabs.length === 0) return;
    
    chrome.scripting.executeScript({
      target: { tabId: tabs[0].id },
      func: injectAndSendAI,
      args: [textToSend]
    }, (results) => {
      if (chrome.runtime.lastError) {
        alert('发送失败: ' + chrome.runtime.lastError.message);
      } else {
        console.log("指令已成功发送");
      }
    });
  });
});

// 2. 查找与展示最后一次回答（已更新为你指定的 div 结构）
document.getElementById('fetchBtn').addEventListener('click', () => {
  chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
    if (!tabs || tabs.length === 0) return;
    
    chrome.scripting.executeScript({
      target: { tabId: tabs[0].id },
      func: extractLatestAnswerFromPage
    }, (results) => {
      if (chrome.runtime.lastError) {
        alert('查找失败: ' + chrome.runtime.lastError.message);
        return;
      }

      if (results && results[0] && results[0].result) {
        const answerText = results[0].result;
        document.getElementById('answerArea').value = answerText;
      } else {
        document.getElementById('answerArea').value = "未能在页面中找到目标回答，请确认 AI 已回复。";
      }
    });
  });
});

// ==================== 网页端执行函数 1：发送指令 ====================
function injectAndSendAI(commandText) {
  const textarea = document.querySelector('textarea[name="search"][placeholder*="给 DeepSeek 发送消息"]');
  
  if (!textarea) {
    alert('未能在当前页面找到 AI 输入框，请确保已打开聊天页面。');
    return;
  }

  textarea.focus();
  const nativeInputValueSetter = Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, "value").set;
  if (nativeInputValueSetter) {
    nativeInputValueSetter.call(textarea, commandText);
  } else {
    textarea.value = commandText;
  }

  const inputEvent = new InputEvent('input', {
    bubbles: true,
    cancelable: true,
    inputType: 'insertText',
    data: commandText
  });
  textarea.dispatchEvent(inputEvent);

  setTimeout(() => {
    const sendButton = document.querySelector('button[type="submit"]') || textarea.closest('form')?.querySelector('button');
    if (sendButton) {
      sendButton.click();
    } else {
      const enterEvent = new KeyboardEvent('keydown', {
        key: 'Enter', code: 'Enter', keyCode: 13, which: 13, bubbles: true
      });
      textarea.dispatchEvent(enterEvent);
    }
  }, 200);
}

// ==================== 网页端执行函数 2：精准解析你的目标 div ====================
function extractLatestAnswerFromPage() {
  // 精准匹配你提供的目标结构
  const allAnswers = document.querySelectorAll('div.ds-message._63c77b1');
  
  if (allAnswers.length > 0) {
    const latestAnswer = allAnswers[allAnswers.length - 1];
    return latestAnswer.innerText.trim();
  }
  
  return null;
}