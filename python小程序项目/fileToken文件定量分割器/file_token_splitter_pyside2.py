# -*- coding: utf-8 -*-
"""
文件夹内容读取 & 按 Token 数拆分保存工具（PySide2 版本）
------------------------------------------------------
功能：
1. 选择一个文件夹，用树形控件（QTreeView + QFileSystemModel）展示其中的文件/子文件夹，
   子文件夹可以原生展开查看内部内容。
2. 输入一个 token 数值作为单个输出 txt 文件的容量上限（支持中文/英文混合估算）。
3. 开关：是否递归读取所有子文件夹中的文件（关闭则只读当前文件夹下的文件，不含子文件夹）。
4. 开关：是否过滤掉常见的注释行和空行。
5. 将文件夹下的文件内容按 token 上限打包写入 txt，超过上限自动拆分为下一个 txt，
   按顺序编号（如 output_001.txt, output_002.txt ...）。
6. 每个文件内容前会写入清晰的分隔符与文件名（相对路径）作为头部。

依赖：
    pip install PySide2
    可选：pip install tiktoken   （用于更精确的 token 计算，否则自动使用启发式估算）
"""

import os
import queue
import sys

from PySide2.QtCore import Qt, QObject, QThread, Signal
from PySide2.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QPushButton, QLineEdit, QLabel, QCheckBox, QGroupBox, QTreeView,
    QFileDialog, QMessageBox, QTextEdit, QSplitter
)
from PySide2.QtWidgets import QFileSystemModel

# ----------------------------------------------------------------------
# Token 计算
# ----------------------------------------------------------------------
try:
    import tiktoken
    _ENC = tiktoken.get_encoding("cl100k_base")

    def count_tokens(text: str) -> int:
        if not text:
            return 0
        return len(_ENC.encode(text))

    TOKEN_METHOD = "tiktoken (cl100k_base)"
except Exception:
    _ENC = None

    def count_tokens(text: str) -> int:
        """启发式 token 估算：中文字符按 ~1.5 token/字，其余字符按 ~4 字符/token。"""
        if not text:
            return 0
        cjk_count = 0
        other_len = 0
        for ch in text:
            if ("\u4e00" <= ch <= "\u9fff") or ("\u3400" <= ch <= "\u4dbf"):
                cjk_count += 1
            else:
                other_len += 1
        cjk_tokens = int(cjk_count * 1.5)
        other_tokens = other_len / 4.0
        total = cjk_tokens + other_tokens
        return max(0, int(round(total)))

    TOKEN_METHOD = "启发式估算（未检测到 tiktoken，可执行 pip install tiktoken 以获得更精确结果）"


# ----------------------------------------------------------------------
# 注释 / 空行过滤
# ----------------------------------------------------------------------
COMMENT_PREFIXES = {
    ".py": ("#",),
    ".pyw": ("#",),
    ".js": ("//",),
    ".jsx": ("//",),
    ".ts": ("//",),
    ".tsx": ("//",),
    ".java": ("//",),
    ".c": ("//",),
    ".h": ("//",),
    ".cpp": ("//",),
    ".hpp": ("//",),
    ".cs": ("//",),
    ".go": ("//",),
    ".rs": ("//",),
    ".swift": ("//",),
    ".kt": ("//",),
    ".php": ("//", "#"),
    ".rb": ("#",),
    ".sh": ("#",),
    ".bash": ("#",),
    ".yaml": ("#",),
    ".yml": ("#",),
    ".toml": ("#",),
    ".ini": (";", "#"),
    ".sql": ("--",),
    ".lua": ("--",),
    ".html": ("<!--",),
    ".htm": ("<!--",),
    ".xml": ("<!--",),
    ".css": ("/*",),
    ".scss": ("//", "/*"),
}
DEFAULT_COMMENT_PREFIXES = ("#", "//", "--")

LIKELY_BINARY_EXT = {
    ".exe", ".dll", ".so", ".dylib", ".bin", ".o", ".obj", ".class",
    ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".ico", ".webp", ".svg",
    ".mp3", ".mp4", ".avi", ".mov", ".mkv", ".wav", ".flac",
    ".zip", ".rar", ".7z", ".tar", ".gz", ".bz2", ".xz",
    ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
    ".pyc", ".pyo", ".woff", ".woff2", ".ttf", ".eot", ".db", ".sqlite",
}


def filter_lines(text: str, ext: str) -> str:
    """去除空行以及以常见注释符开头的整行注释（简单按行判断，不处理块注释内部内容）。"""
    prefixes = COMMENT_PREFIXES.get(ext.lower(), DEFAULT_COMMENT_PREFIXES)
    result = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if any(stripped.startswith(p) for p in prefixes):
            continue
        result.append(line)
    return "\n".join(result)


# ----------------------------------------------------------------------
# 文件读取
# ----------------------------------------------------------------------
def read_file_content(path: str):
    """尝试用多种编码读取文本文件，失败（如二进制文件）返回 None。"""
    ext = os.path.splitext(path)[1].lower()
    if ext in LIKELY_BINARY_EXT:
        return None
    for enc in ("utf-8", "utf-8-sig", "gbk", "gb18030", "big5", "latin-1"):
        try:
            with open(path, "r", encoding=enc) as f:
                content = f.read()
            if "\x00" in content:
                return None
            return content
        except (UnicodeDecodeError, LookupError):
            continue
        except Exception:
            return None
    return None


# ----------------------------------------------------------------------
# 按 token 上限对长文本进行拆分（用于单个文件内容本身就超过上限的情况）
# ----------------------------------------------------------------------
def chunk_text_by_tokens(text: str, max_tokens: int):
    if max_tokens <= 0:
        max_tokens = 200
    lines = text.split("\n")
    chunks = []
    current = []
    current_tokens = 0

    def flush_current():
        if current:
            chunks.append("\n".join(current))

    for line in lines:
        line_tokens = count_tokens(line)
        if line_tokens > max_tokens:
            flush_current()
            current.clear()
            current_tokens = 0
            approx_chars_per_chunk = max(1, int(len(line) * max_tokens / max(1, line_tokens)))
            for i in range(0, len(line), approx_chars_per_chunk):
                chunks.append(line[i:i + approx_chars_per_chunk])
            continue
        if current_tokens + line_tokens > max_tokens and current:
            flush_current()
            current = []
            current_tokens = 0
        current.append(line)
        current_tokens += line_tokens

    flush_current()
    return chunks if chunks else [text]


SEP_LINE = "=" * 60


# ----------------------------------------------------------------------
# 后台处理 Worker（跑在 QThread 中，避免界面卡死）
# ----------------------------------------------------------------------
class Worker(QObject):
    log = Signal(str)
    finished = Signal()

    def __init__(self, folder, token_limit, recursive, do_filter, out_dir, prefix):
        super().__init__()
        self.folder = folder
        self.token_limit = token_limit
        self.recursive = recursive
        self.do_filter = do_filter
        self.out_dir = out_dir
        self.prefix = prefix

    def _collect_files(self):
        files = []
        if self.recursive:
            for root, _dirs, names in os.walk(self.folder):
                for name in names:
                    files.append(os.path.join(root, name))
        else:
            for name in sorted(os.listdir(self.folder)):
                full = os.path.join(self.folder, name)
                if os.path.isfile(full):
                    files.append(full)
        return sorted(files)

    def run(self):
        try:
            files = self._collect_files()
            self.log.emit(f"共发现 {len(files)} 个文件，开始读取...")

            current_parts = []
            current_tokens = 0
            file_index = 1
            written_count = 0
            skipped = 0
            processed = 0

            def flush():
                nonlocal current_parts, current_tokens, file_index, written_count
                if not current_parts:
                    return
                out_name = f"{self.prefix}_{file_index:03d}.txt"
                out_path = os.path.join(self.out_dir, out_name)
                with open(out_path, "w", encoding="utf-8") as f:
                    f.write(("\n\n" + SEP_LINE + "\n\n").join(current_parts))
                written_count += 1
                self.log.emit(f"已写出：{out_name}（约 {current_tokens} tokens，含 {len(current_parts)} 段）")
                file_index += 1
                current_parts = []
                current_tokens = 0

            for filepath in files:
                content = read_file_content(filepath)
                if content is None:
                    skipped += 1
                    continue
                if self.do_filter:
                    ext = os.path.splitext(filepath)[1]
                    content = filter_lines(content, ext)
                if not content.strip():
                    skipped += 1
                    continue

                rel = os.path.relpath(filepath, self.folder)
                processed += 1

                header = f"{SEP_LINE}\n文件: {rel}\n{SEP_LINE}"
                block_full = header + "\n" + content
                block_tokens = count_tokens(block_full)

                if block_tokens > self.token_limit:
                    header_tokens = count_tokens(header)
                    budget = max(50, self.token_limit - header_tokens - 20)
                    sub_chunks = chunk_text_by_tokens(content, budget)
                    total_parts = len(sub_chunks)
                    for i, sub in enumerate(sub_chunks, 1):
                        sub_header = (
                            f"{SEP_LINE}\n文件: {rel} (分段 {i}/{total_parts})\n{SEP_LINE}"
                        )
                        sub_block = sub_header + "\n" + sub
                        sub_tokens = count_tokens(sub_block)
                        if current_tokens + sub_tokens > self.token_limit and current_parts:
                            flush()
                        current_parts.append(sub_block)
                        current_tokens += sub_tokens
                else:
                    if current_tokens + block_tokens > self.token_limit and current_parts:
                        flush()
                    current_parts.append(block_full)
                    current_tokens += block_tokens

            flush()

            self.log.emit("-" * 40)
            self.log.emit(
                f"处理完成：共处理 {processed} 个文件，跳过 {skipped} 个（二进制/空/无法读取），"
                f"生成 {written_count} 个 txt 文件。"
            )
            self.log.emit(f"输出目录：{self.out_dir}")
            self.log.emit("=" * 40)
        except Exception as e:
            self.log.emit(f"发生错误：{e}")
        finally:
            self.finished.emit()


# ----------------------------------------------------------------------
# 主窗口
# ----------------------------------------------------------------------
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("文件夹内容读取 · 按Token拆分保存工具（PySide2）")
        self.resize(920, 680)

        self.selected_folder = ""
        self.fs_model = None
        self._thread = None
        self._worker = None

        self._build_ui()

    # ---------------- UI ----------------
    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)

        # 顶部：选择文件夹
        top_layout = QHBoxLayout()
        self.btn_choose = QPushButton("选择文件夹")
        self.btn_choose.clicked.connect(self.choose_folder)
        self.path_edit = QLineEdit()
        self.path_edit.setReadOnly(True)
        top_layout.addWidget(self.btn_choose)
        top_layout.addWidget(self.path_edit)
        main_layout.addLayout(top_layout)

        # 中部：树形控件
        self.tree = QTreeView()
        self.tree.setSelectionMode(QTreeView.SingleSelection)
        main_layout.addWidget(self.tree, stretch=3)

        # 选项区
        opts_group = QGroupBox("拆分选项")
        opts_layout = QGridLayout(opts_group)

        opts_layout.addWidget(QLabel("单个txt的Token上限："), 0, 0)
        self.token_edit = QLineEdit("2000")
        self.token_edit.setFixedWidth(100)
        opts_layout.addWidget(self.token_edit, 0, 1)
        method_label = QLabel(f"（{TOKEN_METHOD}）")
        method_label.setStyleSheet("color: #666;")
        opts_layout.addWidget(method_label, 0, 2, 1, 2)

        self.recursive_check = QCheckBox("递归读取所有子文件夹（关闭则只读当前文件夹，不含子文件夹）")
        self.recursive_check.setChecked(True)
        opts_layout.addWidget(self.recursive_check, 1, 0, 1, 4)

        self.filter_check = QCheckBox("过滤注释行与空行")
        self.filter_check.setChecked(False)
        opts_layout.addWidget(self.filter_check, 2, 0, 1, 4)

        opts_layout.addWidget(QLabel("输出文件名前缀："), 3, 0)
        self.prefix_edit = QLineEdit("output")
        self.prefix_edit.setFixedWidth(160)
        opts_layout.addWidget(self.prefix_edit, 3, 1)

        self.btn_start = QPushButton("开始处理并保存")
        self.btn_start.clicked.connect(self.on_start)
        opts_layout.addWidget(self.btn_start, 0, 4, 4, 1)
        opts_layout.setColumnStretch(3, 1)

        main_layout.addWidget(opts_group)

        # 日志区
        log_group = QGroupBox("日志")
        log_layout = QVBoxLayout(log_group)
        self.log_edit = QTextEdit()
        self.log_edit.setReadOnly(True)
        log_layout.addWidget(self.log_edit)
        main_layout.addWidget(log_group, stretch=2)

    # ---------------- 事件处理 ----------------
    def choose_folder(self):
        path = QFileDialog.getExistingDirectory(self, "选择要读取的文件夹")
        if not path:
            return
        self.selected_folder = path
        self.path_edit.setText(path)

        self.fs_model = QFileSystemModel()
        self.fs_model.setRootPath(path)
        self.tree.setModel(self.fs_model)
        self.tree.setRootIndex(self.fs_model.index(path))
        self.tree.setColumnWidth(0, 320)

        self.append_log(f"已加载文件夹：{path}")

    def append_log(self, msg: str):
        self.log_edit.append(msg)

    def on_start(self):
        if not self.selected_folder or not os.path.isdir(self.selected_folder):
            QMessageBox.critical(self, "错误", "请先选择一个有效的文件夹")
            return
        try:
            token_limit = int(self.token_edit.text().strip())
            if token_limit <= 0:
                raise ValueError
        except ValueError:
            QMessageBox.critical(self, "错误", "请输入有效的正整数作为 Token 上限")
            return

        out_dir = QFileDialog.getExistingDirectory(self, "选择保存拆分结果的输出文件夹")
        if not out_dir:
            return

        recursive = self.recursive_check.isChecked()
        do_filter = self.filter_check.isChecked()
        prefix = self.prefix_edit.text().strip() or "output"

        self.append_log("=" * 40)
        self.append_log(
            f"开始处理：文件夹={self.selected_folder}，Token上限={token_limit}，"
            f"递归={'是' if recursive else '否'}，过滤注释空行={'是' if do_filter else '否'}"
        )

        self.btn_start.setEnabled(False)

        self._thread = QThread()
        self._worker = Worker(
            self.selected_folder, token_limit, recursive, do_filter, out_dir, prefix
        )
        self._worker.moveToThread(self._thread)

        self._thread.started.connect(self._worker.run)
        self._worker.log.connect(self.append_log)
        self._worker.finished.connect(self._on_finished)
        self._worker.finished.connect(self._thread.quit)
        self._worker.finished.connect(self._worker.deleteLater)
        self._thread.finished.connect(self._thread.deleteLater)

        self._thread.start()

    def _on_finished(self):
        self.btn_start.setEnabled(True)


def main():
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
