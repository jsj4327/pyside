# main_window.py
import os
import sys
from PySide2.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QTabWidget,
    QApplication, QLabel, QMenuBar, QMenu, QAction,
    QSplitter, QMessageBox, QStatusBar
)
from PySide2.QtCore import Qt, QTimer, QSettings
from PySide2.QtGui import QIcon, QKeySequence

from file_browser import FileBrowser
from file_browser_persistence import FileBrowserPersistence
from code_diff import CodeDiff
from source_viewer.source_viewer_widget import SourceViewerWidget


class MainWindow(QMainWindow):
    """
    主窗口类，界面大小为显示器尺寸的85%，居中显示
    不包含底部工具栏（任务栏）
    """

    def __init__(self):
        super().__init__()

        # 设置窗口标题
        self.setWindowTitle("ProjectBuilder")

        # 设置窗口图标
        self._setup_icon()

        # 设置窗口大小和位置
        self._setup_geometry()

        # 设置中心部件
        self._setup_central_widget()

        # 设置UI
        self._setup_ui()

        # 设置菜单栏
        self._setup_menu()

        # 设置状态栏
        self._setup_statusbar()

        # 恢复持久化状态
        self._load_persistence()

    # ==========================================
    # 初始化
    # ==========================================
    def _setup_icon(self):
        """设置窗口图标"""
        current_dir = os.path.dirname(os.path.abspath(__file__))
        icon_path = os.path.join(current_dir, "projectbuilder.png")

        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        else:
            pass

    def _setup_geometry(self):
        """设置窗口大小为显示器尺寸的85%，居中显示"""
        screen = QApplication.primaryScreen()
        if screen:
            available_geometry = screen.availableGeometry()
            width = int(available_geometry.width() * 0.85)
            height = int(available_geometry.height() * 0.85)
            x = available_geometry.x() + (available_geometry.width() - width) // 2
            y = available_geometry.y() + (available_geometry.height() - height) // 2
            self.setGeometry(x, y, width, height)
            self.setMinimumSize(int(width * 0.6), int(height * 0.6))
        else:
            self.resize(1024, 768)

    def _setup_central_widget(self):
        """设置中心部件"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        self._central_layout = QVBoxLayout(central_widget)
        self._central_layout.setContentsMargins(5, 5, 5, 5)
        self._central_layout.setSpacing(5)

    def _setup_statusbar(self):
        """设置状态栏"""
        self.statusBar().showMessage("就绪")

    # ==========================================
    # UI 布局
    # ==========================================
    def _setup_ui(self):
        """设置UI界面"""
        self.tab_widget = QTabWidget()
        self.tab_widget.setTabsClosable(False)
        self.tab_widget.setMovable(True)
        self.tab_widget.setDocumentMode(True)

        # ---- Tab1: 文件浏览器 ----
        self.file_browser = FileBrowser(root_path=os.path.expanduser("~"))
        self.file_browser.path_changed.connect(self._on_path_changed)
        self.file_browser.file_double_clicked.connect(self._on_file_double_clicked)
        self.file_browser.file_selected.connect(self._on_file_selected)
        self.file_browser.folder_created.connect(self._on_folder_created)

        # 连接信号到状态栏
        self.file_browser.path_changed.connect(
            lambda p: self.statusBar().showMessage(f"📂 当前路径: {p}")
        )
        self.file_browser.file_selected.connect(
            lambda p: self.statusBar().showMessage(f"📄 选中: {os.path.basename(p)}")
        )

        # ---- Tab2: 代码差异比较器 ----
        self.code_diff = CodeDiff()
        self.code_diff.compare_finished.connect(self._on_diff_finished)

        # 注意：此处不再直接将 file_double_clicked 绑定到 code_diff.load_left_file，
        # 而是统一由下方的 _on_file_double_clicked 槽函数来分发，以严格控制 Ctrl 拦截逻辑。
        # self.file_browser.file_double_clicked.connect(self.code_diff.load_left_file)

        # ---- Tab3: 源码浏览器 ----
        self.source_viewer_widget = SourceViewerWidget()
        tab3 = QWidget()
        tab3_layout = QVBoxLayout(tab3)
        tab3_layout.setContentsMargins(0, 0, 0, 0)
        tab3_layout.addWidget(self.source_viewer_widget)

        # ---- Tab4: 占位 ----
        tab4 = QWidget()
        tab4_layout = QVBoxLayout(tab4)
        tab4_layout.addWidget(QLabel("Tab 4 - 预留"))
        tab4_layout.addStretch()

        # 添加Tab
        self.tab_widget.addTab(self.file_browser, "📁 文件浏览器")
        self.tab_widget.addTab(self.code_diff, "📊 代码差异")
        self.tab_widget.addTab(tab3, "📄 源码浏览")
        self.tab_widget.addTab(tab4, "Tab 4")

        # 设置Tab样式
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

    # ==========================================
    # 菜单栏
    # ==========================================
    def _setup_menu(self):
        """设置菜单栏"""
        menubar = self.menuBar()

        # ---- 文件菜单 ----
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

        # ---- 视图菜单 ----
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

        # ---- 工具菜单 ----
        tools_menu = menubar.addMenu("工具(&T)")

        action_diff = QAction("代码差异比较", self)
        action_diff.setShortcut("Ctrl+D")
        action_diff.triggered.connect(self._on_menu_switch_to_diff)
        tools_menu.addAction(action_diff)

        # ---- 帮助菜单 ----
        help_menu = menubar.addMenu("帮助(&H)")

        action_about = QAction("关于", self)
        action_about.triggered.connect(self._on_menu_about)
        help_menu.addAction(action_about)

    # ==========================================
    # 持久化
    # ==========================================
    def _load_persistence(self):
        """加载持久化状态"""
        QTimer.singleShot(50, self._do_load_persistence)

    def _do_load_persistence(self):
        """执行加载持久化"""
        from file_browser_persistence import load_file_browser_settings
        load_file_browser_settings(self.file_browser, "ProjectBuilder")
        self.statusBar().showMessage("✅ 配置已加载")

    def save_persistence(self):
        """保存持久化状态"""
        from file_browser_persistence import save_file_browser_settings
        save_file_browser_settings(self.file_browser, "ProjectBuilder")
        print("✅ 配置已保存")

    def closeEvent(self, event):
        """窗口关闭事件 - 自动保存配置"""
        self.save_persistence()
        event.accept()

    # ==========================================
    # 菜单事件
    # ==========================================
    def _on_menu_open_directory(self):
        """菜单：打开目录"""
        from PySide2.QtWidgets import QFileDialog
        path = QFileDialog.getExistingDirectory(
            self,
            "选择目录",
            self.file_browser.get_current_path()
        )
        if path:
            self.file_browser.load_directory(path)

    def _on_menu_refresh(self):
        """菜单：刷新"""
        current_tab = self.tab_widget.currentIndex()
        if current_tab == 0:
            self.file_browser.refresh()
            self.statusBar().showMessage("🔄 已刷新文件浏览器")
        elif current_tab == 1:
            self.code_diff._perform_compare()
            self.statusBar().showMessage("🔄 已重新比对")

    def _on_menu_hidden_toggled(self, checked):
        """菜单：显示隐藏文件"""
        self.file_browser.btn_hidden.setChecked(checked)
        self.action_hidden.setChecked(checked)

    def _on_menu_count_lines_toggled(self, checked):
        """菜单：统计行数"""
        self.file_browser.btn_count_lines.setChecked(checked)
        self.action_count_lines.setChecked(checked)

    def _on_menu_switch_to_diff(self):
        """菜单：切换到差异比较"""
        self.tab_widget.setCurrentIndex(1)

    def _on_menu_about(self):
        """菜单：关于"""
        QMessageBox.about(
            self,
            "关于 ProjectBuilder",
            "<h2>ProjectBuilder</h2>"
            "<p>版本: 1.0.0</p>"
            "<p>一个集成了文件浏览器和代码差异比较器的开发工具</p>"
        )

    # ==========================================
    # 文件浏览器信号处理
    # ==========================================
    def _on_path_changed(self, path):
        """路径变更"""
        self.statusBar().showMessage(f"📂 当前路径: {path}")

    def _on_file_selected(self, path):
        """文件选中"""
        self.statusBar().showMessage(f"📄 选中: {os.path.basename(path)}")

    def _on_file_double_clicked(self, path):
        """文件双击 - 由文件浏览器触发"""
        self.statusBar().showMessage(f"📄 打开文件: {os.path.basename(path)}")

        # ---- 关键拦截：判断是否按下了 Ctrl 键 ----
        modifiers = QApplication.keyboardModifiers()
        if modifiers == Qt.ControlModifier:
            # 1. 切换到 Tab3 (源码浏览)
            self.tab_widget.setCurrentIndex(2)
            # 2. 加载文件到源码浏览器组件
            if hasattr(self, 'source_viewer_widget'):
                self.source_viewer_widget.open_file(path)
            # 3. 绝对拦截：直接 return，阻止触发后面的代码差异比对逻辑
            return

        # ---- 原有逻辑：未按 Ctrl 键时，正常走差异比较逻辑 ----
        # 加载文件到差异比较器左侧
        if hasattr(self, 'code_diff'):
            self.code_diff.load_left_file(path)
        # 自动切换到差异比较 Tab
        if self.tab_widget.currentIndex() != 1:
            self.tab_widget.setCurrentIndex(1)

    def _on_folder_created(self, path):
        """文件夹创建"""
        self.statusBar().showMessage(f"📁 已创建文件夹: {os.path.basename(path)}")

    # ==========================================
    # 代码差异信号处理
    # ==========================================
    def _on_diff_finished(self, model):
        """差异比对完成"""
        if model and model.is_processed:
            stats = model.statistics
            self.statusBar().showMessage(
                f"✅ 差异比对完成 | 相似度: {stats.similarity:.1f}% | "
                f"新增: {stats.inserted} | 删除: {stats.deleted} | 修改: {stats.modified}"
            )
        else:
            self.statusBar().showMessage("✅ 差异比对完成")

    # ==========================================
    # 键盘快捷键
    # ==========================================
    def keyPressEvent(self, event):
        """键盘事件"""
        if event.key() == Qt.Key_Escape:
            pass
        elif event.key() == Qt.Key_F5:
            self._on_menu_refresh()
        else:
            super().keyPressEvent(event)