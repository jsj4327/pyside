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
        self.disconnection_callback = None   # 新增
        self.message_callback = None

        self.server.newConnection.connect(self._on_new_connection)

    def listen(self, host, port, connection_callback=None, disconnection_callback=None, message_callback=None):
        self.connection_callback = connection_callback
        self.disconnection_callback = disconnection_callback
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

        # 连接回调，传递当前连接数
        if self.connection_callback:
            self.connection_callback(len(self.clients))

        socket.textMessageReceived.connect(lambda msg: self._process_message(socket, msg))
        socket.disconnected.connect(lambda: self._on_disconnected(socket))

    def _process_message(self, socket, message):
        try:
            data = json.loads(message)
            # 处理 ping
            if isinstance(data, dict) and data.get("type") == "ping":
                pong_message = json.dumps({"type": "pong"}, ensure_ascii=False)
                if socket.state() == QAbstractSocket.ConnectedState:
                    socket.sendTextMessage(pong_message)
                return

            if self.message_callback:
                self.message_callback(data)
        except json.JSONDecodeError:
            print(f"[Bridge] JSON 解析错误: {message}")

    def _on_disconnected(self, socket):
        if socket in self.clients:
            self.clients.remove(socket)
            socket.deleteLater()
            print(f"[Bridge] 📤 客户端断开 (剩余: {len(self.clients)})")

        # 断开回调，传递剩余连接数
        if self.disconnection_callback:
            self.disconnection_callback(len(self.clients))

    def send_to_all_clients(self, data_dict):
        if not self.clients:
            print("[Bridge] 没有客户端，跳过发送")
            return

        message = json.dumps(data_dict, ensure_ascii=False)

        for client in list(self.clients):
            if client.state() == QAbstractSocket.ConnectedState:
                try:
                    client.sendTextMessage(message)
                except Exception as e:
                    print(f"[Bridge] 发送给客户端 {id(client)} 失败: {e}")
            else:
                print(f"[Bridge] 客户端 {id(client)} 状态异常，移除")
                if client in self.clients:
                    self.clients.remove(client)

    def close(self):
        for client in self.clients:
            client.close()
        self.server.close()

    def is_listening(self):
        return self.server.isListening()