# -*- coding: utf-8 -*-
"""Bridge 模块对外 API。"""
from PySide2.QtCore import QObject, Signal

from modules.bridge.domain.message import extract_files_payload
from modules.bridge.infrastructure.websocket_server import WebSocketBridgeServer


class BridgeApi(QObject):
    message_received = Signal(dict)
    files_received = Signal(list)

    def __init__(self, port=9002, parent=None):
        super().__init__(parent)
        self._server = WebSocketBridgeServer(port=port, parent=self)
        self._server.message_received.connect(self._on_raw_message)

    def _on_raw_message(self, data: dict):
        self.message_received.emit(data)
        files = extract_files_payload(data)
        if files:
            self.files_received.emit(files)

    def send_to_extension(self, text: str) -> None:
        self._server.send_text(text)