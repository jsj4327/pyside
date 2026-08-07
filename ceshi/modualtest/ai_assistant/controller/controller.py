# -*- coding:utf-8 -*-
import os
import json
from datetime import datetime
from PySide2.QtCore import QObject, QTimer
from PySide2.QtWidgets import QMessageBox, QApplication, QWidget
import traceback

from ..common.utils import build_file_prompt


class AIAssistantController(QObject):
    """AI 助手控制器 - 完全独立，自动查找 Bridge"""
    
    def __init__(self, model, view, parent=None):
        print("[CONTROLLER-INIT] ========== AIAssistantController 初始化开始 ==========")
        super().__init__(parent)
        self.model = model
        self.view = view
        self._bridge_connected = False
        self._last_connection_state = None
        self._connect_signals()
        self._initialize_view()
        
        # 定时检查 Bridge 连接状态
        self._status_timer = QTimer(self)
        self._status_timer.timeout.connect(self._check_bridge_connection)
        self._status_timer.start(2000)
        
        QTimer.singleShot(500, self._check_bridge_connection)
        
        # 加载历史记录
        print("[CONTROLLER-INIT] 开始加载历史记录")
        self._load_history()
        
        # 如果历史为空，添加示例数据
        QTimer.singleShot(100, self._add_sample_history)
        
        # 调试信息
        self._debug_settings()
        
        print("[CONTROLLER-INIT] ========== AIAssistantController 初始化完成 ==========")
    
    def _connect_signals(self):
        print("[CONTROLLER-SIGNAL] 开始连接信号")
        self.view.sig_text_changed.connect(self._on_text_changed)
        self.view.sig_preset_clicked.connect(self._on_preset_clicked)
        self.view.sig_file_option_changed.connect(self._on_file_option_changed)
        self.view.sig_send_clicked.connect(self._on_send_clicked)
        self.view.sig_clear_clicked.connect(self._on_clear_clicked)
        self.view.sig_history_selected.connect(self._on_history_selected)
        self.view.sig_history_cleared.connect(self._on_history_cleared)
        self.model.sig_history_updated.connect(self._on_history_updated)
        self.model.sig_status_changed.connect(self._on_status_changed)
        print("[CONTROLLER-SIGNAL] 所有信号连接完成")
    
    def _initialize_view(self):
        print("[CONTROLLER-INIT] 初始化视图")
        self.view.update_status("idle", "就绪")
        print("[CONTROLLER-INIT] 视图初始化完成")
    
    def _debug_settings(self):
        """调试：显示QSettings信息"""
        from PySide2.QtCore import QSettings
        settings = QSettings("AIAssistant", "History")
        print(f"[SETTINGS-DEBUG] 组织: {settings.organizationName()}")
        print(f"[SETTINGS-DEBUG] 应用: {settings.applicationName()}")
        print(f"[SETTINGS-DEBUG] 文件路径: {settings.fileName()}")
    
    def _add_sample_history(self):
        """添加示例历史记录（仅当历史为空时）"""
        print("[HISTORY-SAMPLE] ========== 检查是否需要添加示例历史 ==========")
        history = self.model.get_history()
        print(f"[HISTORY-SAMPLE] 当前历史记录数: {len(history)}")
        
        if not history:
            print("[HISTORY-SAMPLE] 历史为空，开始添加示例数据")
            samples = [
                "请帮我分析这段代码的性能瓶颈",
                "为这个函数生成单元测试用例",
                "解释一下这个设计模式的应用场景",
                "优化这段SQL查询语句",
                "重构这个类使其符合SOLID原则"
            ]
            for i, sample in enumerate(samples):
                print(f"[HISTORY-SAMPLE] 添加示例 {i+1}: {sample}")
                self.model.add_history(sample)
            
            print("[HISTORY-SAMPLE] 示例历史添加完成，重新加载")
            self._load_history()
        else:
            print("[HISTORY-SAMPLE] 历史记录已存在，跳过添加示例")
    
    def _load_history(self):
        """加载历史记录并更新视图"""
        print("[HISTORY-LOAD] ========== 加载历史记录 ==========")
        history = self.model.get_history()
        print(f"[HISTORY-LOAD] 历史记录条数: {len(history)}")
        if history:
            print(f"[HISTORY-LOAD] 最新记录: {history[0][:50]}...")
            for i, item in enumerate(history[:3]):
                print(f"[HISTORY-LOAD]   {i+1}. {item[:30]}...")
        else:
            print("[HISTORY-LOAD] 历史记录为空")
        
        print("[HISTORY-LOAD] 调用 view.update_history_menu")
        self.view.update_history_menu(history)
        print("[HISTORY-LOAD] 历史记录加载完成")
    
    # ---------- Bridge 查找 ----------
    def _find_bridge_widget(self):
        """自动查找 BridgeWidget 实例"""
        print("[BRIDGE-FIND] 查找 BridgeWidget")
        for widget in QApplication.topLevelWidgets():
            if hasattr(widget, 'bridge'):
                print(f"[BRIDGE-FIND] 找到顶层 widget 的 bridge 属性")
                return getattr(widget, 'bridge')
            for child in widget.findChildren(QWidget):
                class_name = child.__class__.__name__
                if 'Bridge' in class_name and hasattr(child, 'controller'):
                    print(f"[BRIDGE-FIND] 找到 Bridge 子控件: {class_name}")
                    return child
        print("[BRIDGE-FIND] 未找到 BridgeWidget")
        return None
    
    def _get_bridge_server(self):
        """获取 BridgeServer 实例"""
        print("[BRIDGE-SERVER] 获取 BridgeServer")
        bridge_widget = self._find_bridge_widget()
        if bridge_widget and hasattr(bridge_widget, 'controller'):
            controller = bridge_widget.controller
            if hasattr(controller, '_server'):
                print("[BRIDGE-SERVER] 找到 BridgeServer")
                return controller._server
        print("[BRIDGE-SERVER] 未找到 BridgeServer")
        return None
    
    def _get_bridge_view(self):
        """获取 Bridge 的 View（用于显示日志）"""
        bridge_widget = self._find_bridge_widget()
        if bridge_widget and hasattr(bridge_widget, 'view'):
            return bridge_widget.view
        return None
    
    def _log_to_bridge(self, message: str, log_type: str = "info"):
        """将日志发送到 Bridge 的日志显示"""
        self.model.sig_log.emit(message)
        
        bridge_view = self._get_bridge_view()
        if bridge_view:
            try:
                if hasattr(bridge_view, 'append_log'):
                    bridge_view.append_log(f"[AI] {message}", log_type)
                elif hasattr(bridge_view, 'core') and hasattr(bridge_view.core, 'append_log'):
                    bridge_view.core.append_log(f"[AI] {message}", log_type)
            except Exception:
                pass
    
    def _log_to_bridge_detail(self, message: str, log_type: str = "info", detail: str = ""):
        """将详细日志发送到 Bridge 的详细日志窗口"""
        time_str = datetime.now().strftime("%H:%M:%S")
        
        bridge_view = self._get_bridge_view()
        if bridge_view:
            try:
                if hasattr(bridge_view, 'core') and hasattr(bridge_view.core, 'sig_detail_log'):
                    bridge_view.core.sig_detail_log.emit(log_type, time_str, message, detail)
            except Exception:
                pass
    
    def _check_bridge_connection(self):
        """检查 Bridge 连接状态"""
        bridge = self._get_bridge_server()
        
        if bridge and hasattr(bridge, 'clients'):
            client_count = len(bridge.clients)
            connected = client_count > 0
        else:
            client_count = 0
            connected = False
        
        self._bridge_connected = connected
        self.view.set_connection_status(connected)
        
        # 只在状态变化时记录日志
        if connected != self._last_connection_state:
            self._last_connection_state = connected
            if connected:
                self.view.update_status("idle", f"Bridge 已连接 ({client_count} 个客户端)")
                try:
                    bridge_view = self._get_bridge_view()
                    if bridge_view and hasattr(bridge_view, 'append_log'):
                        bridge_view.append_log(f"[AI] Bridge 已连接 ({client_count} 个客户端)", "info")
                except Exception:
                    pass
            else:
                self.view.update_status("idle", "等待 Bridge 连接...")
                try:
                    bridge_view = self._get_bridge_view()
                    if bridge_view and hasattr(bridge_view, 'append_log'):
                        bridge_view.append_log("[AI] Bridge 已断开", "info")
                except Exception:
                    pass
    
    # ---------- View 事件 ----------
    def _on_text_changed(self, text: str):
        print(f"[CONTROLLER-TEXT] 文本变化，长度: {len(text)}")
        self.model.set_text(text)
    
    def _on_preset_clicked(self, index: int):
        print(f"[CONTROLLER-PRESET] 预设点击: {index}")
        preset = self.model.get_preset(index)
        if not preset:
            print(f"[CONTROLLER-PRESET] 预设 {index} 不存在")
            return
        
        current_text = self.view.get_text()
        user_input = current_text if current_text.strip() else "请分析以下内容"
        
        prompt = preset.template.format(
            user_input=user_input,
            files="{files}"
        )
        
        self.view.set_text(prompt)
        self.model.set_preset(index)
        self.view.update_status("idle", f"已应用「{preset.name}」模板")
        self._log_to_bridge(f"应用模板: {preset.name}", "info")
        print(f"[CONTROLLER-PRESET] 已应用模板: {preset.name}")
    
    def _on_file_option_changed(self, option: int):
        print(f"[CONTROLLER-OPTION] 文件选项变化: {option}")
        self.model.set_file_option(option)
        option_names = ["不附加", "附加选中文件", "附加当前文件夹"]
        self.view.update_status("idle", f"文件选项: {option_names[option]}")
        self._log_to_bridge(f"文件选项: {option_names[option]}", "info")
    
    def _find_file_browser(self):
        """查找 FileBrowserWidget 实例"""
        print("[FILEBROWSER-FIND] 查找文件浏览器")
        for widget in QApplication.topLevelWidgets():
            if hasattr(widget, 'browser'):
                print("[FILEBROWSER-FIND] 找到顶层 widget 的 browser 属性")
                return getattr(widget, 'browser')
            for child in widget.findChildren(QWidget):
                class_name = child.__class__.__name__
                if 'FileBrowser' in class_name or 'Browser' in class_name:
                    print(f"[FILEBROWSER-FIND] 找到文件浏览器子控件: {class_name}")
                    return child
        print("[FILEBROWSER-FIND] 未找到文件浏览器")
        return None
    
    def _get_file_content(self):
        """获取文件内容"""
        print("[FILE-CONTENT] 获取文件内容")
        option = self.model.file_option
        print(f"[FILE-CONTENT] 文件选项: {option}")
        
        if option == 0:
            print("[FILE-CONTENT] 不附加文件")
            return ""
        
        file_browser = self._find_file_browser()
        if not file_browser:
            self._log_to_bridge("⚠️ 未找到文件浏览器", "error")
            print("[FILE-CONTENT] 未找到文件浏览器")
            return ""
        
        if option == 1:
            if hasattr(file_browser, 'get_selected_files'):
                files = file_browser.get_selected_files()
                print(f"[FILE-CONTENT] 选中的文件数: {len(files)}")
                if files:
                    base_path = file_browser.get_current_path() if hasattr(file_browser, 'get_current_path') else ""
                    content = build_file_prompt(files, base_path)
                    self._log_to_bridge(f"📎 已附加 {len(files)} 个选中文件", "info")
                    print(f"[FILE-CONTENT] 已附加 {len(files)} 个文件")
                    return content
            self._log_to_bridge("⚠️ 没有选中的文件", "error")
            print("[FILE-CONTENT] 没有选中的文件")
            return ""
        
        elif option == 2:
            if hasattr(file_browser, 'get_current_path'):
                base_path = file_browser.get_current_path()
                print(f"[FILE-CONTENT] 当前路径: {base_path}")
                if base_path:
                    all_files = []
                    for root, dirs, names in os.walk(base_path):
                        dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__']
                        for name in names:
                            if name.endswith(('.py', '.txt', '.md', '.json', '.yaml', '.yml', '.html', '.css', '.js')):
                                all_files.append(os.path.join(root, name))
                    print(f"[FILE-CONTENT] 找到 {len(all_files)} 个文件")
                    if all_files:
                        content = build_file_prompt(all_files, base_path)
                        self._log_to_bridge(f"📁 已附加 {len(all_files)} 个文件夹文件", "info")
                        return content
            self._log_to_bridge("⚠️ 文件夹中没有可附加的文件", "error")
            print("[FILE-CONTENT] 文件夹中没有可附加的文件")
            return ""
        
        return ""
    
    def _on_send_clicked(self):
        """发送请求"""
        print("[CONTROLLER-SEND] ========== 发送按钮点击 ==========")
        text = self.view.get_text()
        print(f"[CONTROLLER-SEND] 文本长度: {len(text)}")
        print(f"[CONTROLLER-SEND] 文本预览: {text[:50]}...")
        
        if not text or not text.strip():
            print("[CONTROLLER-SEND] 文本为空，显示警告")
            QMessageBox.warning(self.view, "提示", "请输入请求内容")
            return
        
        print("[CONTROLLER-SEND] 文本有效，准备发送")
        self._log_to_bridge("📤 准备发送请求...", "info")
        
        self._check_bridge_connection()
        
        if not self._bridge_connected:
            print("[CONTROLLER-SEND] Bridge 未连接")
            self._log_to_bridge("❌ Bridge 未连接", "error")
            QMessageBox.warning(
                self.view, 
                "连接警告", 
                "Bridge 服务未连接，请先启动 Bridge 服务并等待客户端连接"
            )
            return
        
        file_content = self._get_file_content()
        final_prompt = text.replace("{files}", file_content) if file_content else text.replace("{files}", "")
        print(f"[CONTROLLER-SEND] 最终提示长度: {len(final_prompt)}")
        
        self._send_via_bridge(final_prompt)
    
    def _send_via_bridge(self, prompt: str):
        """通过 Bridge 发送请求"""
        print("[CONTROLLER-SEND] ========== 通过 Bridge 发送 ==========")
        self.model.set_sending(True)
        self.view.set_send_enabled(False)
        self.view.update_status("sending", "发送中...")
        
        bridge = self._get_bridge_server()
        
        if not bridge:
            print("[CONTROLLER-SEND] Bridge 服务未启动")
            self._reset_send_state("error", "Bridge 未启动")
            self._log_to_bridge("❌ Bridge 服务未启动", "error")
            QMessageBox.warning(self.view, "错误", "Bridge 服务未启动")
            return
        
        if not hasattr(bridge, 'clients') or len(bridge.clients) == 0:
            print("[CONTROLLER-SEND] 无客户端连接")
            self._reset_send_state("error", "无客户端连接")
            self._log_to_bridge("❌ 无客户端连接", "error")
            QMessageBox.warning(self.view, "警告", "没有客户端连接，请确保 Chrome 插件已连接")
            return
        
        payload = {
            "type": "ANALYZE_REQUEST",
            "filename": "ai_assistant_request",
            "content": prompt,
            "message": "AI 助手请求"
        }
        
        try:
            print("[CONTROLLER-SEND] 发送 payload")
            bridge.send_to_all_clients(payload)
            self._reset_send_state("sent", "发送成功")
            
            # 保存到历史记录
            print("[CONTROLLER-SEND] 保存到历史记录")
            self.model.add_history(prompt)
            
            # 记录完整发送内容到详细日志
            detail = json.dumps(payload, ensure_ascii=False, indent=2)
            self._log_to_bridge_detail("发送请求", "send", detail)
            
            self._log_to_bridge("✅ 请求已发送到 Bridge", "info")
            print("[CONTROLLER-SEND] 发送完成")
        except Exception as e:
            print(f"[CONTROLLER-SEND-ERROR] 发送失败: {e}")
            traceback.print_exc()
            self._reset_send_state("error", f"发送失败: {str(e)}")
            self._log_to_bridge(f"❌ 发送失败: {str(e)}", "error")
            QMessageBox.warning(self.view, "错误", f"发送失败:\n{str(e)}")
    
    def _reset_send_state(self, status: str, msg: str):
        print(f"[CONTROLLER-STATE] 重置发送状态: {status}, {msg}")
        self.model.set_sending(False)
        self.view.set_send_enabled(True)
        self.view.update_status(status, msg)
    
    def _on_clear_clicked(self):
        print("[CONTROLLER-CLEAR] ========== 清空按钮点击 ==========")
        self.view.set_text("")
        self.view.clear_preset_selection()
        self.view.update_status("idle", "已清空")
        self.model.set_text("")
        self._log_to_bridge("已清空输入", "info")
        print("[CONTROLLER-CLEAR] 清空完成")
    
    def _on_status_changed(self, status: str):
        print(f"[CONTROLLER-STATUS] 状态变化: {status}")
        pass
    
    # ---------- 历史记录事件 ----------
    def _on_history_selected(self, text: str):
        """选择历史记录 -> 填充文本框"""
        print("[HISTORY-SELECT] ========== 历史记录被选中 ==========")
        print(f"[HISTORY-SELECT] 文本长度: {len(text)}")
        print(f"[HISTORY-SELECT] 文本预览: {text[:50]}...")
        print("[HISTORY-SELECT] 调用栈:")
        traceback.print_stack()
        
        self.view.set_text(text)
        self.view.update_status("idle", "已加载历史记录")
        self._log_to_bridge(f"加载历史记录 (长度: {len(text)})", "info")
        print("[HISTORY-SELECT] 历史记录加载完成")
    
    def _on_history_cleared(self):
        """清空历史记录"""
        print("[HISTORY-CLEAR] ========== 清空历史记录 ==========")
        self.model.clear_history()
        self.view.update_status("idle", "历史记录已清空")
        self._log_to_bridge("历史记录已清空", "info")
        print("[HISTORY-CLEAR] 历史记录清空完成")
    
    def _on_history_updated(self):
        """历史记录更新 -> 刷新视图"""
        print("[HISTORY-UPDATE] ========== 历史记录更新信号触发 ==========")
        history = self.model.get_history()
        print(f"[HISTORY-UPDATE] 历史记录条数: {len(history)}")
        if history:
            print(f"[HISTORY-UPDATE] 最新记录: {history[0][:50]}...")
        else:
            print("[HISTORY-UPDATE] 历史记录为空")
        
        print("[HISTORY-UPDATE] 调用 view.update_history_menu")
        self.view.update_history_menu(history)
        print("[HISTORY-UPDATE] 视图更新完成")