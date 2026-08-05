import os
from PySide2.QtCore import QThread, Signal


class FileReaderThread(QThread):
    text_ready = Signal(str)
    finished_loading = Signal()
    error_occurred = Signal(str)
    warning_occurred = Signal(str)

    def __init__(self, file_path: str):
        super().__init__()
        self.file_path = file_path
        self.max_preview_size = 2 * 1024 * 1024  # 2MB

    def run(self):
        try:
            file_size = os.path.getsize(self.file_path)
            read_size = -1

            if file_size > self.max_preview_size:
                read_size = self.max_preview_size
                self.warning_occurred.emit(
                    f"⚠️ 文件过大 ({file_size / 1024 / 1024:.2f} MB)，为防止卡顿，仅截取前 2MB 进行预览。"
                )

            with open(self.file_path, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read() if read_size == -1 else f.read(read_size)
                self.text_ready.emit(content)

        except Exception as e:
            self.error_occurred.emit(f"无法读取文件内容: {str(e)}")
        finally:
            self.finished_loading.emit()
