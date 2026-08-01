# main.py
import sys
from PySide2.QtWidgets import QApplication
from modules.shell.main_window import MainWindow
import modules.agent.infrastructure.prompt_engine
from modules.bridge.infrastructure.websocket_server import BridgeServer

def main():
    app = QApplication(sys.argv)
    
    # 1. 先创建主窗口（内部会完成事件监听和状态栏初始化）
    window = MainWindow()
    window.show()
    
    # 2. 后启动 WebSocket 服务（此时 UI 已就绪，能正确接收并显示状态广播）
    bridge_server = BridgeServer(port=9002)
    
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()