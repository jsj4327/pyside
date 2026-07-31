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
    #  核心解析逻辑
    # ══════════════════════════════════════════════════
    def _parse_json_input(self, raw: str) -> list:
        """
        多策略解析：
          策略1: 直接 json.loads（处理合法 JSON）
          策略2: 修复常见问题后重试
          策略3: 正则提取 filename + code 对（兜底）
        """
        raw = raw.strip()
        if not raw:
            return []

        # ── 策略 1：直接解析 ──
        items = self._try_direct_parse(raw)
        if items:
            return items

        # ── 策略 2：修复后重试 ──
        items = self._try_fixed_parse(raw)
        if items:
            return items

        # ── 策略 3：正则兜底 ──
        items = self._regex_fallback(raw)
        return items

    def _try_direct_parse(self, raw: str) -> list:
        """直接 json.loads，处理各种外层包装"""
        try:
            data = json.loads(raw)
            return self._extract_items(data)
        except (json.JSONDecodeError, TypeError):
            return []

    def _try_fixed_parse(self, raw: str) -> list:
        """尝试修复常见 JSON 问题后解析"""
        fixed = raw

        # 修复：code 字段内的未转义双引号
        # 思路：找到 "code": "..." 段，对内部的裸引号转义
        fixed = self._fix_code_quotes(fixed)

        try:
            data = json.loads(fixed)
            return self._extract_items(data)
        except (json.JSONDecodeError, TypeError):
            return []

    def _fix_code_quotes(self, text: str) -> str:
        """
        修复 "code": "..." 中未转义的双引号。
        逐字符扫描，在 code 值内部对裸 " 加反斜杠。
        """
        result = []
        i = 0
        n = len(text)

        while i < n:
            # 检测 "code" 键的开始
            if text[i:i+7] == '"code":':
                result.append('"code":')
                i += 7
                # 跳过空白
                while i < n and text[i] in ' \t\r\n':
                    result.append(text[i])
                    i += 1
                # 期望一个开引号
                if i < n and text[i] == '"':
                    result.append('"')
                    i += 1
                    # 扫描 code 值直到找到真正的结束引号
                    # 结束引号的特征：后面跟 , 或 } 或 ] 或空白+这些字符
                    code_chars = []
                    while i < n:
                        ch = text[i]
                        if ch == '\\':
                            # 已转义的字符，原样保留
                            code_chars.append(ch)
                            i += 1
                            if i < n:
                                code_chars.append(text[i])
                                i += 1
                            continue
                        if ch == '"':
                            # 判断是否是结束引号
                            # 向后看：跳过空白后如果是 , } ] 则是结束
                            j = i + 1
                            while j < n and text[j] in ' \t\r\n':
                                j += 1
                            if j >= n or text[j] in ',}]\n':
                                # 这是结束引号
                                break
                            else:
                                # 这是 code 内部的裸引号，需要转义
                                code_chars.append('\\"')
                                i += 1
                                continue
                        if ch == '\n':
                            # JSON 字符串内不能有裸换行，转为 \\n
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
        """从解析后的数据中提取文件列表"""
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            # 处理 {"files": [...]} 包装
            if 'files' in data and isinstance(data['files'], list):
                return data['files']
            # 单个对象
            if 'filename' in data:
                return [data]
            # 尝试取第一个 list 类型的值
            for v in data.values():
                if isinstance(v, list):
                    return v
        return []

    def _regex_fallback(self, raw: str) -> list:
        """
        终极兜底：用正则逐个提取 "filename" 和 "code" 字段。
        适用于 JSON 严重损坏的情况。
        """
        items = []
        # 匹配 "filename": "xxx"
        fn_pattern = re.compile(r'"filename"\s*:\s*"([^"]+)"')
        # 匹配 "code": "..." （贪婪到下一个 "filename" 或结尾）
        # 使用分段策略
        segments = re.split(r'(?=\{\s*"filename")', raw)

        for seg in segments:
            fn_match = fn_pattern.search(seg)
            if not fn_match:
                continue
            filename = fn_match.group(1)

            # 提取 code：从 "code": " 开始到段尾的 "} 或 "},
            code_match = re.search(
                r'"code"\s*:\s*"(.*?)"(?:\s*\}|\s*,)',
                seg, re.DOTALL
            )
            if code_match:
                code = code_match.group(1)
                # 反转义
                code = code.replace('\\n', '\n').replace('\\"', '"').replace('\\\\', '\\')
            else:
                code = ""

            items.append({"filename": filename, "code": code})

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