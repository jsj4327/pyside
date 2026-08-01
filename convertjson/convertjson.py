import sys
import os
import json
import re
from PySide2.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTextEdit, QPushButton, QLabel, QFileDialog, QGroupBox, QPlainTextEdit
)
from PySide2.QtCore import Qt


class CodeFileGenerator(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("代码文件生成器")
        self.resize(950, 700)
        self.output_dir = os.path.expanduser("~/output_code")
        self._init_ui()

    def _init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setSpacing(8)

        # ── 输入区 ──
        grp_input = QGroupBox("JSON 输入")
        lay_input = QVBoxLayout(grp_input)
        self.txt_input = QPlainTextEdit()
        self.txt_input.setPlaceholderText(
            '支持格式：\n'
            '1. {"files": [{"filename":"a.py","code":"..."}, ...]}\n'
            '2. [{"filename":"a.py","code":"..."}, ...]\n'
            '3. 多个独立 {"filename":"...","code":"..."} 对象'
        )
        lay_input.addWidget(self.txt_input)
        layout.addWidget(grp_input, stretch=3)

        # ── 输出目录 ──
        lay_dir = QHBoxLayout()
        lay_dir.addWidget(QLabel("输出根目录："))
        self.lbl_dir = QLabel(self.output_dir)
        self.lbl_dir.setStyleSheet("color: #2196F3; font-weight: bold;")
        lay_dir.addWidget(self.lbl_dir, stretch=1)
        btn_browse = QPushButton("选择目录...")
        btn_browse.clicked.connect(self._browse_dir)
        lay_dir.addWidget(btn_browse)
        layout.addLayout(lay_dir)

        # ── 按钮 ──
        lay_btn = QHBoxLayout()
        self.btn_generate = QPushButton("▶ 生成文件")
        self.btn_generate.setFixedHeight(36)
        self.btn_generate.setStyleSheet(
            "QPushButton { background:#4CAF50; color:white; font-size:14px; "
            "border-radius:4px; } QPushButton:hover { background:#388E3C; }"
        )
        self.btn_generate.clicked.connect(self._generate)
        lay_btn.addStretch()
        lay_btn.addWidget(self.btn_generate)
        lay_btn.addStretch()
        layout.addLayout(lay_btn)

        # ── 日志区 ──
        grp_log = QGroupBox("执行日志")
        lay_log = QVBoxLayout(grp_log)
        self.txt_log = QTextEdit()
        self.txt_log.setReadOnly(True)
        self.txt_log.setMaximumHeight(220)
        lay_log.addWidget(self.txt_log)
        layout.addWidget(grp_log, stretch=1)

        self.statusBar().showMessage("就绪")

    def _browse_dir(self):
        d = QFileDialog.getExistingDirectory(self, "选择输出根目录", self.output_dir)
        if d:
            self.output_dir = d
            self.lbl_dir.setText(d)

    # ══════════════════════════════════════════════════
    #  核心解析逻辑 (已修复 & 增强版)
    # ══════════════════════════════════════════════════
    def _parse_json_input(self, raw: str) -> list:
        raw = raw.strip()
        if not raw:
            return []

        # 清理 AI 经常输出的 Markdown 代码块标记
        raw = re.sub(r'^\s*```(?:json)?', '', raw, flags=re.MULTILINE)
        raw = re.sub(r'```\s*$', '', raw, flags=re.MULTILINE)
        raw = raw.strip()

        # ── 策略 1：直接解析 ──
        items = self._try_direct_parse(raw)
        if items:
            return items

        # ── 策略 2：修复后重试 ──
        items = self._try_fixed_parse(raw)
        if items:
            return items

        # ── 策略 3：正则兜底 ──
        return self._regex_fallback(raw)

    def _try_direct_parse(self, raw: str) -> list:
        try:
            # 添加 strict=False，允许 JSON 字符串内部存在真实的换行符/制表符
            data = json.loads(raw, strict=False)
            return self._extract_items(data)
        except (json.JSONDecodeError, TypeError):
            return []

    def _try_fixed_parse(self, raw: str) -> list:
        fixed = raw

        # 处理非法的转义字符（如代码里的正则 \d 而不是 \\d）
        fixed = re.sub(r'\\(?![/"\\bfnrtu])', r'\\\\', fixed)

        # 处理尾随逗号 (Trailing commas)
        fixed = re.sub(r',\s*([}\]])', r'\1', fixed)

        # 修复：code 字段内的未转义双引号
        fixed = self._fix_code_quotes(fixed)

        try:
            data = json.loads(fixed, strict=False)
            return self._extract_items(data)
        except (json.JSONDecodeError, TypeError):
            return []

    def _fix_code_quotes(self, text: str) -> str:
        result = []
        i = 0
        n = len(text)

        while i < n:
            if text[i:i+7] == '"code":':
                result.append('"code":')
                i += 7
                while i < n and text[i] in ' \t\r\n':
                    result.append(text[i])
                    i += 1
                if i < n and text[i] == '"':
                    result.append('"')
                    i += 1
                    code_chars = []
                    while i < n:
                        ch = text[i]
                        if ch == '\\':
                            code_chars.append(ch)
                            i += 1
                            if i < n:
                                code_chars.append(text[i])
                                i += 1
                            continue
                        if ch == '"':
                            j = i + 1
                            while j < n and text[j] in ' \t\r\n':
                                j += 1
                            # 绝不能将 \n 作为 JSON 值的结束符
                            if j >= n or text[j] in ',}]':
                                break
                            else:
                                code_chars.append('\\"')
                                i += 1
                                continue
                        if ch == '\n':
                            code_chars.append('\\n')
                            i += 1
                            continue
                        code_chars.append(ch)
                        i += 1

                    result.append(''.join(code_chars))
                    if i < n:
                        result.append('"')  # 关闭引号
                        i += 1
                continue
            else:
                result.append(text[i])
                i += 1

        return ''.join(result)

    def _extract_items(self, data) -> list:
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            if 'files' in data and isinstance(data['files'], list):
                return data['files']
            if 'filename' in data:
                return [data]
            for v in data.values():
                if isinstance(v, list):
                    return v
        return []

    def _regex_fallback(self, raw: str) -> list:
        items = []
        segments = re.split(r'"filename"\s*:\s*', raw)
        
        for seg in segments[1:]:
            fn_match = re.match(r'"([^"]+)"', seg)
            if not fn_match:
                continue
            filename = fn_match.group(1)

            code_match = re.search(r'"code"\s*:\s*"(.*)', seg, re.DOTALL)
            if code_match:
                code_str = code_match.group(1)
                end_match = re.search(r'"\s*(?:}|,\s*")', code_str)
                if end_match:
                    code_str = code_str[:end_match.start()]
                else:
                    code_str = code_str.rstrip()
                    if code_str.endswith('"'):
                        code_str = code_str[:-1]
                
                code_str = code_str.replace('\\n', '\n').replace('\\"', '"').replace('\\\\', '\\')
                items.append({"filename": filename, "code": code_str})

        return items

    # ══════════════════════════════════════════════════
    #  生成文件
    # ══════════════════════════════════════════════════
    def _generate(self):
        raw = self.txt_input.toPlainText()
        self.txt_log.clear()

        items = self._parse_json_input(raw)

        if not items:
            self._log("❌ 未能解析到任何文件条目，请检查输入格式。")
            return

        self._log(f"📋 共解析到 {len(items)} 个文件条目\n")

        success_count = 0
        fail_count = 0

        for i, item in enumerate(items, 1):
            if not isinstance(item, dict):
                self._log(f"❌ [{i}] 条目格式错误（非字典），已跳过")
                fail_count += 1
                continue

            filename = item.get("filename", "").strip()
            code = item.get("code", "")

            if not filename:
                self._log(f"⚠️  [{i}] 缺少 filename，已跳过")
                fail_count += 1
                continue

            # 安全检查
            if ".." in filename or filename.startswith(("/", "\\")):
                self._log(f"⚠️  [{i}] 非法路径：{filename}，已跳过")
                fail_count += 1
                continue

            full_path = os.path.join(self.output_dir, filename)
            dir_part = os.path.dirname(full_path)

            try:
                if dir_part:
                    os.makedirs(dir_part, exist_ok=True)

                with open(full_path, "w", encoding="utf-8") as f:
                    f.write(code)

                size_info = f"{len(code)} 字符" if code else "空文件"
                self._log(f"✅ [{i:2d}] {filename}  ({size_info})")
                success_count += 1

            except Exception as e:
                self._log(f"❌ [{i:2d}] {filename}  写入失败: {e}")
                fail_count += 1

        self._log(f"\n{'═' * 50}")
        self._log(f"📊 结果：成功 {success_count} / 失败 {fail_count} / 总计 {len(items)}")
        self._log(f"📂 输出：{self.output_dir}")
        self.statusBar().showMessage(f"完成：成功 {success_count}，失败 {fail_count}")

    def _log(self, msg: str):
        self.txt_log.append(msg)
        sb = self.txt_log.verticalScrollBar()
        sb.setValue(sb.maximum())


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    win = CodeFileGenerator()
    win.show()
    sys.exit(app.exec_())