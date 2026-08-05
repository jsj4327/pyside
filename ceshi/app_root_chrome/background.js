// background.js - V3 激进保活 + 主动检测 + 即时状态同步

let ws = null;
let isConnected = false;
let history = [];
let panelPort = null;

let heartbeatInterval = null;
let heartbeatTimeout = null;
const HEARTBEAT_INTERVAL = 10000; // 10 秒
const HEARTBEAT_TIMEOUT = 5000;

// ============================================
// 保持 Service Worker 活跃（每 12 秒唤醒）
// ============================================
chrome.alarms.create('keepAlive', { periodInMinutes: 0.2 }); // 12 秒，避免使用 periodInSeconds
chrome.alarms.onAlarm.addListener((alarm) => {
  if (alarm.name === 'keepAlive') {
    // 主动检查 WebSocket 状态
    if (!ws || ws.readyState !== WebSocket.OPEN) {
      if (isConnected) {
        isConnected = false;
        sendToPanel({ type: 'status', connected: false });
        console.log('[BG] 检测到连接断开，已发送断开状态');
      }
      if (ws) {
        try { ws.close(); } catch (e) {}
        ws = null;
      }
      connect();
    }
  }
});

// ============================================
// WebSocket 连接管理
// ============================================
function connect() {
  if (ws && (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING)) {
    return;
  }

  clearHeartbeatTimers();

  ws = new WebSocket('ws://127.0.0.1:9002');

  ws.onopen = () => {
    isConnected = true;
    sendToPanel({ type: 'status', connected: true });
    console.log('[BG] WebSocket 已连接');
    startHeartbeat();
  };

  ws.onclose = () => {
    isConnected = false;
    sendToPanel({ type: 'status', connected: false });
    console.log('[BG] WebSocket 断开，立即重连');
    clearHeartbeatTimers();
    setTimeout(connect, 500);
  };

  ws.onerror = (err) => {
    console.error('[BG] WebSocket 错误:', err);
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.close();
    }
  };

  ws.onmessage = (e) => {
    try {
      const data = JSON.parse(e.data);
      if (data.type === 'pong') {
        if (heartbeatTimeout) {
          clearTimeout(heartbeatTimeout);
          heartbeatTimeout = null;
        }
        console.log('[BG] 收到心跳响应 (pong)');
        return;
      }
      history.push(data);
      sendToPanel({ type: 'message', data });
    } catch (ex) {
      console.warn('[BG] 非 JSON 消息:', e.data);
    }
  };
}

// ============================================
// 心跳机制
// ============================================
function startHeartbeat() {
  clearHeartbeatTimers();
  sendPing();
  heartbeatInterval = setInterval(sendPing, HEARTBEAT_INTERVAL);
}

function sendPing() {
  if (!ws || ws.readyState !== WebSocket.OPEN) {
    clearHeartbeatTimers();
    return;
  }

  if (heartbeatTimeout) {
    console.warn('[BG] 上次心跳未收到响应，主动关闭连接');
    ws.close();
    return;
  }

  try {
    ws.send(JSON.stringify({ type: 'ping' }));
    console.log('[BG] 发送心跳 (ping)');
    heartbeatTimeout = setTimeout(() => {
      console.warn('[BG] 心跳超时，未收到 pong，主动关闭连接');
      if (ws && ws.readyState === WebSocket.OPEN) {
        ws.close();
      }
      heartbeatTimeout = null;
    }, HEARTBEAT_TIMEOUT);
  } catch (e) {
    console.error('[BG] 发送心跳失败:', e);
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.close();
    }
  }
}

function clearHeartbeatTimers() {
  if (heartbeatInterval) {
    clearInterval(heartbeatInterval);
    heartbeatInterval = null;
  }
  if (heartbeatTimeout) {
    clearTimeout(heartbeatTimeout);
    heartbeatTimeout = null;
  }
}

// ============================================
// 与面板通信
// ============================================
function sendToPanel(msg) {
  if (panelPort) panelPort.postMessage(msg);
}

chrome.runtime.onConnect.addListener((port) => {
  if (port.name === 'panel') {
    panelPort = port;
    port.onDisconnect.addListener(() => { panelPort = null; });
    port.postMessage({ type: 'init', connected: isConnected, history });
  }
});

chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === 'sendToClient') {
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify(request.payload));
      sendResponse({ success: true });
    } else {
      sendResponse({ success: false, error: 'WebSocket 未连接' });
    }
    return true;
  }
  if (request.action === 'getStatus') {
    sendResponse({ connected: isConnected, history });
    return true;
  }
  if (request.action === 'reconnect') {
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.close();
    } else {
      connect();
    }
    sendResponse({ success: true });
    return true;
  }
  if (request.action === 'clearHistory') {
    history = [];
    sendResponse({ success: true });
    return true;
  }
});

chrome.action.onClicked.addListener((tab) => {
  chrome.tabs.sendMessage(tab.id, { type: 'togglePanel' });
});

connect();
console.log('[BG] 后台服务已启动');