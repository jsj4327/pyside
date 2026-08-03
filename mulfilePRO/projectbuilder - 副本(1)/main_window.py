# main_window.py
import os
import sys
from PySide2.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QTabWidget,
    QApplication, QLabel, QMenuBar, QMenu, QAction,
    QMessageBox, QStatusBar
)
from PySide2.QtCore import Qt, QTimer
from PySide2.QtGui import QIcon, QKeySequence

from file_browser import FileBrowser
from file_browser_persistence import load_file_browser_settings, save_file_browser_settings
from code_diff import CodeDiff
from source_viewer.source_viewer_widget import SourceViewerWidget

# ---------- 容错导入分批复制模块 ----------
try:
    from batch_copy import BatchCopyWidget
    BATCH_COPY_AVAILABLE = True
except ImportError:
    BATCH_COPY_AVAILABLE = False
    from PySide2.QtWidgets import QWidget, QLabel, QVBoxLayout
    class BatchCopyWidget(QWidget):
        def __init__(self, parent=None):
            super().__init__(parent)
            layout = QVBoxLayout(self)
            label = QLabel("📦 分批复制模块未安装\n请创建 batch_copy 目录并放入相关文件")
            label.setAlignment(Qt.AlignCenter)
            label.setStyleSheet("color: #888; font-size: 16px;")
            layout.addWidget(label)
    print("⚠️ 分批复制模块未找到，使用占位组件。")


class MainWindow(QMainWindow):
    """
    主窗口类，界面大小为显示器宽度的85%，高度为可用屏幕高度的90%（避免遮挡任务栏）
    """

    def __init__(self):
        super().__init__()

        self.setWindowTitle("ProjectBuilder")
        self._setup_icon()
        self._setup_geometry()
        self._setup_central_widget()
        self._setup_ui()
        self._setup_menu()
        self._setup_statusbar()
        self._load_persistence()

    # ---------- 初始化 ----------
    def _setup_icon(self):
        current_dir = os.path.dirname(os.path.abspath(__file__))
        icon_path = os.path.join(current_dir, "projectbuilder.png")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

    def _setup_geometry(self):
        """窗口宽度为屏幕宽度的85%，高度为可用屏幕高度的90%（留出任务栏空间）"""
        screen = QApplication.primaryScreen()
        if screen:
            avail = screen.availableGeometry()
            width = int(avail.width() * 0.85)
            height = int(avail.height() * 0.90)  # 改为90%
            x = avail.x() + (avail.width() - width) // 2
            y = avail.y()  # 从可用区域顶部开始
            self.setGeometry(x, y, width, height)
            self.setMinimumSize(int(width * 0.6), int(height * 0.6))
        else:
            self.resize(1024, 768)

    def _setup_central_widget(self):
        central = QWidget()
        self.setCentralWidget(central)
        self._central_layout = QVBoxLayout(central)
        self._central_layout.setContentsMargins(5, 5, 5, 5)
        self._central_layout.setSpacing(5)

    def _setup_statusbar(self):
        self.statusBar().showMessage("就绪")

    # ---------- UI ----------
    def _setup_ui(self):
        self.tab_widget = QTabWidget()
        self.tab_widget.setTabsClosable(False)
        self.tab_widget.setMovable(True)
        self.tab_widget.setDocumentMode(True)

        # Tab1: 文件浏览器
        self.file_browser = FileBrowser(root_path=os.path.expanduser("~"))
        self.file_browser.path_changed.connect(self._on_path_changed)
        self.file_browser.file_double_clicked.connect(self._on_file_double_clicked)
        self.file_browser.file_selected.connect(self._on_file_selected)
        self.file_browser.folder_created.connect(self._on_folder_created)
        # 连接批量复制和代码合并信号
        self.file_browser.batch_copy_requested.connect(self._on_batch_copy_requested)
        self.file_browser.code_merge_requested.connect(self._on_code_merge_requested)

        # Tab2: 代码差异
        self.code_diff = CodeDiff()
        self.code_diff.compare_finished.connect(self._on_diff_finished)

        # Tab3: 源码浏览
        self.source_viewer_widget = SourceViewerWidget()
        tab3 = QWidget()
        tab3_layout = QVBoxLayout(tab3)
        tab3_layout.setContentsMargins(0, 0, 0, 0)
        tab3_layout.addWidget(self.source_viewer_widget)

        # Tab4: 分批复制
        self.batch_copy_widget = BatchCopyWidget()
        tab4_label = "📦 分批复制" if BATCH_COPY_AVAILABLE else "📦 分批复制 (不可用)"

        # Tab5: 代码合并（占位）
        self.code_merge_widget = QLabel("代码合并功能开发中\n\n请在此处集成您的合并工具")
        self.code_merge_widget.setAlignment(Qt.AlignCenter)
        self.code_merge_widget.setStyleSheet("color: #888; font-size: 16px;")

        # 添加所有标签页
        self.tab_widget.addTab(self.file_browser, "📁 文件浏览器")
        self.tab_widget.addTab(self.code_diff, "📊 代码差异")
        self.tab_widget.addTab(tab3, "📄 源码浏览")
        self.tab_widget.addTab(self.batch_copy_widget, tab4_label)
        self.tab_widget.addTab(self.code_merge_widget, "🔀 代码合并")

        self.tab_widget.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #d0d0d0;
                border-radius: 4px;
                background: white;
            }
            QTabBar::tab {
                padding: 8px 16px;
                margin-right: 2px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                background: #f0f0f0;
            }
            QTabBar::tab:selected {
                background: white;
                border: 1px solid #d0d0d0;
                border-bottom: none;
            }
            QTabBar::tab:hover:!selected {
                background: #e0e0e0;
            }
        """)

        self._central_layout.addWidget(self.tab_widget)

    # ---------- 菜单 ----------
    def _setup_menu(self):
        menubar = self.menuBar()

        file_menu = menubar.addMenu("文件(&F)")
        action_open = QAction("打开目录...", self)
        action_open.setShortcut(QKeySequence.Open)
        action_open.triggered.connect(self._on_menu_open_directory)
        file_menu.addAction(action_open)

        file_menu.addSeparator()
        action_refresh = QAction("刷新", self)
        action_refresh.setShortcut(QKeySequence.Refresh)
        action_refresh.triggered.connect(self._on_menu_refresh)
        file_menu.addAction(action_refresh)

        file_menu.addSeparator()
        action_exit = QAction("退出", self)
        action_exit.setShortcut(QKeySequence.Quit)
        action_exit.triggered.connect(self.close)
        file_menu.addAction(action_exit)

        view_menu = menubar.addMenu("视图(&V)")
        self.action_hidden = QAction("显示隐藏文件", self)
        self.action_hidden.setCheckable(True)
        self.action_hidden.setChecked(self.file_browser.show_hidden)
        self.action_hidden.triggered.connect(self._on_menu_hidden_toggled)
        view_menu.addAction(self.action_hidden)

        self.action_count_lines = QAction("统计代码行数", self)
        self.action_count_lines.setCheckable(True)
        self.action_count_lines.setChecked(self.file_browser.count_lines)
        self.action_count_lines.triggered.connect(self._on_menu_count_lines_toggled)
        view_menu.addAction(self.action_count_lines)

        view_menu.addSeparator()
        action_view_refresh = QAction("刷新", self)
        action_view_refresh.setShortcut("F5")
        action_view_refresh.triggered.connect(self._on_menu_refresh)
        view_menu.addAction(action_view_refresh)

        tools_menu = menubar.addMenu("工具(&T)")
        action_diff = QAction("代码差异比较", self)
        action_diff.setShortcut("Ctrl+D")
        action_diff.triggered.connect(self._on_menu_switch_to_diff)
        tools_menu.addAction(action_diff)

        help_menu = menubar.addMenu("帮助(&H)")
        action_about = QAction("关于", self)
        action_about.triggered.connect(self._on_menu_about)
        help_menu.addAction(action_about)

    # ---------- 持久化 ----------
    def _load_persistence(self):
        QTimer.singleShot(50, self._do_load_persistence)

    def _do_load_persistence(self):
        load_file_browser_settings(self.file_browser, "ProjectBuilder")
        self.statusBar().showMessage("✅ 配置已加载")

    def save_persistence(self):
        save_file_browser_settings(self.file_browser, "ProjectBuilder")
        print("✅ 配置已保存")

    def closeEvent(self, event):
        self.save_persistence()
        event.accept()

    # ---------- 菜单槽 ----------
    def _on_menu_open_directory(self):
        from PySide2.QtWidgets import QFileDialog
        path = QFileDialog.getExistingDirectory(
            self, "选择目录", self.file_browser.get_current_path()
        )
        if path:
            self.file_browser.load_directory(path)

    def _on_menu_refresh(self):
        current = self.tab_widget.currentIndex()
        if current == 0:
            self.file_browser.refresh()
            self.statusBar().showMessage("🔄 已刷新文件浏览器")
        elif current == 1:
            self.code_diff._perform_compare()
            self.statusBar().showMessage("🔄 已重新比对")

    def _on_menu_hidden_toggled(self, checked):
        self.file_browser.btn_hidden.setChecked(checked)
        self.action_hidden.setChecked(checked)

    def _on_menu_count_lines_toggled(self, checked):
        self.file_browser.btn_count_lines.setChecked(checked)
        self.action_count_lines.setChecked(checked)

    def _on_menu_switch_to_diff(self):
        self.tab_widget.setCurrentIndex(1)

    def _on_menu_about(self):
        QMessageBox.about(
            self,
            "关于 ProjectBuilder",
            "<h2>ProjectBuilder</h2><p>版本 1.0.0</p>"
            "<p>文件浏览器 + 代码差异 + 源码浏览 + 分批复制 + 代码合并</p>"
        )

    # ---------- 文件浏览器信号 ----------
    def _on_path_changed(self, path):
        self.statusBar().showMessage(f"📂 当前路径: {path}")

    def _on_file_selected(self, path):
        self.statusBar().showMessage(f"📄 选中: {os.path.basename(path)}")

    def _on_file_double_clicked(self, path):
        self.statusBar().showMessage(f"📄 打开文件: {os.path.basename(path)}")

        modifiers = QApplication.keyboardModifiers()
        if modifiers == Qt.ControlModifier:
            self.tab_widget.setCurrentIndex(2)
            if hasattr(self, 'source_viewer_widget'):
                self.source_viewer_widget.open_file(path)
            return

        if hasattr(self, 'code_diff'):
            self.code_diff.load_left_file(path)
        if self.tab_widget.currentIndex() != 1:
            self.tab_widget.setCurrentIndex(1)

    def _on_folder_created(self, path):
        self.statusBar().showMessage(f"📁 已创建文件夹: {os.path.basename(path)}")

    # ---------- 批量复制请求 ----------
    def _on_batch_copy_requested(self, path):
        self.tab_widget.setCurrentIndex(3)
        if hasattr(self, 'batch_copy_widget') and BATCH_COPY_AVAILABLE:
            self.batch_copy_widget.set_source_path(path)
            self.statusBar().showMessage(f"📦 已切换到分批复制，源路径: {path}")
        else:
            self.statusBar().showMessage("⚠️ 分批复制模块未安装，无法设置路径")

    # ---------- 代码合并请求 ----------
    def _on_code_merge_requested(self, path):
        self.tab_widget.setCurrentIndex(4)
        self.statusBar().showMessage(f"🔀 已切换到代码合并，当前路径: {path}")

    # ---------- 差异信号 ----------
    def _on_diff_finished(self, model):
        if model and model.is_processed:
            stats = model.statistics
            self.statusBar().showMessage(
                f"✅ 差异比对完成 | 相似度: {stats.similarity:.1f}% | "
                f"新增: {stats.inserted} | 删除: {stats.deleted} | 修改: {stats.modified}"
            )
        else:
            self.statusBar().showMessage("✅ 差异比对完成")

    # ---------- 键盘 ----------
    def keyPressEvent(self, event):
        if event.key() == Qt.Key_F5:
            self._on_menu_refresh()
        else:
            super().keyPressEvent(event)