# -*- coding: utf-8 -*-
"""
BigShrimp 程序总入口（组合根）。
调试启动：在项目根目录执行
  python main.py
"""
import os
import sys

_ROOT = os.path.dirname(os.path.abspath(__file__))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from PySide2.QtWidgets import QApplication

from modules.agent.api import AgentApi
from modules.bridge.api import BridgeApi
from modules.shell.main_window import MainWindow
from modules.workspace.api import WorkspaceApi


def main():
    app = QApplication(sys.argv)

    bridge = BridgeApi(port=9002)
    workspace = WorkspaceApi()
    agent = AgentApi()

    window = MainWindow(bridge=bridge, workspace=workspace, agent=agent)
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()