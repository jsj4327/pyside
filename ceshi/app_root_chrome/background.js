// background.js - 增加心跳检测与状态同步

let ws = null;
let isConnected = false;
let history = [];
let panelPort = null;

// ---- 心跳相关变量 ----
let heartbeatInterval = null;      // 定时发送 ping 的间隔
let heartbeatTimeout = null;       // 等待 pong 的超时定时器
const HEARTBEAT_INTERVAL = 30000;  // 30 秒
const HEARTBEAT_TIMEOUT = 5000;    // 5 秒

// ============================================
// WebSocket 连接管理
// ============================================
function connect() {
  // 如果已有连接且处于打开或正在连接状态，则直接返回
  if (ws && (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING)) {
    return;
  }

  // 清理可能残留的定时器
  clearHeartbeatTimers();

  ws = new WebSocket('ws://127.0.0.1:9002');

  ws.onopen = () => {
    isConnected = true;
    sendToPanel({ type: 'status', connected: true });
    console.log('[BG] WebSocket 已连接');
    // 启动心跳检测
    startHeartbeat();
  };

  ws.onclose = () => {
    isConnected = false;
    sendToPanel({ type: 'status', connected: false });
    console.log('[BG] WebSocket 断开，3秒后重连');
    // 停止心跳
    clearHeartbeatTimers();
    // 3 秒后尝试重连
    setTimeout(connect, 3000);
  };

  ws.onerror = (err) => {
    console.error('[BG] WebSocket 错误:', err);
    // 发生错误时，主动关闭连接，触发 onclose
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.close();
    }
  };

  ws.onmessage = (e) => {
    try {
      const data = JSON.parse(e.data);
      // ---- 心跳响应检测 ----
      if (data.type === 'pong') {
        // 收到 pong，清除超时定时器
        if (heartbeatTimeout) {
          clearTimeout(heartbeatTimeout);
          heartbeatTimeout = null;
        }
        console.log('[BG] 收到心跳响应 (pong)');
        // 不将 pong 消息存入历史或转发给面板
        return;
      }

      // 非心跳消息：存入历史并转发给面板
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
  // 先清理可能残留的定时器
  clearHeartbeatTimers();

  // 首次发送 ping
  sendPing();

  // 定时发送 ping
  heartbeatInterval = setInterval(() => {
    sendPing();
  }, HEARTBEAT_INTERVAL);
}

function sendPing() {
  if (!ws || ws.readyState !== WebSocket.OPEN) {
    // 连接已断开，停止心跳
    clearHeartbeatTimers();
    return;
  }

  // 如果已有超时定时器，说明上次 ping 还没收到 pong，网络可能有问题
  if (heartbeatTimeout) {
    console.warn('[BG] 上次心跳未收到响应，主动关闭连接');
    ws.close(); // 触发 onclose，进而重连
    return;
  }

  try {
    ws.send(JSON.stringify({ type: 'ping' }));
    console.log('[BG] 发送心跳 (ping)');

    // 设置超时定时器
    heartbeatTimeout = setTimeout(() => {
      console.warn('[BG] 心跳超时，未收到 pong，主动关闭连接');
      if (ws && ws.readyState === WebSocket.OPEN) {
        ws.close(); // 触发 onclose，进而重连
      }
      heartbeatTimeout = null;
    }, HEARTBEAT_TIMEOUT);
  } catch (e) {
    console.error('[BG] 发送心跳失败:', e);
    // 发送失败也视为连接异常，关闭连接
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

// ============================================
// 监听面板连接
// ============================================
chrome.runtime.onConnect.addListener((port) => {
  if (port.name === 'panel') {
    panelPort = port;
    port.onDisconnect.addListener(() => { panelPort = null; });
    port.postMessage({ type: 'init', connected: isConnected, history });
  }
});

// ============================================
// 处理来自面板的消息
// ============================================
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
    // 手动重连：先关闭现有连接，然后调用 connect
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

// ============================================
// 点击扩展图标切换面板
// ============================================
chrome.action.onClicked.addListener((tab) => {
  chrome.tabs.sendMessage(tab.id, { type: 'togglePanel' });
});

// ============================================
// 启动连接
// ============================================
connect();
console.log('[BG] 后台服务已启动');