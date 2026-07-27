# -*- coding: utf-8 -*-
import sys
import json
from PySide2.QtWidgets import QApplication, QWidget, QVBoxLayout, QTextEdit
from PySide2.QtCore import QObject, Signal, Slot
from PySide2.QtWebSockets import QWebSocketServer, QWebSocket
from PySide2.QtNetwork import QHostAddress

class BridgeServer(QObject):
    """WebSocket 通信桥梁服务端"""
    message_received = Signal(dict)

    def __init__(self, port=9002, parent=None):
        super().__init__(parent)
        # 创建非加密 WebSocket 服务器
        self.server = QWebSocketServer("PySideExtensionBridge", QWebSocketServer.NonSecureMode, self)
        self.clients = []

        if self.server.listen(QHostAddress.LocalHost, port):
            print(f"[WebSocket] 服务启动成功，监听端口: {port}")
            self.server.newConnection.connect(self._on_new_connection)
        else:
            print(f"[WebSocket] 启动失败: {self.server.errorString()}")

    def _on_new_connection(self):
        client = self.server.nextPendingConnection()
        client.textMessageReceived.connect(self._on_text_received)
        client.disconnected.connect(lambda: self._on_disconnected(client))
        self.clients.append(client)
        print("[WebSocket] 浏览器插件已连接")

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

    @Slot(dict)
    def send_to_extension(self, data_dict):
        """向所有已连接的插件推送数据"""
        msg = json.dumps(data_dict, ensure_ascii=False)
        for client in self.clients:
            client.sendTextMessage(msg)


# UI 测试窗口
class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PySide 与 浏览器插件通信演示")
        self.resize(500, 300)

        layout = QVBoxLayout(self)
        self.log_view = QTextEdit(self)
        self.log_view.setReadOnly(True)
        layout.addWidget(self.log_view)

        # 启动 WebSocket 服务
        self.bridge = BridgeServer(port=9002, parent=self)
        self.bridge.message_received.connect(self.handle_extension_message)

    def handle_extension_message(self, data):
        self.log_view.append(f"收到插件消息: {data}")
        
        # 收到消息后，回传一个响应给插件
        response = {"status": "ok", "action": "reply", "received": data}
        self.bridge.send_to_extension(response)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())