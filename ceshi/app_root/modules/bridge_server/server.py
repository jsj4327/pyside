# -*- coding:utf-8 -*-
import json
from PySide2.QtCore import QObject, Signal
from PySide2.QtNetwork import QHostAddress
# 【修复】从 QtWebSockets 导入，而不是 QtNetwork
from PySide2.QtWebSockets import QWebSocketServer, QWebSocket

class BridgeServer(QObject):
    """基于 Qt 原生 QWebSocketServer 的服务端"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # 初始化服务器，监听 ws:// 连接
        self.server = QWebSocketServer(
            "PySideExtensionBridge", 
            QWebSocketServer.NonSecureMode, 
            self
        )
        
        # 存储所有连接的客户端
        self.clients = []
        
        # 回调函数
        self.connection_callback = None
        self.message_callback = None

        # 【关键】绑定新连接信号
        self.server.newConnection.connect(self._on_new_connection)

    def listen(self, host, port, connection_callback=None, message_callback=None):
        """启动监听"""
        self.connection_callback = connection_callback
        self.message_callback = message_callback
        
        if self.server.listen(QHostAddress(host), port):
            print(f"[Bridge] 🚀 服务已启动在 ws://{host}:{port}")
            return True
        else:
            print(f"[Bridge] ❌ 启动失败: {self.server.errorString()}")
            return False

    def _on_new_connection(self):
        """处理新连接"""
        socket = self.server.nextPendingConnection()
        
        self.clients.append(socket)
        
        client_id = id(socket)
        print(f"[Bridge] 📥 客户端连接 ({client_id})")

        # 触发连接回调
        if self.connection_callback:
            self.connection_callback()

        # 绑定消息接收信号
        socket.textMessageReceived.connect(lambda msg: self._process_message(socket, msg))
        
        # 绑定断开连接信号
        socket.disconnected.connect(lambda: self._on_disconnected(socket))

    def _process_message(self, socket, message):
        """处理收到的消息"""
        try:
            data = json.loads(message)
            if self.message_callback:
                # 这里在主线程执行，可以直接操作 UI
                self.message_callback(data)
        except json.JSONDecodeError:
            print(f"[Bridge] JSON 解析错误: {message}")

    def _on_disconnected(self, socket):
        """处理断开连接"""
        if socket in self.clients:
            self.clients.remove(socket)
            # 资源清理
            socket.deleteLater()
            print(f"[Bridge] 📤 客户端断开 (剩余: {len(self.clients)})")

    def send_to_all_clients(self, data_dict):
        """
        【公共接口】向所有连接的客户端广播 JSON 消息
        """
        if not self.clients:
            return

        message = json.dumps(data_dict, ensure_ascii=False)
        
        # 遍历发送
        for client in self.clients:
            if client.state() == QWebSocket.ConnectedState:
                try:
                    client.sendTextMessage(message)
                except Exception as e:
                    print(f"[Bridge] 发送失败: {e}")

    def close(self):
        """停止服务"""
        for client in self.clients:
            client.close()
        self.server.close()
