from PySide2.QtCore import QObject
from PySide2.QtWebSockets import QWebSocketServer, QWebSocket
from PySide2.QtNetwork import QHostAddress

class BridgeServer(QObject):
    def __init__(self, port=8765, parent=None):
        super().__init__(parent)
        self.server = QWebSocketServer("PDFReaderBridge", QWebSocketServer.NonSecureMode, self)
        self.port = port
        self.clients = []

    def start(self):
        if self.server.listen(QHostAddress.LocalHost, self.port):
            self.server.newConnection.connect(self.on_new_connection)
            print(f"WebSocket bridge started on ws://localhost:{self.port}")
        else:
            print(f"Failed to start WebSocket server on port {self.port}")

    def on_new_connection(self):
        client_socket = self.server.nextPendingConnection()
        client_socket.textMessageReceived.connect(lambda msg: self.handle_message(client_socket, msg))
        client_socket.disconnected.connect(lambda: self.handle_disconnection(client_socket))
        self.clients.append(client_socket)
        print(f"AI plugin connected: {client_socket.peerAddress().toString()}")

    def handle_message(self, client_socket: QWebSocket, message: str):
        print(f"Received from AI plugin: {message}")
        client_socket.sendTextMessage(f"Bridge acknowledged: {message}")

    def handle_disconnection(self, client_socket: QWebSocket):
        if client_socket in self.clients:
            self.clients.remove(client_socket)
        client_socket.deleteLater()
        print("AI plugin disconnected")