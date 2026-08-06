# -*- coding:utf-8 -*-
import os
import json
import re
from PySide2.QtWidgets import QWidget, QMessageBox, QMenu, QAction
from PySide2.QtCore import Qt, QTimer, Signal

from .ui_builder import ProjectCreatorUI
from .handlers import EventHandlers
from .modification_manager import ModificationManager


def extract_json_from_response(text):
    """从 AI 响应中提取 JSON"""
    if not text:
        return None
    def strip_line_numbers(content):
        lines = content.splitlines()
        stripped_lines = []
        for line in lines:
            stripped = re.sub(r'^\s*\d+[\.\)]?\s*', '', line)
            stripped_lines.append(stripped)
        return '\n'.join(stripped_lines)
    candidates = []
    match = re.search(r'```json\s*([\s\S]*?)\s*```', text)
    if match:
        candidates.append(match.group(1).strip())
    match = re.search(r'```\s*([\s\S]*?)\s*```', text)
    if match:
        candidates.append(match.group(1).strip())
    match = re.search(r'【?[\u4e00-\u9fa5]*\s*(?:json|JSON|代码块|结果)\s*】?\s*([\s\S]*?)\s*【?[\u4e00-\u9fa5]*\s*(?:结束|结尾|完毕)\s*】?', text)
    if match:
        candidates.append(match.group(1).strip())
    candidates.append(text.strip())
    for raw in candidates:
        cleaned = strip_line_numbers(raw)
        try:
            return json.loads(cleaned)
        except:
            pass
        json_match = re.search(r'(\{[\s\S]*\}|\[[\s\S]*\])', cleaned)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except:
                pass
    json_match = re.search(r'(\{[\s\S]*\})', text)
    if json_match:
        try:
            candidate = json_match.group(1)
            cleaned = strip_line_numbers(candidate)
            return json.loads(cleaned)
        except:
            pass
    return None


class ProjectCreatorWidget(QWidget):
    """项目创建器主控件"""

    ai_response_received = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_file = ""
        self.stage = 'idle'
        self.elapsed_seconds = 0
        self.timer = QTimer()

        self.controls = ProjectCreatorUI.setup_ui(self)
        self.file_manager = self.controls['file_manager']

        self.handlers = EventHandlers(self, self.controls)
        self.modification_manager = ModificationManager(self)

        self._bind_signals()
        self._setup_context_menu()

    def _setup_context_menu(self):
        """为反馈列表添加右键菜单"""
        self.controls['feedback_list'].setContextMenuPolicy(Qt.CustomContextMenu)
        self.controls['feedback_list'].customContextMenuRequested.connect(self._show_feedback_context_menu)

    def _show_feedback_context_menu(self, position):
        item = self.controls['feedback_list'].itemAt(position)
        if not item:
            return
        menu = QMenu(self)
        remove_action = QAction("🗑 移除该项", self)
        remove_action.triggered.connect(self.modification_manager.remove_selected)
        menu.addAction(remove_action)
        # 可选：添加"移除所有"等
        menu.exec_(self.controls['feedback_list'].viewport().mapToGlobal(position))

    def _bind_signals(self):
        # 文件管理器
        self.file_manager.file_selected.connect(self.handlers.on_file_selected)
        self.file_manager.directory_changed.connect(self.handlers.on_directory_changed)

        # 按钮
        self.controls['btn_build'].clicked.connect(self.handlers.send_build_request)
        self.controls['btn_improve'].clicked.connect(self.handlers.send_improve_request)
        self.controls['btn_clear'].clicked.connect(self.handlers.on_clear)
        self.controls['btn_unblock'].clicked.connect(self.handlers.unblock)
        self.controls['btn_run'].clicked.connect(self.handlers.run_current_file)
        self.controls['btn_feedback_ai'].clicked.connect(self.handlers.send_error_to_ai)

        # 查看 Prompt 按钮
        self.controls['btn_view_build_prompt'].clicked.connect(self.handlers.view_build_prompt)
        self.controls['btn_view_improve_prompt'].clicked.connect(self.handlers.view_improve_prompt)
        self.controls['btn_view_feedback_prompt'].clicked.connect(self.handlers.view_feedback_prompt)

        # 修改记录
        self.controls['btn_apply_selected'].clicked.connect(self.modification_manager.apply_selected)
        self.controls['btn_undo_selected'].clicked.connect(self.modification_manager.undo_selected)
        self.controls['btn_apply_all'].clicked.connect(self.modification_manager.apply_all)
        self.controls['btn_undo_all'].clicked.connect(self.modification_manager.undo_all)

        # 列表选择
        self.controls['feedback_list'].itemSelectionChanged.connect(self.modification_manager.on_selection_changed)

        # 大纲树
        self.controls['outline_tree'].itemClicked.connect(self.handlers.on_outline_clicked)

        # 编辑器更新大纲
        self.controls['code_editor'].textChanged.connect(self.handlers._update_outline)

        # 定时器
        self.timer.timeout.connect(self.handlers.update_timer)

    def append_ai_result(self, text):
        if self.stage != 'generating':
            return

        self.timer.stop()
        data = extract_json_from_response(text)
        if data is None:
            self.controls['log_text'].append("❌ 未能从响应中提取JSON数据")
            self.controls['log_text'].append(f"响应预览: {text[:200]}...")
            self.controls['status_label'].setText("❌ 解析AI响应失败")
            self.handlers._reset_state()
            return

        if isinstance(data, list):
            self.modification_manager.display_modifications(data)
        elif isinstance(data, dict):
            if 'files' in data and isinstance(data['files'], list):
                self.modification_manager.display_modifications(data['files'])
            elif 'path' in data and 'content' in data:
                self.modification_manager.display_modifications([data])
            else:
                self.controls['log_text'].append("⚠️ AI响应格式无法识别")
                self.handlers._reset_state()
                return
        else:
            self.controls['log_text'].append("⚠️ AI响应不是列表或字典")
            self.handlers._reset_state()
            return

        self.controls['status_label'].setText(f"收到 {len(self.modification_manager.modification_history)} 个文件")
        self.handlers.after_response()