"""
主程序入口：设置 TabWidget 页面并启动应用程序
- 设为项目后同步源路径到「分批复制」「代码合并」
"""
import sys
from typing import List

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

        self.tabs = QTabWidget(self)

        self.picker = ProjectPickerWidget()
        self.content = ProjectContentWidget()
        self.batch_copier = BatchCopyWidget()
        self.code_merger = CodeMergerWidget()

        self.tabs.addTab(self.picker, "📁 项目选择")
        self.tabs.addTab(self.content, "📄 项目内容与架构")
        self.tabs.addTab(self.batch_copier, "📦 分批复制工具")
        self.tabs.addTab(self.code_merger, "🧩 代码合并工具")

        self.setCentralWidget(self.tabs)
        self.setStatusBar(QStatusBar())
        self.statusBar().showMessage("准备就绪")

        self.picker.project_selected.connect(self._on_project_selected)
        self.content.request_batch_copy.connect(self._on_request_batch_copy)
        
        # 绑定“一键代码合并”请求信号
        self.content.request_one_click_merge.connect(self._on_request_one_click_merge)

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
        """设为项目：打开内容页，并同步源路径到分批复制 / 代码合并"""
        if self.content.set_root_path(path):
            self.batch_copier.set_source_path(path)
            self.code_merger.set_source_path(path)
            self.statusBar().showMessage(
                f"已打开项目并同步源路径: {path}"
            )
            self.tabs.setCurrentIndex(1)

    def _on_request_batch_copy(self, path: str) -> None:
        """右键发送到分批复制：同时填成分批与合并的源路径"""
        self.batch_copier.set_source_path(path)
        self.code_merger.set_source_path(path)
        self.tabs.setCurrentIndex(2)
        self.statusBar().showMessage(f"已填入源路径: {path}")

    def _on_request_one_click_merge(self, folders: List[str]) -> None:
        """响应右键一键合并，触发合并逻辑并更新状态栏"""
        written = self.code_merger.do_one_click_merge(
            folders, project_root=self.content._current_path
        )
        if written:
            self.statusBar().showMessage(f"已成功一键合并并复制 {len(written)} 个文件。")


def main() -> None:
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    win.raise_()
    win.activateWindow()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()