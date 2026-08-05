# -*- coding: utf-8 -*-
from PySide2.QtCore import QObject


class PreviewController(QObject):
    """代码预览Tab的控制器"""

    def __init__(self, file_manager, code_editor, file_label, tab_widget, log_viewer, parent=None):
        super().__init__(parent)
        self.fm = file_manager
        self.editor = code_editor
        self.label = file_label
        self.tab_widget = tab_widget
        self.log_viewer = log_viewer
        self.current_filename = None

    def select_file(self, filename):
        self.current_filename = filename
        content = self.fm.get_cached(filename)
        if content is not None:
            self.editor.setPlainText(content)
            self.label.setText(f"当前编辑: {filename}")
            self.tab_widget.setCurrentIndex(1)

    def save_current(self):
        if not self.current_filename:
            return
        code = self.editor.toPlainText()
        try:
            self.fm.save_file(self.current_filename, code)
            self.log_viewer.append_log(
                "手动保存",
                f"文件 <b>{self.current_filename}</b> 已成功保存。",
                "SUCCESS",
            )
        except Exception as e:
            self.log_viewer.append_log("保存失败", str(e), "ERROR")
