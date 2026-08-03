# modules/bridge/infrastructure/websocket_server.py
import json
from PySide2.QtCore import QObject, Signal, Slot, QTimer
from PySide2.QtWebSockets import QWebSocketServer, QWebSocket
from PySide2.QtNetwork import QHostAddress
from shared.infrastructure.event_bus import event_bus

class BridgeServer(QObject):
    """WebSocket 通信桥梁服务端（带心跳保活与状态轮询）"""

    message_received = Signal(dict)

    def __init__(self, port=9002, parent=None):
        super().__init__(parent)
        self.server = QWebSocketServer(
            "PySideExtensionBridge", QWebSocketServer.NonSecureMode, self
        )
        self.clients = []

        # 尝试监听端口并记录状态
        self.is_running = self.server.listen(QHostAddress.LocalHost, port)
        if self.is_running:
            print(f"[WebSocket] 服务启动成功，监听端口: {port}")
            self.server.newConnection.connect(self._on_new_connection)
            
            # --- 新增：启动心跳与状态轮询定时器 ---
            self.heartbeat_timer = QTimer(self)
            self.heartbeat_timer.timeout.connect(self._check_connections)
            self.heartbeat_timer.start(3000)  # 每 3 秒轮询一次
        else:
            print(f"[WebSocket] 启动失败: {self.server.errorString()}")

        # 广播服务器整体运行状态
        event_bus.publish("bridge:server_status", {
            "is_running": self.is_running,
            "port": port,
            "error": "" if self.is_running else self.server.errorString()
        })

        # 初始化时广播初始未连接状态
        event_bus.publish("bridge:client_status", {"state": "init"})

        # 订阅下发指令事件
        event_bus.subscribe("bridge:send_to_extension", self._on_send_event)

    def _on_new_connection(self):
        client = self.server.nextPendingConnection()
        client.textMessageReceived.connect(self._on_text_received)
        
        # 修复：放弃 lambda，直接绑定槽函数，在槽函数内使用 self.sender() 获取对象
        client.disconnected.connect(self._on_disconnected)
        
        self.clients.append(client)
        print("[WebSocket] 浏览器插件已连接")
        event_bus.publish("bridge:client_status", {"state": "connected"})

    def _on_disconnected(self):
        """处理正常的断开事件"""
        client = self.sender()
        self._remove_client(client)

    def _check_connections(self):
        """主动轮询检查连接状态（心跳机制）"""
        for client in list(self.clients):
            # 1. 检查底层 socket 状态是否还处于连接中 (PySide2.QtNetwork.QAbstractSocket.ConnectedState 等于 3，或者直接用数值/跳过严格枚举检查)
            # 也可以通过判断 isValid() 来替代
            if not client.isValid():
                print("[WebSocket] 轮询检测到失效连接，执行清理")
                self._remove_client(client)
            else:
                # 2. 发送 ping 帧保持活跃
                client.ping()

    def _remove_client(self, client):
        """统一清理失效客户端，并触发 UI 更新"""
        if client in self.clients:
            self.clients.remove(client)
            client.deleteLater()
            print(f"[WebSocket] 客户端已移除，当前剩余连接数: {len(self.clients)}")
            
        # 只有当所有客户端都断开时，才向 UI 广播“断开”状态
        if len(self.clients) == 0:
            event_bus.publish("bridge:client_status", {"state": "disconnected"})

    def _on_text_received(self, message):
        # 无论内容是什么，先无条件在终端打印，确保能看到！
        print(f"[WebSocket 收到原始文本] 长度: {len(message)}, 内容预览: {message[:100]}...")
        
        try:
            # 尝试解析为 JSON
            data = json.loads(message)
            self.message_received.emit(data)
            event_bus.publish("bridge:message_received", data)
        except json.JSONDecodeError:
            # 如果不是 JSON，也通过事件总线把纯文本透传过去，并作为字典包装
            print(f"[WebSocket] 收到非 JSON 纯文本，执行兼容透传")
            event_bus.publish("bridge:message_received", {"payload": message})

    def _on_send_event(self, data: dict):
        text_msg = data.get("text", "")
        if text_msg:
            self.send_to_extension(text_msg)

    @Slot(str)
    def send_to_extension(self, text_msg):
        for client in self.clients:
            client.sendTextMessage(text_msg)
        print(f"[WebSocket] 已向插件发送文本指令: {text_msg}")