"""
代码合并工具组件模块
支持配置持久化、打开目标文件夹、一键合并导出
"""
from __future__ import annotations

import ast
import os
import re
from typing import List, Optional, Set, Tuple

from PySide2.QtCore import QMimeData, QSettings, QUrl, Qt
from PySide2.QtGui import QDesktopServices
from PySide2.QtWidgets import (
    QApplication,
    QButtonGroup,
    QCheckBox,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

try:
    import tiktoken

    TIKTOKEN_AVAILABLE = True
except ImportError:
    TIKTOKEN_AVAILABLE = False


def estimate_tokens(text: str) -> int:
    if TIKTOKEN_AVAILABLE:
        try:
            enc = tiktoken.get_encoding("cl100k_base")
            return len(enc.encode(text, disallowed_special=()))
        except Exception:
            pass
    chinese_chars = len(re.findall(r"[\u4e00-\u9fa5]", text))
    other_chars = len(text) - chinese_chars
    return chinese_chars + (other_chars // 4)


def strip_python_comments(code: str) -> str:
    try:
        parsed = ast.parse(code)
        for node in ast.walk(parsed):
            if isinstance(
                node, (ast.FunctionDef, ast.ClassDef, ast.AsyncFunctionDef, ast.Module)
            ):
                if (
                    node.body
                    and isinstance(node.body[0], ast.Expr)
                    and isinstance(node.body[0].value, (ast.Str, ast.Constant))
                ):
                    node.body.pop(0)
    except Exception:
        pass

    lines = []
    for line in code.splitlines():
        line_s = line.strip()
        if line_s.startswith("#"):
            continue
        if "#" in line and (line.count('"') % 2 != 0 or line.count("'") % 2 != 0):
            line = line.split("#")[0]
        lines.append(line)
    return "\n".join(lines)


def strip_generic_comments(code: str) -> str:
    code = re.sub(r"/\*[\s\S]*?\*/", "", code)
    lines = []
    for line in code.splitlines():
        if line.strip().startswith("//"):
            continue
        lines.append(line)
    return "\n".join(lines)


def remove_comments(code: str, file_path: str) -> str:
    ext = os.path.splitext(file_path)[1].lower()
    if ext == ".py":
        return strip_python_comments(code)
    if ext in [".js", ".ts", ".c", ".cpp", ".h", ".hpp", ".java", ".go", ".cs"]:
        return strip_generic_comments(code)
    return code


class CodeMergerWidget(QWidget):
    """代码打包合并 Widget（控件状态可持久化）"""

    SETTINGS_ORG = "ReadPro"
    SETTINGS_APP = "CodeMerger"

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._build_ui()
        self._connect_signals()
        self._load_settings()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        cfg_group = QGroupBox("1. 源路径与基本过滤规则")
        cfg_layout = QVBoxLayout(cfg_group)

        src_bar = QHBoxLayout()
        src_bar.addWidget(QLabel("源文件夹路径:"))
        self.src_edit = QLineEdit()
        self.src_edit.setPlaceholderText("请选择要打包的文件夹…")
        self.btn_browse_src = QPushButton("浏览…")
        self.btn_open_src = QPushButton("打开源目录")
        src_bar.addWidget(self.src_edit, 1)
        src_bar.addWidget(self.btn_browse_src)
        src_bar.addWidget(self.btn_open_src)
        cfg_layout.addLayout(src_bar)

        dest_bar = QHBoxLayout()
        dest_bar.addWidget(QLabel("合并结果导出目录:"))
        self.dest_edit = QLineEdit()
        self.dest_edit.setPlaceholderText("选择存放合并后的 .txt 文件的文件夹…")
        self.btn_browse_dest = QPushButton("浏览…")
        self.btn_open_dest = QPushButton("打开目标文件夹")
        dest_bar.addWidget(self.dest_edit, 1)
        dest_bar.addWidget(self.btn_browse_dest)
        dest_bar.addWidget(self.btn_open_dest)
        cfg_layout.addLayout(dest_bar)

        opts_bar = QHBoxLayout()
        self.chk_non_empty = QCheckBox("排除空文件(0字节)")
        self.chk_non_empty.setChecked(True)
        opts_bar.addWidget(self.chk_non_empty)

        opts_bar.addSpacing(15)
        opts_bar.addWidget(QLabel("排除后缀名(空格分隔):"))
        self.exclude_ext_edit = QLineEdit()
        self.exclude_ext_edit.setPlaceholderText("例如: .log .bak .png")
        opts_bar.addWidget(self.exclude_ext_edit, 1)

        cfg_layout.addLayout(opts_bar)
        layout.addWidget(cfg_group)

        policy_group = QGroupBox("2. 合并拆分策略与处理选项")
        policy_layout = QVBoxLayout(policy_group)

        mode_bar = QHBoxLayout()
        self.bg_mode = QButtonGroup(self)

        self.radio_size_500k = QRadioButton("按文件大小: 500 KB 档位")
        self.radio_size_2m = QRadioButton("按文件大小: 2 MB 档位")
        self.radio_token = QRadioButton("按 Token 数量限额:")
        self.radio_size_500k.setChecked(True)

        self.bg_mode.addButton(self.radio_size_500k, 0)
        self.bg_mode.addButton(self.radio_size_2m, 1)
        self.bg_mode.addButton(self.radio_token, 2)

        mode_bar.addWidget(self.radio_size_500k)
        mode_bar.addWidget(self.radio_size_2m)
        mode_bar.addWidget(self.radio_token)

        self.spin_token_limit = QSpinBox()
        self.spin_token_limit.setRange(10000, 2000000)
        self.spin_token_limit.setSingleStep(50000)
        self.spin_token_limit.setValue(200000)
        self.spin_token_limit.setSuffix(" Tokens")
        mode_bar.addWidget(self.spin_token_limit)
        mode_bar.addStretch()
        policy_layout.addLayout(mode_bar)

        extra_opts_bar = QHBoxLayout()
        self.chk_remove_comments = QCheckBox("合并时尝试清理代码注释")
        self.chk_remove_comments.setChecked(False)
        extra_opts_bar.addWidget(self.chk_remove_comments)

        token_hint = (
            "【Tiktoken 已就绪】精确计算 Token"
            if TIKTOKEN_AVAILABLE
            else "【Tiktoken 未安装】使用字符算法估算 Token"
        )
        self.lbl_token_hint = QLabel(token_hint)
        self.lbl_token_hint.setStyleSheet("color: #666;")
        extra_opts_bar.addSpacing(20)
        extra_opts_bar.addWidget(self.lbl_token_hint)
        extra_opts_bar.addStretch()
        policy_layout.addLayout(extra_opts_bar)
        layout.addWidget(policy_group)

        act_bar = QHBoxLayout()
        self.btn_run_merge = QPushButton("🚀 开始合并代码并导出文件")
        self.btn_run_merge.setFixedHeight(40)
        self.btn_run_merge.setStyleSheet(
            "background-color: #4CAF50; color: white; font-weight: bold;"
        )
        act_bar.addWidget(self.btn_run_merge)
        layout.addLayout(act_bar)

        self.list_tabs = QTabWidget()
        self.merged_result_list = QListWidget()
        self.filtered_list_widget = QListWidget()
        self.list_tabs.addTab(self.merged_result_list, "📦 生成的合并文件列表")
        self.list_tabs.addTab(
            self.filtered_list_widget, "🚫 已过滤/跳过的文件清单 (0)"
        )
        layout.addWidget(self.list_tabs, 1)

    def _connect_signals(self) -> None:
        self.btn_browse_src.clicked.connect(self._browse_src)
        self.btn_browse_dest.clicked.connect(self._browse_dest)
        self.btn_open_src.clicked.connect(self._open_src_folder)
        self.btn_open_dest.clicked.connect(self._open_dest_folder)
        self.btn_run_merge.clicked.connect(self.run_merge_process)

        self.src_edit.editingFinished.connect(self._save_settings)
        self.dest_edit.editingFinished.connect(self._save_settings)
        self.chk_non_empty.toggled.connect(self._save_settings)
        self.exclude_ext_edit.editingFinished.connect(self._save_settings)
        self.chk_remove_comments.toggled.connect(self._save_settings)
        self.spin_token_limit.valueChanged.connect(self._save_settings)
        self.radio_size_500k.toggled.connect(self._save_settings)
        self.radio_size_2m.toggled.connect(self._save_settings)
        self.radio_token.toggled.connect(self._save_settings)

    def _settings(self) -> QSettings:
        return QSettings(self.SETTINGS_ORG, self.SETTINGS_APP)

    def _load_settings(self) -> None:
        s = self._settings()
        self.src_edit.setText(str(s.value("src_path", "") or ""))
        self.dest_edit.setText(str(s.value("dest_path", "") or ""))
        self.chk_non_empty.setChecked(s.value("exclude_empty", True, type=bool))
        self.exclude_ext_edit.setText(str(s.value("exclude_exts", "") or ""))
        self.chk_remove_comments.setChecked(
            s.value("remove_comments", False, type=bool)
        )
        self.spin_token_limit.setValue(int(s.value("token_limit", 200000)))
        mode = int(s.value("split_mode", 0))
        if mode == 1:
            self.radio_size_2m.setChecked(True)
        elif mode == 2:
            self.radio_token.setChecked(True)
        else:
            self.radio_size_500k.setChecked(True)

    def _save_settings(self) -> None:
        s = self._settings()
        s.setValue("src_path", self.src_edit.text().strip())
        s.setValue("dest_path", self.dest_edit.text().strip())
        s.setValue("exclude_empty", self.chk_non_empty.isChecked())
        s.setValue("exclude_exts", self.exclude_ext_edit.text().strip())
        s.setValue("remove_comments", self.chk_remove_comments.isChecked())
        s.setValue("token_limit", self.spin_token_limit.value())
        if self.radio_size_2m.isChecked():
            mode = 1
        elif self.radio_token.isChecked():
            mode = 2
        else:
            mode = 0
        s.setValue("split_mode", mode)
        s.sync()

    def set_source_path(self, path: str) -> None:
        if os.path.isdir(path):
            self.src_edit.setText(path)
            self._save_settings()

    def _browse_src(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "选择源代码文件夹")
        if path:
            self.src_edit.setText(path)
            self._save_settings()

    def _browse_dest(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "选择导出目标文件夹")
        if path:
            self.dest_edit.setText(path)
            self._save_settings()

    def _open_src_folder(self) -> None:
        path = self.src_edit.text().strip()
        if not os.path.isdir(path):
            QMessageBox.warning(self, "提示", "源文件夹路径无效或不存在。")
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(path))

    def _open_dest_folder(self) -> None:
        path = self.dest_edit.text().strip()
        if not os.path.isdir(path):
            QMessageBox.warning(self, "提示", "目标文件夹路径无效或不存在。")
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(path))

    def _get_exclude_exts(self) -> Set[str]:
        raw_text = self.exclude_ext_edit.text().strip().lower()
        if not raw_text:
            return set()
        ext_set = set()
        for p in raw_text.split():
            if not p.startswith("."):
                p = "." + p
            ext_set.add(p)
        return ext_set

    def _build_tree_str(self, root_dir: str, file_paths: List[str]) -> str:
        rel_paths = [os.path.relpath(p, root_dir) for p in file_paths]
        lines = [
            "=" * 60,
            f"【本部分包含的文件架构树】 (根目录: {os.path.basename(root_dir)})",
            "=" * 60,
        ]
        tree = {}
        for rel in rel_paths:
            parts = rel.split(os.sep)
            curr = tree
            for part in parts:
                curr = curr.setdefault(part, {})

        def _render_tree(node, prefix=""):
            items = sorted(node.keys())
            count = len(items)
            for idx, item in enumerate(items):
                is_last = idx == count - 1
                connector = "└── " if is_last else "├── "
                lines.append(f"{prefix}{connector}{item}")
                if node[item]:
                    new_prefix = prefix + ("    " if is_last else "│   ")
                    _render_tree(node[item], new_prefix)

        _render_tree(tree)
        lines.append("=" * 60 + "\n")
        return "\n".join(lines)

    def run_merge_process(self) -> None:
        self._save_settings()
        src_dir = self.src_edit.text().strip()
        dest_dir = self.dest_edit.text().strip()

        if not os.path.isdir(src_dir):
            QMessageBox.warning(self, "路径无效", "请选择有效的源代码文件夹！")
            return
        if not os.path.isdir(dest_dir):
            QMessageBox.warning(
                self, "导出路径无效", "请选择保存合并结果的目标文件夹！"
            )
            return

        only_non_empty = self.chk_non_empty.isChecked()
        strip_comments = self.chk_remove_comments.isChecked()
        exclude_exts = self._get_exclude_exts()

        valid_files: List[str] = []
        filtered_files: List[str] = []

        for root, _, files in os.walk(src_dir):
            for f in sorted(files):
                full_p = os.path.join(root, f)
                _, ext = os.path.splitext(f)
                ext = ext.lower()

                if exclude_exts and ext in exclude_exts:
                    filtered_files.append(
                        f"{full_p}  [原因: 匹配排除后缀 '{ext}']"
                    )
                    continue
                try:
                    if only_non_empty and os.path.getsize(full_p) == 0:
                        filtered_files.append(f"{full_p}  [原因: 空文件 (0 字节)]")
                        continue
                except OSError:
                    continue
                valid_files.append(full_p)

        self.filtered_list_widget.clear()
        for f_item in filtered_files:
            self.filtered_list_widget.addItem(f_item)
        self.list_tabs.setTabText(
            1, f"🚫 已过滤/跳过的文件清单 ({len(filtered_files)})"
        )

        if not valid_files:
            QMessageBox.information(
                self, "扫描结果", "未搜集到任何符合条件的可合并文件。"
            )
            return

        use_token_mode = self.radio_token.isChecked()
        if self.radio_size_500k.isChecked():
            limit_value = 500 * 1024
        elif self.radio_size_2m.isChecked():
            limit_value = 2 * 1024 * 1024
        else:
            limit_value = self.spin_token_limit.value()

        batches: List[List[Tuple[str, str]]] = []
        current_batch: List[Tuple[str, str]] = []
        current_batch_cost = 0

        for fpath in valid_files:
            try:
                with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
            except Exception as e:
                filtered_files.append(f"{fpath}  [原因: 读取失败 {e}]")
                continue

            if strip_comments:
                content = remove_comments(content, fpath)

            rel_path = os.path.relpath(fpath, src_dir)
            ext = os.path.splitext(fpath)[1].lstrip(".")
            block_text = f"\n\n# FILE: {rel_path}\n```{ext}\n{content}\n```\n"

            if use_token_mode:
                cost = estimate_tokens(block_text)
            else:
                cost = len(block_text.encode("utf-8"))

            if current_batch and current_batch_cost + cost > limit_value:
                batches.append(current_batch)
                current_batch = []
                current_batch_cost = 0

            current_batch.append((fpath, block_text))
            current_batch_cost += cost

        if current_batch:
            batches.append(current_batch)

        # 3. 导出文件名加上当前项目的前缀
        project_prefix = os.path.basename(os.path.normpath(src_dir)) or "merged"

        self.merged_result_list.clear()
        written = []
        for i, batch in enumerate(batches, start=1):
            paths_in_batch = [p for p, _ in batch]
            header = self._build_tree_str(src_dir, paths_in_batch)
            body = "".join(text for _, text in batch)
            out_name = f"{project_prefix}_merged_part{i}.txt"
            out_path = os.path.join(dest_dir, out_name)
            try:
                with open(out_path, "w", encoding="utf-8") as f:
                    f.write(header)
                    f.write(body)
                written.append(out_path)
                self.merged_result_list.addItem(out_path)
            except Exception as e:
                QMessageBox.warning(self, "写入失败", f"{out_path}\n{e}")

        self.list_tabs.setTabText(
            1, f"🚫 已过滤/跳过的文件清单 ({len(filtered_files)})"
        )
        QMessageBox.information(
            self,
            "合并完成",
            f"共处理有效文件 {len(valid_files)} 个\n"
            f"生成合并文件 {len(written)} 个\n"
            f"导出目录: {dest_dir}",
        )

    def do_one_click_merge(self, folder_paths: List[str], project_root: Optional[str] = None) -> List[str]:
        """
        供外部调用的“一键代码合并”功能：
        按照当前保存的策略，把所选文件夹合并导出，并复制结果到系统剪贴板
        """
        self._save_settings()
        dest_dir = self.dest_edit.text().strip()
        if not os.path.isdir(dest_dir):
            QMessageBox.warning(
                self, "导出路径无效", "请先在【代码合并工具】选项卡设置有效的合并结果导出目录！"
            )
            return []

        only_non_empty = self.chk_non_empty.isChecked()
        strip_comments = self.chk_remove_comments.isChecked()
        exclude_exts = self._get_exclude_exts()

        # 确定参考的基准根路径（用于计算相对路径与前缀名）
        base_dir = project_root if (project_root and os.path.isdir(project_root)) else (
            self.src_edit.text().strip() if os.path.isdir(self.src_edit.text().strip()) else folder_paths[0]
        )

        seen_files = set()
        valid_files: List[str] = []
        filtered_files: List[str] = []

        for folder in folder_paths:
            if not os.path.exists(folder):
                continue
            for root, _, files in os.walk(folder):
                for f in sorted(files):
                    full_p = os.path.join(root, f)
                    if full_p in seen_files:
                        continue
                    seen_files.add(full_p)

                    _, ext = os.path.splitext(f)
                    ext = ext.lower()

                    if exclude_exts and ext in exclude_exts:
                        filtered_files.append(f"{full_p}  [原因: 匹配排除后缀 '{ext}']")
                        continue
                    try:
                        if only_non_empty and os.path.getsize(full_p) == 0:
                            filtered_files.append(f"{full_p}  [原因: 空文件 (0 字节)]")
                            continue
                    except OSError:
                        continue
                    valid_files.append(full_p)

        if not valid_files:
            QMessageBox.information(
                self, "扫描结果", "所选文件夹中未搜集到任何符合条件的可合并文件。"
            )
            return []

        use_token_mode = self.radio_token.isChecked()
        if self.radio_size_500k.isChecked():
            limit_value = 500 * 1024
        elif self.radio_size_2m.isChecked():
            limit_value = 2 * 1024 * 1024
        else:
            limit_value = self.spin_token_limit.value()

        batches: List[List[Tuple[str, str]]] = []
        current_batch: List[Tuple[str, str]] = []
        current_batch_cost = 0

        for fpath in valid_files:
            try:
                with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
            except Exception as e:
                filtered_files.append(f"{fpath}  [原因: 读取失败 {e}]")
                continue

            if strip_comments:
                content = remove_comments(content, fpath)

            try:
                rel_path = os.path.relpath(fpath, base_dir)
            except ValueError:
                rel_path = fpath

            ext = os.path.splitext(fpath)[1].lstrip(".")
            block_text = f"\n\n# FILE: {rel_path}\n```{ext}\n{content}\n```\n"

            if use_token_mode:
                cost = estimate_tokens(block_text)
            else:
                cost = len(block_text.encode("utf-8"))

            if current_batch and current_batch_cost + cost > limit_value:
                batches.append(current_batch)
                current_batch = []
                current_batch_cost = 0

            current_batch.append((fpath, block_text))
            current_batch_cost += cost

        if current_batch:
            batches.append(current_batch)

        project_prefix = os.path.basename(os.path.normpath(base_dir)) or "merged"

        written = []
        for i, batch in enumerate(batches, start=1):
            paths_in_batch = [p for p, _ in batch]
            header = self._build_tree_str(base_dir, paths_in_batch)
            body = "".join(text for _, text in batch)
            out_name = f"{project_prefix}_merged_part{i}.txt"
            out_path = os.path.join(dest_dir, out_name)
            try:
                with open(out_path, "w", encoding="utf-8") as f:
                    f.write(header)
                    f.write(body)
                written.append(out_path)
            except Exception as e:
                QMessageBox.warning(self, "写入失败", f"{out_path}\n{e}")

        if written:
            # 复制导出的文件对象到系统剪贴板
            clipboard = QApplication.clipboard()
            mime_data = QMimeData()
            urls = [QUrl.fromLocalFile(p) for p in written]
            mime_data.setUrls(urls)
            clipboard.setMimeData(mime_data)

            # 弹出对话框提示复制文件成功
            file_names = [os.path.basename(p) for p in written]
            names_str = "\n".join([f"- {name}" for name in file_names])
            msg = (
                f"一键代码合并完成并已自动复制到剪贴板！\n\n"
                f"成功导出并复制了 {len(written)} 个合并文件：\n"
                f"{names_str}"
            )
            QMessageBox.information(self, "一键代码合并成功", msg)

        return written