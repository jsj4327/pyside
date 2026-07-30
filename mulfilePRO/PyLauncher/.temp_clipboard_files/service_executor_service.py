# -*- coding: utf-8 -*-

from PySide2.QtCore import QObject, QProcess, Signal

class ExecutorService(QObject):
    """脚本执行服务：负责使用 QProcess 异步调用 Python 3 子进程"""

    stdout_received = Signal(str)
    process_finished = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.process = None

    def start_script(self, script_path, working_dir=None, args=None):
        """启动 Python 脚本子进程"""
        self.stop_script()  # 如果已有运行中的进程，先关闭

        self.process = QProcess(self)
        if working_dir:
            self.process.setWorkingDirectory(working_dir)

        # 监听输出与完成信号
        self.process.readyReadStandardOutput.connect(self._handle_stdout)
        self.process.readyReadStandardError.connect(self._handle_stderr)
        self.process.finished.connect(self._handle_finished)

        cmd_args = [script_path]
        if args:
            cmd_args.extend(args)

        # 【关键修改】强制使用 python3 解释器启动，解决 Python 2 编码报错
        python_bin = "python3"
        self.process.start(python_bin, cmd_args)

    def stop_script(self):
        """停止运行中的进程"""
        if self.process and self.process.state() != QProcess.NotRunning:
            self.process.kill()
            self.process.waitForFinished(1000)
            self.process = None

    def _handle_stdout(self):
        data = self.process.readAllStandardOutput().data().decode('utf-8', errors='replace')
        self.stdout_received.emit(data)

    def _handle_stderr(self):
        data = self.process.readAllStandardError().data().decode('utf-8', errors='replace')
        self.stdout_received.emit(data)

    def _handle_finished(self, exit_code, exit_status):
        self.process_finished.emit(exit_code)