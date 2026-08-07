# -*- coding:utf-8 -*-
from PySide2.QtCore import QObject, Signal
from PySide2.QtCore import QSettings
from dataclasses import dataclass
from typing import List, Optional
import json
import traceback


@dataclass
class RequestPreset:
    """请求预设"""
    name: str
    template: str
    icon: str = ""


class AIAssistantModel(QObject):
    """AI 助手数据模型"""
    
    # 信号
    sig_text_changed = Signal(str)
    sig_preset_changed = Signal(str)
    sig_file_option_changed = Signal(int)
    sig_request_sent = Signal(dict)
    sig_status_changed = Signal(str)
    sig_log = Signal(str)
    sig_history_updated = Signal()
    
    # 文件选项常量
    OPTION_NONE = 0
    OPTION_SELECTED_FILE = 1
    OPTION_FOLDER_FILES = 2
    
    # 历史记录配置
    MAX_HISTORY_COUNT = 30
    
    def __init__(self, parent=None):
        super().__init__(parent)
        print("[MODEL-INIT] ========== AIAssistantModel 初始化 ==========")
        self._text = ""
        self._current_preset = None
        self._file_option = self.OPTION_NONE
        self._is_sending = False
        
        # 预设列表
        self._presets = [
            RequestPreset(
                name="代码审查",
                template="请对以下代码进行全面的代码审查，指出潜在问题、安全隐患和优化建议：\n\n{user_input}\n\n{files}",
                icon="🔍"
            ),
            RequestPreset(
                name="代码优化",
                template="请优化以下代码，提高代码质量、性能和可读性，并解释修改的原因：\n\n{user_input}\n\n{files}",
                icon="⚡"
            ),
            RequestPreset(
                name="添加注释",
                template="请为以下代码添加详细的中文注释，包括函数说明、参数说明和返回值说明：\n\n{user_input}\n\n{files}",
                icon="📝"
            ),
            RequestPreset(
                name="错误修复",
                template="请分析以下代码中的错误并修复，说明错误原因和修复方案：\n\n{user_input}\n\n{files}",
                icon="🔧"
            ),
            RequestPreset(
                name="功能解释",
                template="请详细解释以下代码的功能、架构和工作原理：\n\n{user_input}\n\n{files}",
                icon="📖"
            ),
            RequestPreset(
                name="生成测试",
                template="请为以下代码生成全面的单元测试用例，覆盖主要功能和边界条件：\n\n{user_input}\n\n{files}",
                icon="🧪"
            ),
        ]
        
        print(f"[MODEL-INIT] 预设数量: {len(self._presets)}")
        print("[MODEL-INIT] AIAssistantModel 初始化完成")
    
    @property
    def text(self) -> str:
        return self._text
    
    def set_text(self, text: str):
        print(f"[MODEL-TEXT] 设置文本，长度: {len(text)}")
        self._text = text
        self.sig_text_changed.emit(text)
    
    @property
    def current_preset(self) -> Optional[RequestPreset]:
        return self._current_preset
    
    def set_preset(self, index: int):
        print(f"[MODEL-PRESET] 设置预设: {index}")
        if 0 <= index < len(self._presets):
            self._current_preset = self._presets[index]
            self.sig_preset_changed.emit(self._current_preset.name)
            print(f"[MODEL-PRESET] 预设已设置: {self._current_preset.name}")
        else:
            print(f"[MODEL-PRESET] 预设索引 {index} 超出范围")
    
    def get_preset(self, index: int) -> Optional[RequestPreset]:
        if 0 <= index < len(self._presets):
            return self._presets[index]
        return None
    
    def get_presets(self) -> List[RequestPreset]:
        return self._presets.copy()
    
    @property
    def file_option(self) -> int:
        return self._file_option
    
    def set_file_option(self, option: int):
        print(f"[MODEL-OPTION] 设置文件选项: {option}")
        self._file_option = option
        self.sig_file_option_changed.emit(option)
    
    @property
    def is_sending(self) -> bool:
        return self._is_sending
    
    def set_sending(self, sending: bool):
        print(f"[MODEL-SENDING] 设置发送状态: {sending}")
        self._is_sending = sending
        status = "sending" if sending else "idle"
        self.sig_status_changed.emit(status)
    
    # ---------- 历史记录管理 ----------
    def get_history(self) -> List[str]:
        """获取历史记录列表"""
        print("[MODEL-GET] ========== get_history 被调用 ==========")
        print("[MODEL-GET] 调用栈:")
        traceback.print_stack()
        
        try:
            settings = QSettings("AIAssistant", "History")
            history = settings.value("history", [])
            
            print(f"[MODEL-GET] 从 QSettings 读取历史记录")
            print(f"[MODEL-GET] 原始类型: {type(history)}")
            print(f"[MODEL-GET] 原始值: {history}")
            
            # 处理各种可能的类型
            if history is None:
                print("[MODEL-GET] 历史记录为 None，返回空列表")
                return []
            if isinstance(history, str):
                print(f"[MODEL-GET] 历史记录是字符串: {history[:50]}...")
                # 如果是字符串，尝试解析JSON
                try:
                    parsed = json.loads(history)
                    if isinstance(parsed, list):
                        print(f"[MODEL-GET] 解析为列表，共 {len(parsed)} 条")
                        return parsed
                except Exception as e:
                    print(f"[MODEL-GET] JSON 解析失败: {e}")
                result = [history] if history else []
                print(f"[MODEL-GET] 返回字符串列表，共 {len(result)} 条")
                return result
            if isinstance(history, list):
                print(f"[MODEL-GET] 历史记录是列表，共 {len(history)} 条")
                if history:
                    print(f"[MODEL-GET] 最新记录: {history[0][:50]}...")
                return history
            
            print(f"[MODEL-GET] 历史记录是其他类型: {type(history)}，返回空列表")
            return []
        except Exception as e:
            print(f"[MODEL-GET-ERROR] 读取历史记录失败: {e}")
            traceback.print_exc()
            return []
    
    def add_history(self, text: str):
        """添加文本到历史记录（去重、限制数量）"""
        print("[MODEL-ADD] ========== add_history 被调用 ==========")
        print(f"[MODEL-ADD] 文本长度: {len(text)}")
        print(f"[MODEL-ADD] 文本预览: {text[:50]}...")
        print("[MODEL-ADD] 调用栈:")
        traceback.print_stack()
        
        if not text or not text.strip():
            print("[MODEL-ADD] 文本为空，不添加到历史")
            return
        
        # 清理文本
        text = text.strip()
        print(f"[MODEL-ADD] 清理后文本长度: {len(text)}")
        
        try:
            settings = QSettings("AIAssistant", "History")
            history = self.get_history()
            
            # 确保是列表
            if not isinstance(history, list):
                print(f"[MODEL-ADD] 历史不是列表类型: {type(history)}，重置为空列表")
                history = []
            
            print(f"[MODEL-ADD] 当前历史记录数: {len(history)}")
            
            # 去重：如果已存在，移除旧记录
            if text in history:
                history.remove(text)
                print("[MODEL-ADD] 移除重复记录")
            
            # 插入到最前面
            history.insert(0, text)
            print(f"[MODEL-ADD] 插入到最前面，当前共 {len(history)} 条")
            
            # 限制数量
            if len(history) > self.MAX_HISTORY_COUNT:
                history = history[:self.MAX_HISTORY_COUNT]
                print(f"[MODEL-ADD] 截断到 {self.MAX_HISTORY_COUNT} 条")
            
            # 保存
            print("[MODEL-ADD] 保存到 QSettings")
            settings.setValue("history", history)
            settings.sync()
            print("[MODEL-ADD] 保存完成，已同步")
            
            # 调试信息
            print(f"[MODEL-ADD] 历史记录共 {len(history)} 条")
            if history:
                print(f"[MODEL-ADD] 最新: {history[0][:50]}...")
            
            # 发射信号
            print("[MODEL-ADD] 发射 sig_history_updated 信号")
            self.sig_history_updated.emit()
            print("[MODEL-ADD] 信号发射完成")
            
        except Exception as e:
            print(f"[MODEL-ADD-ERROR] 保存历史记录失败: {e}")
            traceback.print_exc()
    
    def clear_history(self):
        """清空历史记录"""
        print("[MODEL-CLEAR] ========== clear_history 被调用 ==========")
        print("[MODEL-CLEAR] 调用栈:")
        traceback.print_stack()
        
        try:
            settings = QSettings("AIAssistant", "History")
            settings.remove("history")
            settings.sync()
            print("[MODEL-CLEAR] 历史记录已清空")
            print("[MODEL-CLEAR] 发射 sig_history_updated 信号")
            self.sig_history_updated.emit()
            print("[MODEL-CLEAR] 信号发射完成")
        except Exception as e:
            print(f"[MODEL-CLEAR-ERROR] 清空历史记录失败: {e}")
            traceback.print_exc()