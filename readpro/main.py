# -*- coding: utf-8 -*-
"""
主程序入口：设置 TabWidget 页面并启动应用程序
"""
import sys

from batch_copy_widget import BatchCopyWidget
from merger_widget import CodeMergerWidget
from PySide2.QtGui import QGuiApplication
from PySide2.QtWidgets import QApplication, QMainWindow, QStatusBar, QTabWidget
from widgets import ProjectContentWidget, ProjectPickerWidget


class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()
        self.setWindowTitle("项目架构与分批复制/代码合并工具箱")
        self._place_window()

        # 创建 Tab 控件
        self.tabs = QTabWidget(self)

        self.picker = ProjectPickerWidget()
        self.content = ProjectContentWidget()
        self.batch_copier = BatchCopyWidget()
        self.code_merger = CodeMergerWidget()

        # 组装 4 个 Tab 页面
        self.tabs.addTab(self.picker, "📁 项目选择")
        self.tabs.addTab(self.content, "📄 项目内容与架构")
        self.tabs.addTab(self.batch_copier, "📦 分批复制工具")
        self.tabs.addTab(self.code_merger, "🧩 代码合并工具")

        self.setCentralWidget(self.tabs)

        self.setStatusBar(QStatusBar())
        self.statusBar().showMessage("准备就绪")

        # 绑定信号
        self.picker.project_selected.connect(self._on_project_selected)
        self.content.request_batch_copy.connect(self._on_request_batch_copy)

    def _place_window(self) -> None:
        screen = QGuiApplication.primaryScreen()
        if not screen:
            self.resize(1250, 780)
            return
        avail = screen.availableGeometry()
        w = int(avail.width() * 0.9)
        h = int(avail.height() * 0.9)
        x = avail.x() + (avail.width() - w) // 2
        y = avail.y() + (avail.height() - h) // 2
        self.setGeometry(x, y, w, h)

    def _on_project_selected(self, path: str) -> None:
        if self.content.set_root_path(path):
            self.statusBar().showMessage(f"已打开项目: {path}")
            self.tabs.setCurrentIndex(1)

    def _on_request_batch_copy(self, path: str) -> None:
        """从文件树右键菜单联动，可方便填入路径"""
        self.batch_copier.set_source_path(path)
        self.code_merger.set_source_path(path)
        self.tabs.setCurrentIndex(2)


def main() -> None:
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    win.raise_()
    win.activateWindow()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()