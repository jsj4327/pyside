# -*- coding:utf-8 -*-
import sys
import os
BASE_PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_PROJECT_DIR not in sys.path: sys.path.insert(0, BASE_PROJECT_DIR)

from PySide2.QtWidgets import QApplication
from PySide2.QtGui import QFont
from windows import MainAppWindow
from modules.bridge_server import BridgeServer

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    
    # 字体设置
    font = QFont()
    for font_name in ["WenQuanYi Micro Hei", "Noto Sans CJK SC", "SimHei"]:
        if QFont(font_name).exactMatch(): font = QFont(font_name, 10); break
    app.setFont(font)

    window = MainAppWindow()

    # --- 启动 WebSocket Bridge 服务 ---
    try:
        # 定义消息回调
        def on_message_callback(data):
            window.on_browser_message(data)

        # 定义断开回调
        def on_disconnection_callback(count):
            window.on_plugin_disconnected(count)

        bridge = BridgeServer(parent=window)
        success = bridge.listen(
            host='127.0.0.1', 
            port=9002,
            connection_callback=window.on_plugin_connected,
            disconnection_callback=on_disconnection_callback,  # 新增
            message_callback=on_message_callback
        )

        if success:
            window.bridge_server = bridge
            # 初始状态：运行中，连接数0
            window.set_bridge_status(True, 9002, 0)
        else:
            window.set_bridge_status(False)

    except Exception as e:
        print(f"[Main] 未知错误: {e}")
        window.set_bridge_status(False)

    window.show()
    sys.exit(app.exec_())