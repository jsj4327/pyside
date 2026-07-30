# -*- coding: utf-8 -*-
"""Bridge 外层：QWebSocketServer。"""
import json

from PySide2.QtCore import QObject, Signal, Slot
from PySide2.QtNetwork import QHostAddress
from PySide2.QtWebSockets import QWebSocketServer


class WebSocketBridgeServer(QObject):
    """与浏览器插件通信的 WebSocket 服务端。"""

    message_received = Signal(dict)
    client_connected = Signal()
    client_disconnected = Signal()
    server_failed = Signal(str)

    def __init__(self, port=9002, parent=None):
        super().__init__(parent)
        self._port = port
        self.server = QWebSocketServer(
            "PySideExtensionBridge",
            QWebSocketServer.NonSecureMode,
            self,
        )
        self.clients = []

        if self.server.listen(QHostAddress.LocalHost, port):
            print(f"[WebSocket] 服务启动成功，监听端口: {port}")
            self.server.newConnection.connect(self._on_new_connection)
        else:
            err = self.server.errorString()
            print(f"[WebSocket] 启动失败: {err}")
            self.server_failed.emit(err)

    def _on_new_connection(self):
        client = self.server.nextPendingConnection()
        client.textMessageReceived.connect(self._on_text_received)
        client.disconnected.connect(lambda: self._on_disconnected(client))
        self.clients.append(client)
        print("[WebSocket] 浏览器插件已连接")
        self.client_connected.emit()

    def _on_text_received(self, message):
        try:
            data = json.loads(message)
            self.message_received.emit(data)
        except json.JSONDecodeError:
            print(f"[WebSocket] 无法解析的非 JSON 消息: {message}")

    def _on_disconnected(self, client):
        if client in self.clients:
            self.clients.remove(client)
            client.deleteLater()
        print("[WebSocket] 浏览器插件已断开")
        self.client_disconnected.emit()

    @Slot(str)
    def send_text(self, text_msg: str):
        for client in self.clients:
            client.sendTextMessage(text_msg)
        print(f"[WebSocket] 已向插件发送文本指令: {text_msg}")