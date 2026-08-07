# -*- coding:utf-8 -*-
from PySide2.QtCore import QObject, Signal
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional


@dataclass
class ExecutionRecord:
    """执行记录"""
    file_path: str
    exit_code: int
    stdout: str
    stderr: str
    duration: float
    timestamp: datetime = field(default_factory=datetime.now)
    
    def has_error(self) -> bool:
        """是否有错误"""
        return self.exit_code != 0 or bool(self.stderr.strip())
    
    def get_summary(self) -> str:
        """获取摘要"""
        status = "❌ 失败" if self.has_error() else "✅ 成功"
        return f"{status} | {self.file_path} | 退出码: {self.exit_code} | 耗时: {self.duration:.2f}s"


class DebugModel(QObject):
    """Debug 数据模型"""
    
    sig_history_changed = Signal()
    sig_current_template_changed = Signal(str)
    sig_current_file_changed = Signal(str)
    
    MAX_HISTORY_COUNT = 50
    
    def __init__(self, parent=None):
        super().__init__(parent)
        print("[DEBUG-MODEL] DebugModel 初始化")
        self._execution_history: List[ExecutionRecord] = []
        self._current_template: str = "debug_default"
        self._current_file: str = ""
        self._is_running: bool = False
    
    @property
    def current_file(self) -> str:
        return self._current_file
    
    def set_current_file(self, file_path: str):
        print(f"[DEBUG-MODEL] 设置当前文件: {file_path}")
        self._current_file = file_path
        self.sig_current_file_changed.emit(file_path)
    
    @property
    def current_template(self) -> str:
        return self._current_template
    
    def set_current_template(self, template_name: str):
        print(f"[DEBUG-MODEL] 设置当前模板: {template_name}")
        self._current_template = template_name
        self.sig_current_template_changed.emit(template_name)
    
    @property
    def is_running(self) -> bool:
        return self._is_running
    
    def set_running(self, running: bool):
        print(f"[DEBUG-MODEL] 设置运行状态: {running}")
        self._is_running = running
    
    def add_history(self, record: ExecutionRecord):
        """添加执行历史"""
        print(f"[DEBUG-MODEL] 添加历史记录: {record.file_path}")
        self._execution_history.insert(0, record)
        
        # 限制数量
        if len(self._execution_history) > self.MAX_HISTORY_COUNT:
            self._execution_history = self._execution_history[:self.MAX_HISTORY_COUNT]
        
        self.sig_history_changed.emit()
    
    def get_history(self) -> List[ExecutionRecord]:
        """获取执行历史"""
        return self._execution_history.copy()
    
    def get_last_record(self) -> Optional[ExecutionRecord]:
        """获取最后一次执行记录"""
        if self._execution_history:
            return self._execution_history[0]
        return None
    
    def clear_history(self):
        """清空历史"""
        print("[DEBUG-MODEL] 清空历史记录")
        self._execution_history.clear()
        self.sig_history_changed.emit()