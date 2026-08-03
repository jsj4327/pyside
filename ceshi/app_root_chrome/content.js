let ws = null;
let isUiVisible = false;
let shadowHost = null;
let shadowRoot = null;

// WebSocket 初始化
function initWebSocket() {
    if (ws && (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING)) {
        return;
    }

    const WS_URL = "ws://127.0.0.1:9002";
    console.log("[插件] 正在连接...", WS_URL);
    
    ws = new WebSocket(WS_URL);

    ws.onopen = () => {
        updateStatus("🟢 已连接");
    };

    ws.onclose = () => {
        updateStatus("🔴 断开");
    };

    ws.onerror = (e) => {
        console.error("[插件] 错误", e);
        updateStatus("连接错误");
    };

    ws.onmessage = (event) => {
        try {
            const data = JSON.parse(event.data);
            console.log("[插件] 收到:", data);

            if (data.type === "ANALYZE_REQUEST") {
                const resultArea = shadowRoot ? shadowRoot.getElementById('aiResult') : null;
                if (resultArea) {
                    resultArea.value = `收到: ${data.filename}\n长度: ${data.content.length}\n模拟分析中...`;
                }
                
                // 模拟 AI 响应
                const mockResult = `[AI] 分析完成：文件 ${data.filename} 结构清晰。`;
                sendResultToPython(mockResult);
            }
        } catch (e) {
            console.error(e);
        }
    };
}

function sendResultToPython(text) {
    if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ type: "AI_RESULT", text: text }));
    }
}

// --- UI 构建逻辑 ---

function createShadowUI() {
    // 防止重复创建
    if (document.getElementById('my-extension-shadow-host')) {
        shadowHost = document.getElementById('my-extension-shadow-host');
        shadowRoot = shadowHost.shadowRoot;
        return;
    }

    shadowHost = document.createElement('div');
    shadowHost.id = 'my-extension-shadow-host';
    
    Object.assign(shadowHost.style, {
        position: 'fixed',
        top: '20px',
        right: '20px',
        zIndex: '2147483647',
        width: '320px'
    });
    
    document.body.appendChild(shadowHost);

    // 创建 Shadow DOM
    shadowRoot = shadowHost.attachShadow({ mode: 'open' });

    const template = `
        <style>
            :host { display: block; font-family: sans-serif; }
            .card {
                background: #ffffff;
                border: 1px solid #ccc;
                border-radius: 8px;
                box-shadow: 0 4px 12px rgba(0,0,0,0.2);
                padding: 16px;
            }
            h3 { margin: 0 0 10px; font-size: 16px; color: #333; }
            #status {
                padding: 6px; margin-bottom: 10px; border-radius: 4px; font-size: 12px; text-align: center;
            }
            .connected { background: #e6ffea; color: #00796b; }
            .disconnected { background: #ffebee; color: #c62828; }
            textarea {
                width: 100%; height: 120px; box-sizing: border-box; border: 1px solid #ddd; padding: 8px; border-radius: 4px; resize: none;
            }
            button {
                width: 100%; margin-top: 8px; padding: 8px; background-color: #007bff; color: white; border: none; border-radius: 4px; cursor: pointer;
            }
            button:hover { background-color: #0056b3; }
        </style>
        <div class="card">
            <h3>🤖 AI 助手</h3>
            <div id="status" class="disconnected">等待连接...</div>
            <textarea id="aiResult" readonly placeholder="分析结果..."></textarea>
            <button id="btnClose">关闭</button>
        </div>
    `;

    shadowRoot.innerHTML = template;

    // 绑定关闭按钮事件
    const closeBtn = shadowRoot.getElementById('btnClose');
    if (closeBtn) {
        closeBtn.addEventListener('click', () => {
            toggleUI(false);
        });
    }

    initWebSocket();
}

function toggleUI(forceState = null) {
    if (!shadowHost) {
        createShadowUI();
        isUiVisible = true;
        return;
    }

    if (forceState !== null) {
        isUiVisible = forceState;
    } else {
        isUiVisible = !isUiVisible;
    }

    shadowHost.style.display = isUiVisible ? 'block' : 'none';
}

function updateStatus(msg) {
    if (shadowRoot) {
        const el = shadowRoot.getElementById('status');
        if (el) {
            el.textContent = msg;
            el.className = msg.includes("已连接") ? "connected" : "disconnected";
        }
    }
}

// --- 消息监听 (核心修复) ---
// 使用 chrome.runtime.onMessage 监听来自 background.js 的指令

// 确保 DOM 加载完成
window.addEventListener('DOMContentLoaded', () => {
    console.log("[插件] Content Script Loaded");
});

// 监听指令
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.action === "TOGGLE_UI") {
        console.log("[插件] 收到切换指令");
        toggleUI();
        // 告诉 background 处理成功
        sendResponse({ status: "done" });
    }
});
