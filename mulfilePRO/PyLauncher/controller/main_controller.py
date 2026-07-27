# -*- coding: utf-8 -*-

import os
from PySide2.QtWidgets import QFileDialog, QMessageBox
from PySide2.QtCore import QSettings

from model.project_model import ProjectModel
from service.scanner_service import ScannerService
from service.executor_service import ExecutorService

from view.main_window import MainWindow
from controller.editor_controller import EditorController

class MainController:
    """全局总控制器：管理 MVC 架构数据与事件流向"""

    def __init__(self):
        self.model = ProjectModel()
        self.scanner_service = ScannerService()
        self.executor_service = ExecutorService()
        self.view = MainWindow()
        self.editor_controller = EditorController(self.view.editor_view)

        # 初始化本地持久化配置
        self.settings = QSettings("PyLauncher", "ProjectState")

        self._init_global_connections()
        
        # 恢复上次打开的项目目录
        self._restore_last_session()

    def show(self):
        """显示主窗口界面"""
        self.view.show()

    def _init_global_connections(self):
        self.view.open_dir_requested.connect(self.handle_open_directory)
        self.model.project_path_changed.connect(lambda path: self.view.status_bar.showMessage(f"当前项目: {path}"))
        self.model.project_scanned.connect(lambda files, mains: self.view.runner_view.set_candidates(mains))

        self.view.project_tree.file_selected.connect(self.handle_file_selected)
        self.view.project_tree.file_double_clicked.connect(self.handle_file_double_clicked)
        
        self.view.runner_view.run_clicked.connect(self.handle_run_script)
        self.view.runner_view.stop_clicked.connect(self.executor_service.stop_script)
        self.executor_service.stdout_received.connect(self.view.console_view.append_log)
        self.executor_service.process_finished.connect(
            lambda code: self.view.console_view.append_log(f"\n[INFO] 进程运行结束，退出码: {code}\n")
        )

    def _restore_last_session(self):
        """从 QSettings 中恢复上一次保存的项目目录"""
        last_dir = self.settings.value("last_project_dir", "")
        if last_dir and os.path.exists(str(last_dir)):
            self._load_project_directory(str(last_dir))

    def handle_open_directory(self):
        dir_path = QFileDialog.getExistingDirectory(self.view, "选择 Python 项目根目录")
        if dir_path:
            self._load_project_directory(dir_path)

    def _load_project_directory(self, dir_path):
        """加载项目目录并持久化存储路径"""
        self.settings.setValue("last_project_dir", dir_path)
        self.model.current_project_dir = dir_path
        scan_result = self.scanner_service.scan_directory(dir_path)
        self.model.set_scan_results(scan_result["files"], scan_result["mains"])
        self.view.project_tree.load_directory(dir_path)

    def handle_file_selected(self, file_path):
        if file_path.endswith('.py'):
            project_dir = self.model.current_project_dir
            if project_dir and file_path.startswith(project_dir):
                rel_path = os.path.relpath(file_path, project_dir)
                self.view.runner_view.set_current_target(rel_path)

    def handle_file_double_clicked(self, file_path):
        self.view.right_tabs.setUpdatesEnabled(False)
        self.editor_controller.open_file(file_path)
        self.view.right_tabs.setCurrentIndex(1)
        self.view.right_tabs.setUpdatesEnabled(True)

    def handle_run_script(self, target, args_str):
        if not target:
            QMessageBox.warning(self.view, "提示", "请选择或输入要运行的 Python 文件！")
            return

        project_dir = self.model.current_project_dir
        if project_dir:
            full_script_path = os.path.join(project_dir, target)
            working_dir = project_dir
        else:
            full_script_path = target
            working_dir = os.path.dirname(target)

        if not os.path.exists(full_script_path):
            QMessageBox.critical(self.view, "错误", f"找不到运行目标: {full_script_path}")
            return

        args_list = args_str.split() if args_str else []

        self.view.right_tabs.setUpdatesEnabled(False)
        self.view.right_tabs.setCurrentIndex(0)
        self.view.console_view.append_log(f"{'='*50}\n[INFO] 正在启动: python3 {target} {' '.join(args_list)}\n")
        self.view.right_tabs.setUpdatesEnabled(True)

        self.executor_service.start_script(full_script_path, working_dir=working_dir, args=args_list)