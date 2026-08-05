from PySide2.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QPlainTextEdit
)

from core.file_reader_thread import FileReaderThread


class FilePreviewPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.reader_thread = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)

        preview_top_layout = QHBoxLayout()
        self.lbl_preview_info = QLabel("准备加载...")
        self.lbl_preview_info.setStyleSheet("color: #2196F3; font-weight: bold;")

        self.btn_close_preview = QPushButton("✖ 关闭预览")
        self.btn_close_preview.setStyleSheet(
            "background-color: #F44336; color: white; font-weight: bold;"
        )
        self.btn_close_preview.setFixedWidth(100)

        preview_top_layout.addWidget(self.lbl_preview_info)
        preview_top_layout.addStretch()
        preview_top_layout.addWidget(self.btn_close_preview)

        self.preview_editor = QPlainTextEdit()
        self.preview_editor.setReadOnly(True)
        self.preview_editor.setStyleSheet(
            "font-family: Consolas, monospace; font-size: 13px;"
        )

        layout.addLayout(preview_top_layout)
        layout.addWidget(self.preview_editor)

    def load_file(self, file_path: str, file_name: str):
        self.lbl_preview_info.setText(f"正在加载: {file_name} ...")
        self.lbl_preview_info.setStyleSheet("color: #FF9800; font-weight: bold;")
        self.preview_editor.clear()

        self.reader_thread = FileReaderThread(file_path)
        self.reader_thread.text_ready.connect(self.preview_editor.setPlainText)
        self.reader_thread.warning_occurred.connect(self._show_warning)
        self.reader_thread.error_occurred.connect(self._show_error)
        self.reader_thread.finished_loading.connect(
            lambda: self._finish_loading(file_name)
        )
        self.reader_thread.start()

    def clear_content(self):
        self.preview_editor.clear()

    def _show_warning(self, msg: str):
        self.lbl_preview_info.setText(msg)
        self.lbl_preview_info.setStyleSheet("color: #FF5722; font-weight: bold;")

    def _show_error(self, msg: str):
        self.lbl_preview_info.setText(msg)
        self.lbl_preview_info.setStyleSheet("color: #F44336; font-weight: bold;")

    def _finish_loading(self, file_name: str):
        if "正在加载" in self.lbl_preview_info.text():
            self.lbl_preview_info.setText(f"预览: {file_name}")
            self.lbl_preview_info.setStyleSheet("color: #4CAF50; font-weight: bold;")
