# -*- coding:utf-8 -*-
import json
from PySide2.QtCore import QObject, Signal
from PySide2.QtNetwork import QHostAddress, QAbstractSocket
from PySide2.QtWebSockets import QWebSocketServer, QWebSocket

class BridgeServer(QObject):
    """基于 Qt 原生 QWebSocketServer 的服务端"""

    def __init__(self, parent=None):
        super().__init__(parent)

        self.server = QWebSocketServer(
            "PySideExtensionBridge",
            QWebSocketServer.NonSecureMode,
            self
        )

        self.clients = []
        self.connection_callback = None
        self.message_callback = None

        self.server.newConnection.connect(self._on_new_connection)

    def listen(self, host, port, connection_callback=None, message_callback=None):
        self.connection_callback = connection_callback
        self.message_callback = message_callback

        if self.server.listen(QHostAddress(host), port):
            print(f"[Bridge] 🚀 服务已启动在 ws://{host}:{port}")
            return True
        else:
            print(f"[Bridge] ❌ 启动失败: {self.server.errorString()}")
            return False

    def _on_new_connection(self):
        socket = self.server.nextPendingConnection()
        self.clients.append(socket)
        client_id = id(socket)
        print(f"[Bridge] 📥 客户端连接 ({client_id})")

        if self.connection_callback:
            self.connection_callback()

        socket.textMessageReceived.connect(lambda msg: self._process_message(socket, msg))
        socket.disconnected.connect(lambda: self._on_disconnected(socket))

    def _process_message(self, socket, message):
        try:
            data = json.loads(message)
            
            # ============================================
            # 新增：处理前端发送的心跳 ping，立刻回复 pong
            # ============================================
            if isinstance(data, dict) and data.get("type") == "ping":
                pong_message = json.dumps({"type": "pong"}, ensure_ascii=False)
                if socket.state() == QAbstractSocket.ConnectedState:
                    socket.sendTextMessage(pong_message)
                return  # 拦截心跳消息，不往下走业务回调

            if self.message_callback:
                self.message_callback(data)
        except json.JSONDecodeError:
            print(f"[Bridge] JSON 解析错误: {message}")

    def _on_disconnected(self, socket):
        if socket in self.clients:
            self.clients.remove(socket)
            socket.deleteLater()
            print(f"[Bridge] 📤 客户端断开 (剩余: {len(self.clients)})")

    # ============================================
    # 修改后的广播发送函数（增强稳定性）
    # ============================================
    def send_to_all_clients(self, data_dict):
        """
        【公共接口】向所有连接的客户端广播 JSON 消息
        """
        if not self.clients:
            print("[Bridge] 没有客户端，跳过发送")
            return

        message = json.dumps(data_dict, ensure_ascii=False)

        # 遍历副本，防止修改列表导致问题
        for client in list(self.clients):
            if client.state() == QAbstractSocket.ConnectedState:
                try:
                    client.sendTextMessage(message)
                except Exception as e:
                    print(f"[Bridge] 发送给客户端 {id(client)} 失败: {e}")
                    # 可选：自动移除失效客户端（也可交由断开事件处理）
                    # if client in self.clients:
                    #     self.clients.remove(client)
            else:
                print(f"[Bridge] 客户端 {id(client)} 状态异常，移除")
                if client in self.clients:
                    self.clients.remove(client)

    def close(self):
        for client in self.clients:
            client.close()
        self.server.close()