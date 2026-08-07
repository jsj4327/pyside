# -*- coding: utf_8 -*-
import sys
from PySide2.QtWidgets import QApplication
from ui.main__window import MainWindow
from bridge.websocket_server import BridgeServer

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # 启动 Qt WebSocket Bridge
    bridge = BridgeServer()
    bridge.start()
    
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())