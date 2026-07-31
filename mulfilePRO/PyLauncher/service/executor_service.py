# -*- coding: utf-8 -*-
from PySide2.QtCore import QObject, QProcess, Signal


class ExecutorService(QObject):
    """脚本执行服务：支持同时运行多个 Python 子进程。"""

    # job_id, text
    stdout_received = Signal(str, str)
    # job_id, exit_code
    process_finished = Signal(str, int)

    def __init__(self, parent=None):
        super().__init__(parent)
        # job_id -> QProcess
        self._processes = {}
        self._job_seq = 0

    def start_script(self, script_path, working_dir=None, args=None, job_label=None):
        """
        启动一个新的 Python 脚本子进程，不停止已有进程。
        返回 job_id，便于日志区分。
        """
        self._job_seq += 1
        job_id = job_label or f"job-{self._job_seq}"
        # 若同名标签冲突，加序号
        if job_id in self._processes:
            job_id = f"{job_id}-{self._job_seq}"

        process = QProcess(self)
        if working_dir:
            process.setWorkingDirectory(working_dir)

        process.setProperty("job_id", job_id)
        process.readyReadStandardOutput.connect(
            lambda p=process: self._handle_stdout(p)
        )
        process.readyReadStandardError.connect(
            lambda p=process: self._handle_stderr(p)
        )
        process.finished.connect(
            lambda code, status, p=process: self._handle_finished(p, code, status)
        )

        cmd_args = [script_path]
        if args:
            cmd_args.extend(args)

        self._processes[job_id] = process
        process.start("python3", cmd_args)
        return job_id

    def stop_script(self, job_id=None):
        """
        停止进程。
        - job_id 有值：只停该任务
        - job_id 为 None：停止全部
        """
        if job_id is not None:
            process = self._processes.get(job_id)
            if process is not None:
                self._kill_process(process)
                self._processes.pop(job_id, None)
            return

        for jid, process in list(self._processes.items()):
            self._kill_process(process)
        self._processes.clear()

    def running_jobs(self):
        """当前仍在运行的 job_id 列表。"""
        return [
            jid
            for jid, p in self._processes.items()
            if p.state() != QProcess.NotRunning
        ]

    def is_any_running(self):
        return len(self.running_jobs()) > 0

    def _kill_process(self, process):
        if process and process.state() != QProcess.NotRunning:
            process.kill()
            process.waitForFinished(1000)

    def _handle_stdout(self, process):
        job_id = process.property("job_id")
        data = process.readAllStandardOutput().data().decode("utf-8", errors="replace")
        if data:
            self.stdout_received.emit(str(job_id), data)

    def _handle_stderr(self, process):
        job_id = process.property("job_id")
        data = process.readAllStandardError().data().decode("utf-8", errors="replace")
        if data:
            self.stdout_received.emit(str(job_id), data)

    def _handle_finished(self, process, exit_code, exit_status):
        job_id = str(process.property("job_id"))
        self._processes.pop(job_id, None)
        process.deleteLater()
        self.process_finished.emit(job_id, exit_code)