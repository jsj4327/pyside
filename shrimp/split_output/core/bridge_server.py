# -*- coding: utf-8 -*-
import json
from PySide2.QtCore import QObject, Signal, Slot
from PySide2.QtNetwork import QHostAddress
from PySide2.QtWebSockets import QWebSocketServer


class BridgeServer(QObject):
    """WebSocket 通信桥梁服务端"""

    message_received = Signal(dict)
    log_message = Signal(str, str)  # (message, level)

    def __init__(self, port=9002, parent=None):
        super().__init__(parent)
        self.server = QWebSocketServer(
            "PySideExtensionBridge", QWebSocketServer.NonSecureMode, self
        )
        self.clients = []
        self.port = port

        if self.server.listen(QHostAddress.LocalHost, port):
            self.log_message.emit(f"服务启动成功，监听端口: {port}", "INFO")
            self.server.newConnection.connect(self._on_new_connection)
        else:
            self.log_message.emit(f"启动失败: {self.server.errorString()}", "ERROR")

    def _on_new_connection(self):
        client = self.server.nextPendingConnection()
        client.textMessageReceived.connect(self._on_text_received)
        client.disconnected.connect(lambda: self._on_disconnected(client))
        self.clients.append(client)
        self.log_message.emit("浏览器插件已连接", "INFO")

    def _on_text_received(self, message):
        try:
            data = json.loads(message)
            self.message_received.emit(data)
        except json.JSONDecodeError:
            self.log_message.emit(f"无法解析的非 JSON 消息: {message}", "WARN")

    def _on_disconnected(self, client):
        if client in self.clients:
            self.clients.remove(client)
            client.deleteLater()
            self.log_message.emit("浏览器插件已断开", "INFO")

    @Slot(str)
    def send_to_extension(self, text_msg):
        for client in self.clients:
            client.sendTextMessage(text_msg)
        self.log_message.emit(f"已向插件发送文本指令", "SEND")
