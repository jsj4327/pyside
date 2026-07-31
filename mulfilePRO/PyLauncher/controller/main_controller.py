import os
import ast
import sys
import shlex
import subprocess
from PySide2.QtCore import QSettings, QByteArray
from PySide2.QtWidgets import QFileDialog


class MainController:
    """主控制器：处理信号联动、QSettings 全局持久化与多进程直接一键启动"""

    def __init__(self, main_window):
        self.main_window = main_window
        self.project_tree = main_window.project_tree
        self.runner_view = main_window.runner_view
        self.editor_view = main_window.editor_view

        self.settings = QSettings("PyLauncherOrg", "PyLauncherIDE")
        self._current_project_dir = ""

        self._bind_signals()
        self.restore_settings()

    def _bind_signals(self):
        """绑定所有视图与控制逻辑"""
        # 1. 打开项目目录
        self.main_window.open_dir_requested.connect(self.on_open_directory)

        # 2. 文件树【单击】py文件 -> 自动传递给运行入口脚本框
        self.project_tree.file_selected.connect(self.on_file_selected)

        # 3. 文件树【双击】py文件 -> 打开源码编辑器
        self.project_tree.file_double_clicked.connect(self.on_file_double_clicked)

        # 4. 源码编辑器保存与运行
        self.editor_view.save_requested.connect(self.on_save_source)
        self.editor_view.run_requested.connect(self.on_run_from_editor)

        # 5. 一键直接启动程序
        self.runner_view.run_requested.connect(self.on_run_script_direct)

        # 6. 主窗口关闭持久化
        self.main_window.window_closing.connect(self.save_settings)

    def on_file_selected(self, file_path: str):
        """文件树单击 .py 文件：自动将路径传递给运行入口"""
        if file_path.endswith(".py"):
            self.runner_view.set_script_path(file_path)
            self.main_window.show_status_message(f"已选中运行脚本: {file_path}", 2000)

    def on_open_directory(self):
        dir_path = QFileDialog.getExistingDirectory(
            self.main_window, 
            "选择项目目录", 
            self._current_project_dir or os.path.expanduser("~")
        )
        if dir_path:
            self._load_project_dir(dir_path)

    def _load_project_dir(self, dir_path: str):
        self._current_project_dir = dir_path
        self.project_tree.load_directory(dir_path)
        self.project_tree.scan_line_counts()
        self.main_window.show_status_message(f"已打开项目: {dir_path}", 3000)

    def on_file_double_clicked(self, file_path: str):
        if not os.path.exists(file_path):
            return

        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()

            self.editor_view.update_editor_content(file_path, content)
            symbols = self._parse_outline(content)
            self.editor_view.update_outline(symbols)

            self.main_window.right_tabs.setCurrentIndex(1)
            self.main_window.show_status_message(f"已打开文件: {file_path}", 2000)

        except Exception as e:
            self.main_window.show_status_message(f"读取文件失败: {str(e)}", 4000)

    def on_save_source(self, content: str):
        file_path = self.editor_view.get_current_file_path()
        if not file_path:
            self.main_window.show_status_message("保存失败：当前未打开文件", 3000)
            return

        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)

            self.editor_view.btn_save.setEnabled(False)
            symbols = self._parse_outline(content)
            self.editor_view.update_outline(symbols)
            self.project_tree.scan_line_counts()

            self.main_window.show_status_message(f"保存成功：{file_path}", 3000)

        except Exception as e:
            self.main_window.show_status_message(f"保存失败：{str(e)}", 5000)

    def on_run_from_editor(self):
        """处理从源码编辑器点击▶运行的请求：若有未保存修改则先自动保存，然后启动"""
        file_path = self.editor_view.get_current_file_path()
        if not file_path or not os.path.exists(file_path):
            self.main_window.show_status_message("运行失败：当前未打开有效文件！", 3000)
            return

        # 如果编辑器处于待保存状态，运行前先自动写盘
        if self.editor_view.btn_save.isEnabled():
            self.on_save_source(self.editor_view.editor.toPlainText())

        # 读取 RunnerView 的全局运行配置
        runner_config = self.runner_view.get_config()
        run_config = {
            "interpreter": runner_config.get("interpreter") or sys.executable,
            "script_path": file_path,
            "args": runner_config.get("args", ""),
            "work_dir": os.path.dirname(os.path.abspath(file_path))
        }

        # 调用拉起进程的统一逻辑
        self.on_run_script_direct(run_config)

    def on_run_script_direct(self, config: dict):
        """一键直接启动程序：后台创建独立子进程，支持多开"""
        script_path = config.get("script_path")
        interpreter = config.get("interpreter") or sys.executable
        args_str = config.get("args", "")
        work_dir = config.get("work_dir") or (os.path.dirname(script_path) if script_path else os.getcwd())

        if not script_path or not os.path.exists(script_path):
            self.main_window.show_status_message("运行失败：指定的脚本文件不存在！", 4000)
            return

        cmd = [interpreter, "-u", script_path]
        if args_str:
            cmd.extend(shlex.split(args_str))

        try:
            subprocess.Popen(
                cmd,
                cwd=work_dir,
                stdout=None,
                stderr=None,
                stdin=None,
                start_new_session=True
            )

            script_name = os.path.basename(script_path)
            self.main_window.show_status_message(f"🚀 已成功启动程序: {script_name}", 3000)

        except Exception as e:
            self.main_window.show_status_message(f"启动失败: {str(e)}", 5000)

    def _parse_outline(self, code_str: str):
        symbols = []
        try:
            tree = ast.parse(code_str)
            for node in ast.iter_child_nodes(tree):
                if isinstance(node, ast.ClassDef):
                    symbols.append({"type": "class", "name": node.name, "lineno": node.lineno})
                elif isinstance(node, ast.FunctionDef):
                    symbols.append({"type": "function", "name": node.name, "lineno": node.lineno})
        except Exception:
            pass
        return symbols

    # ================= Persistence 持久化逻辑 =================

    def save_settings(self):
        """将全程序所有控件状态持久化写入 QSettings"""
        self.settings.setValue("geometry", self.main_window.saveGeometry())
        self.settings.setValue("windowState", self.main_window.saveState())
        self.settings.setValue("main_splitter", self.main_window.main_splitter.saveState())
        self.settings.setValue("editor_splitter", self.editor_view.splitter.saveState())
        self.settings.setValue("current_tab", self.main_window.right_tabs.currentIndex())
        self.settings.setValue("project_dir", self._current_project_dir)

        runner_config = self.runner_view.get_config()
        for k, v in runner_config.items():
            self.settings.setValue(f"runner_{k}", v)

    def restore_settings(self):
        """从 QSettings 恢复控件状态"""
        geometry = self.settings.value("geometry")
        if isinstance(geometry, QByteArray):
            self.main_window.restoreGeometry(geometry)

        main_splitter = self.settings.value("main_splitter")
        if isinstance(main_splitter, QByteArray):
            self.main_window.main_splitter.restoreState(main_splitter)

        editor_splitter = self.settings.value("editor_splitter")
        if isinstance(editor_splitter, QByteArray):
            self.editor_view.splitter.restoreState(editor_splitter)

        current_tab = self.settings.value("current_tab", type=int)
        if current_tab:
            self.main_window.right_tabs.setCurrentIndex(current_tab)

        saved_dir = self.settings.value("project_dir", type=str)
        if saved_dir and os.path.exists(saved_dir):
            self._load_project_dir(saved_dir)

        runner_config = {
            "interpreter": self.settings.value("runner_interpreter", type=str),
            "script_path": self.settings.value("runner_script_path", type=str),
            "args": self.settings.value("runner_args", type=str),
            "work_dir": self.settings.value("runner_work_dir", type=str),
        }
        self.runner_view.set_config(runner_config)