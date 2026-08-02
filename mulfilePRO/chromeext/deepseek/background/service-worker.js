// ==========================================
// 1. 图标点击：动态注入 CSS 和 Content Script
// ==========================================
chrome.action.onClicked.addListener(async (tab) => {
  console.log("【排查日志】捕获到图标点击事件！Tab ID:", tab.id);
  
  if (!tab.id) return;
  
  try {
    // 1. 强行注入 CSS 样式
    await chrome.scripting.insertCSS({
      target: { tabId: tab.id },
      files: ["content/content-style.css"]
    });
    console.log("【排查日志】CSS 样式注入成功");
  } catch (error) {
    console.warn("【排查日志】CSS 注入失败:", error.message);
  }

  try {
    // 2. 注入 JavaScript 逻辑
    // 注意：不要使用 world: "MAIN"，保持默认的 ISOLATED 环境，以便能够访问 chrome.runtime 接口
    await chrome.scripting.executeScript({
      target: { tabId: tab.id },
      files: ["content/content-script.js"]
      //  files: ["content/content-script-deepseek.js"]
    });
    console.log("【排查日志】JS 逻辑注入成功");
  } catch (error) {
    console.error("【排查日志】JS 注入失败:", error.message);
  }
});

// ==========================================
// 2. WebSocket 管理与通信中转
// ==========================================
let ws = null;

function initWebSocket(wsUrl, tabId) {
  if (ws) {
    try { ws.close(); } catch (e) {}
  }

  try {
    ws = new WebSocket(wsUrl || "ws://localhost:9002");

    ws.onopen = () => {
      console.log("[Service Worker] WebSocket 成功连接至 PySide 服务端");
      notifyTab(tabId, { type: "WS_STATUS", status: "connected" });
    };

    ws.onmessage = (event) => {
      console.log("[Service Worker] 收到 PySide 消息，准备转发给前端:", event.data);
      notifyTab(tabId, {
        type: "WS_RECEIVED_DATA",
        data: event.data
      });
    };

    ws.onclose = () => {
      console.log("[Service Worker] WebSocket 已断开");
      notifyTab(tabId, { type: "WS_STATUS", status: "disconnected" });
    };

    ws.onerror = (err) => {
      console.error("[Service Worker] WebSocket 出错:", err);
      notifyTab(tabId, { type: "WS_STATUS", status: "error" });
    };
  } catch (e) {
    console.error("[Service Worker] WebSocket 创建失败:", e);
    notifyTab(tabId, { type: "WS_STATUS", status: "error" });
  }
}

function notifyTab(tabId, message) {
  if (tabId) {
    chrome.tabs.sendMessage(tabId, message).catch(() => {});
  } else {
    chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
      if (tabs[0]?.id) {
        chrome.tabs.sendMessage(tabs[0].id, message).catch(() => {});
      }
    });
  }
}

// 监听来自 content-script 的消息请求
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  const tabId = sender.tab?.id;

  if (request.type === "CONNECT_WS") {
    initWebSocket(request.url, tabId);
    sendResponse({ status: "processing" });
  } 
  else if (request.type === "SEND_WS_DATA") {
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify(request.payload));
      sendResponse({ status: "success" });
    } else {
      sendResponse({ status: "error", message: "WebSocket 未连接或处于断开状态" });
    }
  }
  return true;
});
