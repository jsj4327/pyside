# -*- coding: utf-8 -*-
"""
分批文件复制管理组件模块
用于对文件夹内文件按批次（如每批10个）进行复制/导出，支持排除特定扩展名及空文件
"""
from __future__ import annotations

import os
import shutil
from typing import List, Optional, Set

from PySide2.QtCore import QMimeData, QUrl, Qt
from PySide2.QtWidgets import (
    QApplication,
    QCheckBox,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)


class BatchCopyWidget(QWidget):
    """分批次文件复制管理 Widget"""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._all_files: List[str] = []
        self._batches: List[List[str]] = []
        self._current_batch_index: int = 0
        self._clipboard_mime: Optional[QMimeData] = None

        self._build_ui()
        self._connect_signals()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # 1. 路径与配置区域
        cfg_group = QGroupBox("1. 源文件夹与分批规则配置")
        cfg_layout = QVBoxLayout(cfg_group)

        # 源文件夹选择
        src_bar = QHBoxLayout()
        src_bar.addWidget(QLabel("源文件夹路径:"))
        self.src_edit = QLineEdit()
        self.src_edit.setPlaceholderText("请选择要分批复制的源文件夹…")
        self.btn_browse_src = QPushButton("浏览…")
        src_bar.addWidget(self.src_edit, 1)
        src_bar.addWidget(self.btn_browse_src)
        cfg_layout.addLayout(src_bar)

        # 目标文件夹选择 (可选，用于直接写到目录)
        dest_bar = QHBoxLayout()
        dest_bar.addWidget(QLabel("目标文件夹(可选):"))
        self.dest_edit = QLineEdit()
        self.dest_edit.setPlaceholderText("选填：直接物理复制的目标目录…")
        self.btn_browse_dest = QPushButton("浏览…")
        dest_bar.addWidget(self.dest_edit, 1)
        dest_bar.addWidget(self.btn_browse_dest)
        cfg_layout.addLayout(dest_bar)

        # 过滤与参数配置
        opts_bar = QHBoxLayout()
        
        # 勾选框：非空文件
        self.chk_non_empty = QCheckBox("排除空文件(0字节)")
        self.chk_non_empty.setChecked(True)
        opts_bar.addWidget(self.chk_non_empty)

        # 批次大小
        opts_bar.addSpacing(15)
        opts_bar.addWidget(QLabel("每批数量:"))
        self.spin_batch_size = QSpinBox()
        self.spin_batch_size.setRange(1, 500)
        self.spin_batch_size.setValue(10)  # 默认每次10个
        opts_bar.addWidget(self.spin_batch_size)

        # 扩展名排除过滤输入框
        opts_bar.addSpacing(15)
        opts_bar.addWidget(QLabel("排除后缀名(空格分隔):"))
        self.exclude_ext_edit = QLineEdit()
        self.exclude_ext_edit.setPlaceholderText("例如: .txt .log .bak")
        self.exclude_ext_edit.setToolTip("输入需要过滤掉的文件扩展名，用空格隔开（不区分大小写）")
        opts_bar.addWidget(self.exclude_ext_edit, 1)

        # 扫描按钮
        opts_bar.addSpacing(10)
        self.btn_scan = QPushButton("🔍 开始扫描并拆分批次")
        self.btn_scan.setStyleSheet("font-weight: bold; padding: 5px 15px;")
        opts_bar.addWidget(self.btn_scan)

        cfg_layout.addLayout(opts_bar)
        layout.addWidget(cfg_group)

        # 2. 状态与控制区域
        ctrl_group = QGroupBox("2. 分批进度与控制面板")
        ctrl_layout = QVBoxLayout(ctrl_group)

        self.lbl_status = QLabel("状态: 尚未进行扫描")
        self.lbl_status.setStyleSheet("font-weight: bold; color: #333;")
        ctrl_layout.addWidget(self.lbl_status)

        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        ctrl_layout.addWidget(self.progress_bar)

        btn_bar = QHBoxLayout()
        self.btn_copy_clipboard = QPushButton("📋 复制【当前批次】文件到系统剪贴板")
        self.btn_copy_clipboard.setFixedHeight(35)
        self.btn_copy_clipboard.setEnabled(False)
        self.btn_copy_clipboard.setStyleSheet("background-color: #e3f2fd; font-weight: bold;")

        self.btn_copy_direct = QPushButton("📂 直接复制【当前批次】到目标目录")
        self.btn_copy_direct.setFixedHeight(35)
        self.btn_copy_direct.setEnabled(False)

        self.btn_reset = QPushButton("↺ 重置批次")
        self.btn_reset.setFixedHeight(35)

        btn_bar.addWidget(self.btn_copy_clipboard, 2)
        btn_bar.addWidget(self.btn_copy_direct, 2)
        btn_bar.addWidget(self.btn_reset, 1)
        ctrl_layout.addLayout(btn_bar)

        layout.addWidget(ctrl_group)

        # 3. 文件展示区（包含当前批次清单 & 被过滤文件清单 Tab）
        self.list_tabs = QTabWidget()

        # 当前批次文件列表
        self.file_list_widget = QListWidget()
        self.list_tabs.addTab(self.file_list_widget, "📄 当前批次包含的文件清单")

        # 被过滤/跳过的文件列表
        self.filtered_list_widget = QListWidget()
        self.list_tabs.addTab(self.filtered_list_widget, "🚫 已过滤/跳过的文件清单 (0)")

        layout.addWidget(self.list_tabs, 1)

    def _connect_signals(self) -> None:
        self.btn_browse_src.clicked.connect(self._browse_src)
        self.btn_browse_dest.clicked.connect(self._browse_dest)
        self.btn_scan.clicked.connect(self.scan_and_prepare_batches)
        self.btn_copy_clipboard.clicked.connect(self._copy_current_batch_to_clipboard)
        self.btn_copy_direct.clicked.connect(self._copy_current_batch_to_directory)
        self.btn_reset.clicked.connect(self._reset_batch)

    def set_source_path(self, path: str) -> None:
        """从外部设置源文件夹"""
        if os.path.isdir(path):
            self.src_edit.setText(path)

    def _browse_src(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "选择源文件夹")
        if path:
            self.src_edit.setText(path)

    def _browse_dest(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "选择目标保存文件夹")
        if path:
            self.dest_edit.setText(path)

    def _get_exclude_exts(self) -> Set[str]:
        """解析输入的需要过滤的扩展名集合"""
        raw_text = self.exclude_ext_edit.text().strip().lower()
        if not raw_text:
            return set()
        
        parts = raw_text.split()
        ext_set = set()
        for p in parts:
            if not p.startswith("."):
                p = "." + p
            ext_set.add(p)
        return ext_set

    def scan_and_prepare_batches(self) -> None:
        """扫描文件夹内文件，应用过滤规则并划分为批次"""
        src_dir = self.src_edit.text().strip()
        if not os.path.isdir(src_dir):
            QMessageBox.warning(self, "路径无效", "请选择有效的源文件夹！")
            return

        only_non_empty = self.chk_non_empty.isChecked()
        batch_size = self.spin_batch_size.value()
        exclude_exts = self._get_exclude_exts()

        all_files: List[str] = []
        filtered_files: List[str] = []

        # 遍历与过滤文件
        for root, _, files in os.walk(src_dir):
            for f in sorted(files):
                full_p = os.path.join(root, f)
                _, ext = os.path.splitext(f)
                ext = ext.lower()

                # 规则 1: 检查特定后缀扩展名是否过滤
                if exclude_exts and ext in exclude_exts:
                    filtered_files.append(f"{full_p}  [原因: 匹配排除后缀 '{ext}']")
                    continue

                # 规则 2: 检查文件大小（是否为0字节空文件）
                if only_non_empty and os.path.getsize(full_p) == 0:
                    filtered_files.append(f"{full_p}  [原因: 空文件 (0 字节)]")
                    continue

                all_files.append(full_p)

        # 显示被过滤掉的文件列表
        self.filtered_list_widget.clear()
        for f_item in filtered_files:
            self.filtered_list_widget.addItem(f_item)
        self.list_tabs.setTabText(1, f"🚫 已过滤/跳过的文件清单 ({len(filtered_files)})")

        if not all_files:
            QMessageBox.information(
                self,
                "扫描结果",
                f"未能搜集到符合条件的文件。\n跳过/过滤了 {len(filtered_files)} 个文件。",
            )
            self._reset_batch()
            return

        self._all_files = all_files
        self._batches = [
            all_files[i : i + batch_size] for i in range(0, len(all_files), batch_size)
        ]
        self._current_batch_index = 0

        self.btn_copy_clipboard.setEnabled(True)
        self.btn_copy_direct.setEnabled(bool(self.dest_edit.text().strip()))

        self._update_ui_state()
        QMessageBox.information(
            self,
            "拆分完成",
            f"扫描完成：\n"
            f"- 保留有效文件：{len(all_files)} 个\n"
            f"- 已过滤排除文件：{len(filtered_files)} 个\n"
            f"- 每批最多 {batch_size} 个，已拆分为 {len(self._batches)} 批次！",
        )

    def _update_ui_state(self) -> None:
        total_batches = len(self._batches)
        if total_batches == 0:
            self.lbl_status.setText("状态: 尚未进行扫描")
            self.progress_bar.setValue(0)
            self.file_list_widget.clear()
            self.btn_copy_clipboard.setEnabled(False)
            self.btn_copy_direct.setEnabled(False)
            return

        current = self._current_batch_index
        if current >= total_batches:
            self.lbl_status.setText(f"🎉 全部复制完成！共 {total_batches} 批次，所有文件已处理完。")
            self.progress_bar.setValue(100)
            self.file_list_widget.clear()
            self.btn_copy_clipboard.setEnabled(False)
            self.btn_copy_direct.setEnabled(False)
            return

        progress_pct = int((current / total_batches) * 100)
        self.progress_bar.setValue(progress_pct)

        cur_files = self._batches[current]
        self.lbl_status.setText(
            f"当前进度: 批次 [{current + 1} / {total_batches}] | 本批包含 {len(cur_files)} 个文件"
        )

        self.file_list_widget.clear()
        for f in cur_files:
            self.file_list_widget.addItem(f)

    def _copy_current_batch_to_clipboard(self) -> None:
        """将当前批次的文件加入系统剪贴板，并将指针指向下一批"""
        if self._current_batch_index >= len(self._batches):
            return

        cur_files = self._batches[self._current_batch_index]
        self._clipboard_mime = QMimeData()
        urls = [QUrl.fromLocalFile(p) for p in cur_files]
        self._clipboard_mime.setUrls(urls)
        QApplication.clipboard().setMimeData(self._clipboard_mime)

        QMessageBox.information(
            self,
            "已复制到剪贴板",
            f"已将第 [{self._current_batch_index + 1}] 批次的 {len(cur_files)} 个文件写入剪贴板！\n"
            "你可以粘贴到指定文件夹中。点击确定后将自动切入下一批次。",
        )

        self._current_batch_index += 1
        self._update_ui_state()

    def _copy_current_batch_to_directory(self) -> None:
        """直接将当前批次文件写入指定的目标目录"""
        dest_dir = self.dest_edit.text().strip()
        if not os.path.isdir(dest_dir):
            QMessageBox.warning(self, "目标路径无效", "请输入或选择有效的目标文件夹！")
            return

        if self._current_batch_index >= len(self._batches):
            return

        cur_files = self._batches[self._current_batch_index]
        errors = []
        for src in cur_files:
            base_name = os.path.basename(src)
            target = os.path.join(dest_dir, base_name)
            try:
                shutil.copy2(src, target)
            except Exception as e:
                errors.append(f"{src}: {e}")

        if errors:
            QMessageBox.warning(self, "复制出错", "\n".join(errors))
        else:
            QMessageBox.information(
                self,
                "复制成功",
                f"第 [{self._current_batch_index + 1}] 批次文件已成功物理复制到:\n{dest_dir}",
            )

        self._current_batch_index += 1
        self._update_ui_state()

    def _reset_batch(self) -> None:
        self._current_batch_index = 0
        self._update_ui_state()