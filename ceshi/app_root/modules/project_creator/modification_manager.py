# -*- coding:utf-8 -*-
import os
from PySide2.QtWidgets import QListWidgetItem, QMessageBox
from PySide2.QtCore import Qt


class ModificationManager:
    def __init__(self, parent):
        self.parent = parent
        self.modification_history = []
        self.last_parse_report = ""

    def display_modifications(self, mod_list):
        """
        显示修改列表，并在下方文本框中展示详细的解析报告
        mod_list: 解析后的文件列表 (list of dict)
        """
        self.modification_history = []
        self.parent.controls['feedback_list'].clear()
        for item in mod_list:
            if isinstance(item, dict) and 'path' in item and 'content' in item:
                file_path = item['path'].replace('\\u005f', '_')
                content = item['content']
                self.modification_history.append({
                    'path': file_path,
                    'content': content,
                    'applied': False
                })
        self._update_list()

        # 构建详细的解析报告
        report_lines = []
        report_lines.append("📊 解析结果报告")
        report_lines.append("=" * 50)
        report_lines.append(f"共解析到 {len(self.modification_history)} 个文件")
        report_lines.append("")
        if self.modification_history:
            report_lines.append("【文件列表】")
            for idx, record in enumerate(self.modification_history, 1):
                status = "待应用" if not record['applied'] else "已应用"
                report_lines.append(f"  {idx}. {record['path']} ({status})")
        else:
            report_lines.append("（无文件）")

        report_lines.append("")
        report_lines.append("【解析信息】")
        report_lines.append(f"• 数据来源: AI 响应")
        report_lines.append(f"• 解析时间: 实时")
        report_lines.append(f"• 解析状态: {'成功' if self.modification_history else '空列表'}")

        report = "\n".join(report_lines)
        self.last_parse_report = report
        self.parent.controls['feedback_content'].setPlainText(report)

        if self.modification_history:
            self.parent.controls['btn_apply_all'].setEnabled(True)
            self.parent.controls['btn_undo_all'].setEnabled(False)
            self.parent.controls['log_text'].append(f"✅ 收到 {len(self.modification_history)} 个修改建议")

    def _update_list(self):
        self.parent.controls['feedback_list'].clear()
        for idx, record in enumerate(self.modification_history):
            status = "✅ 已应用" if record['applied'] else "⏳ 待应用"
            item = QListWidgetItem(f"{os.path.basename(record['path'])}  {status}")
            item.setData(Qt.UserRole, idx)
            self.parent.controls['feedback_list'].addItem(item)

    def on_selection_changed(self):
        """点击列表项时显示文件内容，取消选中则显示解析报告"""
        selected = self.parent.controls['feedback_list'].selectedItems()
        if selected:
            idx = selected[0].data(Qt.UserRole)
            record = self.modification_history[idx]
            # 显示文件内容
            content_display = f"【文件】{record['path']}\n\n{record['content']}"
            self.parent.controls['feedback_content'].setPlainText(content_display)
            self.parent.controls['btn_apply_selected'].setEnabled(not record['applied'])
            self.parent.controls['btn_undo_selected'].setEnabled(record['applied'])
        else:
            # 未选中时显示解析报告
            if self.last_parse_report:
                self.parent.controls['feedback_content'].setPlainText(self.last_parse_report)
            else:
                self.parent.controls['feedback_content'].setPlainText("点击列表项查看文件内容，取消选中查看解析报告")
            self.parent.controls['btn_apply_selected'].setEnabled(False)
            self.parent.controls['btn_undo_selected'].setEnabled(False)

    def apply_selected(self):
        selected = self.parent.controls['feedback_list'].selectedItems()
        if not selected:
            return
        idx = selected[0].data(Qt.UserRole)
        self._apply(idx)

    def undo_selected(self):
        selected = self.parent.controls['feedback_list'].selectedItems()
        if not selected:
            return
        idx = selected[0].data(Qt.UserRole)
        self._undo(idx)

    def apply_all(self):
        for i in range(len(self.modification_history)):
            if not self.modification_history[i]['applied']:
                self._apply(i)
        self.parent.controls['btn_apply_all'].setEnabled(False)

    def undo_all(self):
        for i in range(len(self.modification_history)):
            if self.modification_history[i]['applied']:
                self._undo(i)
        self.parent.controls['btn_undo_all'].setEnabled(False)

    # ---------- 移除选中（支持右键） ----------
    def remove_selected(self):
        selected = self.parent.controls['feedback_list'].selectedItems()
        if not selected:
            return
        idx = selected[0].data(Qt.UserRole)
        self._remove_item(idx)
        # 移除后，如果当前处于等待状态（stage == 'generating'），自动解除阻塞
        if self.parent.stage == 'generating':
            self.parent.handlers.unblock()

    def _remove_item(self, idx):
        if idx < len(self.modification_history):
            removed = self.modification_history.pop(idx)
            self._update_list()
            self.parent.controls['log_text'].append(f"🗑 已移除: {removed['path']}")
            if not self.modification_history:
                self.parent.controls['btn_apply_all'].setEnabled(False)
                self.parent.controls['btn_undo_all'].setEnabled(False)
                self.parent.controls['btn_apply_selected'].setEnabled(False)
                self.parent.controls['btn_undo_selected'].setEnabled(False)
            else:
                any_applied = any(r['applied'] for r in self.modification_history)
                self.parent.controls['btn_undo_all'].setEnabled(any_applied)

    # ---------- 应用与撤销 ----------
    def _apply(self, idx):
        record = self.modification_history[idx]
        if record['applied']:
            return
        base_dir = self.parent.file_manager.get_current_path()
        full_path = os.path.join(base_dir, record['path'])
        # 替换内容中的 \u005f 为 _
        content = record['content'].replace('\\u005f', '_')
        try:
            dir_path = os.path.dirname(full_path)
            if dir_path and not os.path.exists(dir_path):
                os.makedirs(dir_path)
            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(content)
            record['applied'] = True
            self._update_list()
            self.parent.controls['log_text'].append(f"✅ 已应用: {record['path']}")
            self.parent.controls['btn_undo_all'].setEnabled(True)
            self.parent.file_manager._refresh()
        except Exception as e:
            QMessageBox.critical(self.parent, "错误", f"应用修改失败: {e}")

    def _undo(self, idx):
        record = self.modification_history[idx]
        if not record['applied']:
            return
        full_path = os.path.join(self.parent.file_manager.get_current_path(), record['path'])
        if os.path.exists(full_path):
            try:
                os.remove(full_path)
                dir_path = os.path.dirname(full_path)
                if os.path.exists(dir_path) and not os.listdir(dir_path):
                    os.rmdir(dir_path)
            except Exception as e:
                QMessageBox.warning(self.parent, "警告", f"删除文件失败: {e}")
        record['applied'] = False
        self._update_list()
        self.parent.controls['log_text'].append(f"↩ 已撤销: {record['path']}")
        any_applied = any(r['applied'] for r in self.modification_history)
        self.parent.controls['btn_undo_all'].setEnabled(any_applied)
        self.parent.file_manager._refresh()