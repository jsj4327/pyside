import re
from PySide2.QtCore import QObject, QProcess, Signal


class GitManager(QObject):
    stdout_received = Signal(str)
    stderr_received = Signal(str)
    process_finished = Signal(int, int)  # exit_code, exit_status

    def __init__(self, parent=None):
        super().__init__(parent)
        self.process = QProcess(self)
        self.process.readyReadStandardOutput.connect(self._handle_stdout)
        self.process.readyReadStandardError.connect(self._handle_stderr)
        self.process.finished.connect(self.process_finished.emit)

    def set_working_directory(self, path: str):
        self.process.setWorkingDirectory(path)

    def is_running(self) -> bool:
        return self.process.state() == QProcess.Running

    def run_command(self, args: list):
        cmd = "git"
        self.process.start(cmd, args)

    def push_with_token(self, url: str, token: str):
        push_url = url
        if token and url.startswith("https://"):
            push_url = re.sub(r"https://", f"https://oauth2:{token}@", url)
        self.run_command(["push", push_url])

    def _handle_stdout(self):
        data = self.process.readAllStandardOutput().data().decode('utf-8', errors='replace')
        self.stdout_received.emit(data.strip())

    def _handle_stderr(self):
        data = self.process.readAllStandardError().data().decode('utf-8', errors='replace')
        self.stderr_received.emit(data.strip())
