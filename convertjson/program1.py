import os
import json
import sys
from PySide2.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPlainTextEdit, QPushButton, QLabel, QFileDialog, QMessageBox,
    QGroupBox, QLineEdit
)
from PySide2.QtCore import Qt
from PySide2.QtGui import QFont


class FileGeneratorWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("代码结构解析生成器")
        self.resize(1000, 700)
        self._init_ui()

    def _init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        # ========== 输出目录 ==========
        dir_group = QGroupBox("输出目录")
        dir_layout = QHBoxLayout(dir_group)

        self.dir_edit = QLineEdit()
        self.dir_edit.setPlaceholderText("选择要生成文件的根目录...")
        self.dir_edit.setText(os.path.join(os.path.expanduser("~"), "generated_code"))
        dir_layout.addWidget(self.dir_edit)

        btn_browse = QPushButton("浏览...")
        btn_browse.clicked.connect(self._browse_dir)
        dir_layout.addWidget(btn_browse)

        layout.addWidget(dir_group)

        # ========== 文本输入区 ==========
        input_group = QGroupBox("粘贴包含 \"files\" 数组的文本")
        input_layout = QVBoxLayout(input_group)

        self.text_edit = QPlainTextEdit()
        self.text_edit.setPlaceholderText(
            '请粘贴类似下面的结构：\n\n'
            '{\n'
            '  "files": [\n'
            '    {\n'
            '      "filename": "crawler/database.py",\n'
            '      "code": "import os\\n..."\n'
            '    },\n'
            '    ...\n'
            '  ]\n'
            '}'
        )
        self.text_edit.setFont(QFont("Consolas", 10))
        input_layout.addWidget(self.text_edit)

        layout.addWidget(input_group)

        # ========== 操作按钮 ==========
        btn_layout = QHBoxLayout()

        self.btn_parse = QPushButton("▶ 解析并生成文件")
        self.btn_parse.setMinimumHeight(40)
        self.btn_parse.clicked.connect(self._parse_and_generate)
        btn_layout.addWidget(self.btn_parse)

        self.btn_clear = QPushButton("清空文本")
        self.btn_clear.clicked.connect(self.text_edit.clear)
        btn_layout.addWidget(self.btn_clear)

        layout.addLayout(btn_layout)

        # ========== 日志 ==========
        log_group = QGroupBox("运行日志")
        log_layout = QVBoxLayout(log_group)

        self.log_edit = QPlainTextEdit()
        self.log_edit.setReadOnly(True)
        self.log_edit.setMaximumHeight(180)
        log_layout.addWidget(self.log_edit)

        layout.addWidget(log_group)

    def _browse_dir(self):
        path = QFileDialog.getExistingDirectory(self, "选择输出目录", self.dir_edit.text())
        if path:
            self.dir_edit.setText(path)

    def _log(self, msg: str):
        self.log_edit.appendPlainText(msg)

    def _parse_and_generate(self):
        self.log_edit.clear()
        raw_text = self.text_edit.toPlainText().strip()
        if not raw_text:
            QMessageBox.warning(self, "提示", "请先粘贴文本内容！")
            return

        output_root = self.dir_edit.text().strip()
        if not output_root:
            QMessageBox.warning(self, "提示", "请先选择输出目录！")
            return

        # ---------- 尝试解析 JSON ----------
        try:
            # 兼容用户只粘贴了 files 数组，或者完整对象
            data = json.loads(raw_text)
        except json.JSONDecodeError:
            # 尝试把文本包成一个对象再解析
            try:
                if raw_text.startswith("["):
                    data = {"files": json.loads(raw_text)}
                else:
                    # 可能用户复制时少了最外层花括号
                    data = json.loads("{" + raw_text + "}")
            except Exception as e:
                self._log(f"❌ JSON 解析失败: {e}")
                QMessageBox.critical(self, "解析错误", f"无法解析为合法 JSON：\n{e}")
                return

        files = data.get("files")
        if not isinstance(files, list):
            self._log("❌ 未找到有效的 \"files\" 数组")
            QMessageBox.warning(self, "格式错误", "文本中必须包含 \"files\" 数组")
            return

        self._log(f"✅ 成功解析，共发现 {len(files)} 个文件")
        os.makedirs(output_root, exist_ok=True)

        success_count = 0
        fail_count = 0

        for item in files:
            if not isinstance(item, dict):
                continue

            filename = item.get("filename", "").strip()
            code = item.get("code", "")

            if not filename:
                self._log("⚠️ 跳过一条无 filename 的记录")
                fail_count += 1
                continue

            # 处理路径（兼容 Windows / Linux）
            full_path = os.path.join(output_root, filename.replace("\\", "/"))
            dir_path = os.path.dirname(full_path)

            try:
                if dir_path:
                    os.makedirs(dir_path, exist_ok=True)

                with open(full_path, "w", encoding="utf-8") as f:
                    f.write(code)

                self._log(f"✅ 已生成: {filename}")
                success_count += 1
            except Exception as e:
                self._log(f"❌ 写入失败 [{filename}]: {e}")
                fail_count += 1

        self._log("-" * 40)
        self._log(f"完成！成功 {success_count} 个，失败 {fail_count} 个")
        self._log(f"输出目录: {output_root}")

        QMessageBox.information(
            self,
            "完成",
            f"成功生成 {success_count} 个文件\n失败 {fail_count} 个\n\n输出目录：\n{output_root}"
        )


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setFont(QFont("Microsoft YaHei", 10))
    win = FileGeneratorWindow()
    win.show()
    sys.exit(app.exec_())