# -*- coding: utf-8 -*-
from datetime import datetime
from PySide2.QtCore import QObject, Slot
from core.prompt_manager import PromptManager


class WorkspaceController(QObject):
    """工作台Tab的业务控制器"""

    def __init__(self, bridge, prompt_manager, log_viewer, history_view, parent=None):
        super().__init__(parent)
        self.bridge = bridge
        self.prompt_mgr = prompt_manager
        self.log_viewer = log_viewer
        self.history_view = history_view

    def send_command(self, user_input, prompt_title, prompt_editors):
        if not user_input.strip():
            return
        editor = prompt_editors.get(prompt_title)
        if not editor:
            return
        template = editor.toPlainText()
        final = PromptManager.render(template, user_input)

        self.bridge.send_to_extension(final)
        self.log_viewer.append_log("指令发送", f"已下发指令 (场景: [{prompt_title}])", "SEND")

        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        html = (
            f'<div style="border-bottom: 2px solid #ddd; margin-bottom: 12px; padding-bottom: 8px;">'
            f'<div style="background-color: #e3f2fd; padding: 4px 8px; font-weight: bold; color: #0d47a1;">'
            f'🕒 {ts} | 场景: [{prompt_title}]</div>'
            f'<pre style="background: #f5f5f5; padding: 8px; margin: 0;">{final}</pre></div>'
        )
        self.history_view.append(html)

    def save_prompt(self, title, editor):
        if editor:
            self.prompt_mgr.save_prompt(title, editor.toPlainText())
            self.log_viewer.append_log("配置持久化", f"场景 [{title}] 的 Prompt 已保存。", "CONFIG")

    def on_dir_changed(self, new_dir):
        self.log_viewer.append_log("目录更改", f"保存路径变更为: {new_dir}", "CONFIG")
