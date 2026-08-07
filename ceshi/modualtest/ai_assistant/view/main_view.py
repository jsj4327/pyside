# -*- coding:utf-8 -*-
from PySide2.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
    QLabel, QTextEdit, QCheckBox, QButtonGroup, QGroupBox,
    QMenu, QAction, QStyle, QDesktopWidget, QApplication,
    QMessageBox
)
from PySide2.QtCore import Qt, Signal, QPoint
from PySide2.QtGui import QIcon
import traceback
from functools import partial

from ..core import TemplateManager, TemplateEditorDialog


class AIAssistantView(QWidget):
    """AI 助手主视图 - 所有控件集中在一个面板中"""
    
    # 信号
    sig_text_changed = Signal(str)
    sig_preset_clicked = Signal(int)
    sig_file_option_changed = Signal(int)
    sig_send_clicked = Signal()
    sig_clear_clicked = Signal()
    sig_history_selected = Signal(str)
    sig_history_cleared = Signal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        print("[VIEW-INIT] ========== AIAssistantView 初始化开始 ==========")
        self._history_texts = []
        self._template_manager = TemplateManager(self)
        self._init_ui()
        self._connect_signals()
        self._setup_context_menu()
        print("[VIEW-INIT] ========== AIAssistantView 初始化完成 ==========")
    
    def _init_ui(self):
        print("[VIEW-UI] 开始初始化 UI")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(6)
        
        # ========== 主面板 ==========
        main_group = QGroupBox("🤖 AI 助手")
        main_layout = QVBoxLayout(main_group)
        main_layout.setSpacing(8)
        
        # ---- 1. 文本框 ----
        self.text_edit = QTextEdit()
        self.text_edit.setPlaceholderText(
            "请输入您的 AI 请求...\n\n"
            "💡 提示：在文本框右键可使用快捷模板\n"
            "例如：\n"
            "  - 请帮我重构这段代码\n"
            "  - 解释一下这个函数的作用\n"
            "  - 为我生成单元测试"
        )
        self.text_edit.setMinimumHeight(150)
        self.text_edit.setStyleSheet("""
            QTextEdit {
                border: 1px solid #ddd;
                border-radius: 4px;
                padding: 8px;
                font-size: 13px;
                background: white;
            }
            QTextEdit:focus {
                border-color: #2196F3;
            }
        """)
        main_layout.addWidget(self.text_edit)
        print("[VIEW-UI] 文本框创建完成")
        
        # ---- 2. 文件选项（3个CheckBox） ----
        option_layout = QHBoxLayout()
        option_layout.setSpacing(16)
        
        option_layout.addWidget(QLabel("文件附加:"))
        
        self.radio_none = QCheckBox("不附加")
        self.radio_none.setChecked(True)
        option_layout.addWidget(self.radio_none)
        
        self.radio_selected = QCheckBox("附加选中文件")
        self.radio_selected.setToolTip("从文件浏览器获取选中的文件")
        option_layout.addWidget(self.radio_selected)
        
        self.radio_folder = QCheckBox("附加当前文件夹")
        self.radio_folder.setToolTip("从文件浏览器获取当前文件夹下所有文件")
        option_layout.addWidget(self.radio_folder)
        
        option_layout.addStretch()
        
        # 互斥分组
        self.option_group = QButtonGroup(self)
        self.option_group.addButton(self.radio_none, 0)
        self.option_group.addButton(self.radio_selected, 1)
        self.option_group.addButton(self.radio_folder, 2)
        self.option_group.setExclusive(True)
        
        main_layout.addLayout(option_layout)
        print("[VIEW-UI] 文件选项创建完成")
        
        # ---- 3. 操作按钮行（拆分发送+下拉） ----
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(0)
        
        # 发送按钮（左侧 - 主要功能）
        self.btn_send = QPushButton("📤 发送")
        self.btn_send.setFixedHeight(32)
        self.btn_send.setStyleSheet("""
            QPushButton {
                background: #4CAF50;
                color: white;
                font-weight: bold;
                padding: 6px 16px;
                border-radius: 4px 0 0 4px;
                border: none;
                font-size: 13px;
            }
            QPushButton:hover {
                background: #43A047;
            }
            QPushButton:disabled {
                background: #a5d6a7;
            }
        """)
        btn_layout.addWidget(self.btn_send)
        print("[VIEW-UI] 发送按钮创建完成")
        
        # 下拉按钮（右侧 - 显示历史菜单）
        self.btn_dropdown = QPushButton("▼")
        self.btn_dropdown.setFixedHeight(32)
        self.btn_dropdown.setFixedWidth(32)
        self.btn_dropdown.setToolTip("历史记录")
        self.btn_dropdown.setStyleSheet("""
            QPushButton {
                background: #4CAF50;
                color: white;
                font-weight: bold;
                border: none;
                border-radius: 0 4px 4px 0;
                font-size: 12px;
                padding: 0 4px;
            }
            QPushButton:hover {
                background: #43A047;
            }
            QPushButton:disabled {
                background: #a5d6a7;
            }
        """)
        btn_layout.addWidget(self.btn_dropdown)
        print(f"[VIEW-UI] 下拉按钮创建完成")
        
        # 清空按钮
        self.btn_clear = QPushButton("🗑 清空")
        self.btn_clear.setStyleSheet("""
            QPushButton {
                background: #e0e0e0;
                color: #333;
                padding: 6px 16px;
                border-radius: 4px;
                border: 1px solid #ccc;
                font-size: 13px;
            }
            QPushButton:hover {
                background: #d5d5d5;
            }
        """)
        self.btn_clear.setFixedHeight(32)
        btn_layout.addWidget(self.btn_clear)
        
        btn_layout.addStretch()
        
        # 连接状态显示
        self.status_indicator = QLabel("⚪ 未连接")
        self.status_indicator.setStyleSheet("color:#888;font-size:11px;padding:0 8px;")
        btn_layout.addWidget(self.status_indicator)
        
        main_layout.addLayout(btn_layout)
        print("[VIEW-UI] 操作按钮创建完成")
        
        # ---- 4. 状态栏 ----
        self.status_label = QLabel("就绪")
        self.status_label.setStyleSheet("color:#666;font-size:11px;padding:2px 4px;")
        main_layout.addWidget(self.status_label)
        
        layout.addWidget(main_group)
        print("[VIEW-UI] 状态栏创建完成")
        
        # ---- 5. 历史菜单 ----
        print("[VIEW-MENU] 开始创建历史菜单")
        self.history_menu = QMenu(self)
        self.history_menu.setStyleSheet("""
            QMenu {
                background: white;
                border: 1px solid #ddd;
                border-radius: 4px;
                padding: 4px 0;
                min-width: 200px;
                max-width: 400px;
            }
            QMenu::item {
                padding: 6px 20px 6px 10px;
                border: none;
            }
            QMenu::item:selected {
                background: #e3f2fd;
            }
            QMenu::separator {
                height: 1px;
                background: #ddd;
                margin: 4px 8px;
            }
        """)
        print(f"[VIEW-MENU] 历史菜单创建完成，地址: {id(self.history_menu)}")
        
        # 连接菜单显示信号
        self.history_menu.aboutToShow.connect(self._on_history_menu_about_to_show)
        print("[VIEW-MENU] aboutToShow 信号已连接")
        
        print("[VIEW-UI] UI 初始化完成")
    
    def _connect_signals(self):
        print("[VIEW-SIGNAL] 开始连接信号")
        
        # 文本框变化
        self.text_edit.textChanged.connect(
            lambda: self.sig_text_changed.emit(self.text_edit.toPlainText())
        )
        print("[VIEW-SIGNAL] 文本框信号已连接")
        
        # 文件选项变化
        self.radio_none.toggled.connect(lambda: self._on_option_changed(0))
        self.radio_selected.toggled.connect(lambda: self._on_option_changed(1))
        self.radio_folder.toggled.connect(lambda: self._on_option_changed(2))
        print("[VIEW-SIGNAL] 文件选项信号已连接")
        
        # 发送按钮点击 → 发送
        self.btn_send.clicked.connect(self._on_send_clicked)
        print("[VIEW-SIGNAL] 发送按钮信号已连接")
        
        # 下拉按钮点击 → 显示历史菜单
        self.btn_dropdown.clicked.connect(self._show_history_menu)
        print(f"[VIEW-SIGNAL] 下拉按钮点击信号已连接到 _show_history_menu")
        
        # 清空按钮
        self.btn_clear.clicked.connect(self.sig_clear_clicked.emit)
        print("[VIEW-SIGNAL] 清空按钮信号已连接")
        
        print("[VIEW-SIGNAL] 所有信号连接完成")
    
    def _setup_context_menu(self):
        """设置右键菜单"""
        print("[VIEW-MENU] 设置右键菜单")
        self.text_edit.setContextMenuPolicy(Qt.CustomContextMenu)
        self.text_edit.customContextMenuRequested.connect(self._show_context_menu)
        print("[VIEW-MENU] 右键菜单设置完成")
    
    def _show_context_menu(self, pos: QPoint):
        """显示右键菜单"""
        print("[VIEW-CONTEXT] ========== 显示右键菜单 ==========")
        
        menu = QMenu(self)
        
        # ---- 构建项目架构（子菜单） ----
        build_menu = menu.addMenu("🏗️ 构建项目架构")
        
        # 从模板管理器加载架构模板
        system_templates = self._template_manager.get_system_templates()
        custom_templates = self._template_manager.get_custom_templates()
        
        # 系统模板 - 架构类
        arch_templates = ["architecture_web", "architecture_mobile", "architecture_desktop", "architecture_default"]
        has_arch_templates = False
        
        for name in arch_templates:
            if name in system_templates:
                display_name = self._template_manager.get_template_display_name(name)
                action = QAction(f"📦 {display_name}", self)
                action.triggered.connect(partial(self._on_build_with_template, name))
                build_menu.addAction(action)
                has_arch_templates = True
        
        # 自定义模板
        if custom_templates:
            if has_arch_templates:
                build_menu.addSeparator()
            for name in custom_templates:
                display_name = self._template_manager.get_template_display_name(name)
                action = QAction(f"✏️ {display_name}", self)
                action.triggered.connect(partial(self._on_build_with_template, name))
                build_menu.addAction(action)
        
        # ---- 改进项目功能 ----
        improve_action = QAction("🚀 改进项目功能", self)
        improve_action.setToolTip("自动生成项目改进请求")
        improve_action.triggered.connect(self._on_improve_project)
        menu.addAction(improve_action)
        
        menu.addSeparator()
        
        # ---- 编辑模板 ----
        edit_action = QAction("📝 编辑模板", self)
        edit_action.setToolTip("编辑所有模板文件")
        edit_action.triggered.connect(self._on_edit_templates)
        menu.addAction(edit_action)
        
        menu.addSeparator()
        
        # ---- 清空 ----
        clear_action = QAction("🗑️ 清空输入", self)
        clear_action.triggered.connect(self.sig_clear_clicked.emit)
        menu.addAction(clear_action)
        
        # 显示菜单
        global_pos = self.text_edit.mapToGlobal(pos)
        menu.exec_(global_pos)
        print("[VIEW-CONTEXT] 右键菜单显示完成")
    
    def _on_build_with_template(self, template_name: str):
        """使用指定模板构建请求"""
        print(f"[VIEW-CONTEXT] 使用模板: {template_name}")
        
        # 获取模板内容
        template = self._template_manager.get_template(template_name)
        if not template:
            QMessageBox.warning(self, "错误", f"模板 '{template_name}' 不存在")
            return
        
        # 获取上下文信息
        context_info = self._get_context_info()
        
        # 填充模板
        try:
            filled_template = template.format(context=context_info)
        except KeyError as e:
            # 如果模板中缺少 {context} 占位符
            print(f"[VIEW-CONTEXT] 模板格式错误: {e}")
            filled_template = template + f"\n\n【项目背景】\n{context_info}"
        except Exception as e:
            print(f"[VIEW-CONTEXT] 模板填充失败: {e}")
            filled_template = template + f"\n\n【项目背景】\n{context_info}"
        
        self.set_text(filled_template)
        display_name = self._template_manager.get_template_display_name(template_name)
        self.update_status("idle", f"已生成 {display_name} 请求")
        print("[VIEW-CONTEXT] 模板填充完成")
    
    def _on_improve_project(self):
        """改进项目功能"""
        print("[VIEW-CONTEXT] ========== 改进项目功能 ==========")
        
        # 使用 improve_project 模板
        template = self._template_manager.get_template("improve_project")
        if not template:
            QMessageBox.warning(self, "错误", "项目改进模板不存在")
            return
        
        context_info = self._get_context_info()
        
        try:
            filled_template = template.format(context=context_info)
        except KeyError as e:
            filled_template = template + f"\n\n【当前状况】\n{context_info}"
        except Exception as e:
            filled_template = template + f"\n\n【当前状况】\n{context_info}"
        
        self.set_text(filled_template)
        self.update_status("idle", "已生成项目改进请求")
        print("[VIEW-CONTEXT] 项目改进请求已生成")
    
    def _on_edit_templates(self):
        """编辑模板"""
        print("[VIEW-CONTEXT] 打开模板编辑器")
        editor = TemplateEditorDialog(self._template_manager, self)
        editor.sig_template_updated.connect(self._on_templates_updated)
        editor.exec_()
    
    def _on_templates_updated(self):
        """模板更新后的回调"""
        print("[VIEW-CONTEXT] 模板已更新")
        # 可以在这里添加刷新逻辑
    
    def _get_context_info(self) -> str:
        """获取上下文信息"""
        print("[VIEW-CONTEXT] 获取上下文信息")
        
        info = []
        
        # 1. 获取当前文件选择
        file_browser = self._find_file_browser()
        if file_browser:
            if hasattr(file_browser, 'get_current_path'):
                current_path = file_browser.get_current_path()
                if current_path:
                    info.append(f"当前项目路径: {current_path}")
            
            if hasattr(file_browser, 'get_selected_files'):
                selected_files = file_browser.get_selected_files()
                if selected_files:
                    info.append(f"选中文件 ({len(selected_files)} 个):")
                    for f in selected_files[:5]:
                        info.append(f"  - {f}")
                    if len(selected_files) > 5:
                        info.append(f"  ... 等 {len(selected_files)} 个文件")
        
        # 2. 获取当前输入的文本
        current_text = self.get_text()
        if current_text and current_text.strip():
            preview = current_text[:200] + "..." if len(current_text) > 200 else current_text
            info.append(f"\n当前输入参考:\n{preview}")
        
        return "\n".join(info) if info else "（请提供更多项目信息）"
    
    def _find_file_browser(self):
        """查找文件浏览器"""
        for widget in QApplication.topLevelWidgets():
            if hasattr(widget, 'browser'):
                return getattr(widget, 'browser')
            for child in widget.findChildren(QWidget):
                class_name = child.__class__.__name__
                if 'FileBrowser' in class_name or 'Browser' in class_name:
                    return child
        return None
    
    def _on_option_changed(self, option: int):
        print(f"[VIEW-OPTION] 文件选项变化: {option}")
        if self.get_file_option() == option:
            self.sig_file_option_changed.emit(option)
    
    def _on_send_clicked(self):
        """发送按钮点击"""
        print("[VIEW-SEND] ========== 发送按钮点击 ==========")
        print(f"[VIEW-SEND] 当前文本长度: {len(self.get_text())}")
        self.sig_send_clicked.emit()
        print("[VIEW-SEND] 发送信号已发射")
    
    def _show_history_menu(self):
        """在按钮下方显示历史菜单"""
        print("[VIEW-MENU] ========== 下拉按钮点击，显示历史菜单 ==========")
        print(f"[VIEW-MENU] 当前历史数据: {len(self._history_texts)} 条")
        
        try:
            # 在显示菜单前更新菜单内容
            print("[VIEW-MENU] 调用 _on_history_menu_about_to_show 更新菜单")
            self._on_history_menu_about_to_show()
            print("[VIEW-MENU] 菜单更新完成")
            
            # 计算显示位置（在按钮正下方）
            pos = self.btn_dropdown.mapToGlobal(
                self.btn_dropdown.rect().bottomLeft()
            )
            print(f"[VIEW-MENU] 菜单显示位置: ({pos.x()}, {pos.y()})")
            
            # 确保菜单位置不超出屏幕底部
            menu_height = self.history_menu.sizeHint().height()
            print(f"[VIEW-MENU] 菜单高度: {menu_height}")
            
            desktop = QDesktopWidget()
            screen_height = desktop.screenGeometry().height()
            print(f"[VIEW-MENU] 屏幕高度: {screen_height}")
            
            if pos.y() + menu_height > screen_height:
                pos = self.btn_dropdown.mapToGlobal(
                    self.btn_dropdown.rect().topLeft()
                )
                pos.setY(pos.y() - menu_height)
                print(f"[VIEW-MENU] 调整菜单位置到上方: ({pos.x()}, {pos.y()})")
            
            # 显示菜单
            print("[VIEW-MENU] 开始执行 menu.exec_()")
            result = self.history_menu.exec_(pos)
            print(f"[VIEW-MENU] 菜单执行完成，返回值: {result}")
            
        except Exception as e:
            print(f"[VIEW-MENU-ERROR] 显示菜单时发生异常:")
            print(f"[VIEW-MENU-ERROR] 异常类型: {type(e)}")
            print(f"[VIEW-MENU-ERROR] 异常信息: {str(e)}")
            traceback.print_exc()
    
    def _on_history_menu_about_to_show(self):
        """历史菜单弹出前更新"""
        print("[VIEW-MENU] ========== aboutToShow 触发 ==========")
        print(f"[VIEW-MENU] 当前历史数据条数: {len(self._history_texts)}")
        
        try:
            self.history_menu.clear()
            print("[VIEW-MENU] 菜单已清空")
            
            history = self._history_texts
            
            if not history:
                print("[VIEW-MENU] 历史为空，添加空状态项")
                empty_action = QAction("📭 暂无历史记录", self)
                empty_action.setEnabled(False)
                self.history_menu.addAction(empty_action)
                return
            
            count = min(10, len(history))
            print(f"[VIEW-MENU] 准备添加 {count} 条历史记录")
            
            for i in range(count):
                text = history[i]
                display = text[:60] + "..." if len(text) > 60 else text
                display = display.replace('\n', ' ').replace('\r', '').strip()
                if not display:
                    display = f"[空记录 {i+1}]"
                
                action = QAction(display, self)
                action.setIcon(self.style().standardIcon(QStyle.SP_FileIcon))
                action.triggered.connect(partial(self._on_history_item_clicked, i))
                self.history_menu.addAction(action)
                print(f"[VIEW-MENU] 添加历史项 {i+1}: {display[:30]}...")
            
            self.history_menu.addSeparator()
            
            clear_action = QAction("🗑 清空历史记录", self)
            clear_action.setIcon(self.style().standardIcon(QStyle.SP_TrashIcon))
            clear_action.triggered.connect(self.sig_history_cleared.emit)
            self.history_menu.addAction(clear_action)
            
            print("[VIEW-MENU] 历史菜单更新完成")
            
        except Exception as e:
            print(f"[VIEW-MENU-ERROR] 更新菜单时发生异常:")
            print(f"[VIEW-MENU-ERROR] 异常类型: {type(e)}")
            print(f"[VIEW-MENU-ERROR] 异常信息: {str(e)}")
            traceback.print_exc()
    
    def _on_history_item_clicked(self, index: int):
        """处理历史项点击"""
        print("[VIEW-MENU] ========== 历史项点击 ==========")
        print(f"[VIEW-MENU] 点击索引: {index}")
        
        try:
            if 0 <= index < len(self._history_texts):
                text = self._history_texts[index]
                print(f"[VIEW-MENU] 选中的历史文本: {text[:50]}...")
                self.sig_history_selected.emit(text)
                print("[VIEW-MENU] 信号发射完成")
            else:
                print(f"[VIEW-MENU-ERROR] 索引 {index} 超出范围")
        except Exception as e:
            print(f"[VIEW-MENU-ERROR] 处理历史项点击时发生异常:")
            print(f"[VIEW-MENU-ERROR] 异常类型: {type(e)}")
            print(f"[VIEW-MENU-ERROR] 异常信息: {str(e)}")
            traceback.print_exc()
    
    # ---------- 公开方法 ----------
    def get_text(self) -> str:
        return self.text_edit.toPlainText()
    
    def set_text(self, text: str):
        print(f"[VIEW-SETTEXT] 设置文本，长度: {len(text)}")
        print(f"[VIEW-SETTEXT] 文本预览: {text[:50]}...")
        self.text_edit.setPlainText(text)
        print("[VIEW-SETTEXT] 文本设置完成")
    
    def get_file_option(self) -> int:
        return self.option_group.checkedId() if self.option_group.checkedId() != -1 else 0
    
    def set_file_option(self, option: int):
        if option == 0:
            self.radio_none.setChecked(True)
        elif option == 1:
            self.radio_selected.setChecked(True)
        elif option == 2:
            self.radio_folder.setChecked(True)
    
    def clear_preset_selection(self):
        """清除预设选中状态（预设按钮已删除，此方法保留为空）"""
        pass
    
    def set_preset_selection(self, index: int):
        """设置预设选中（预设按钮已删除，此方法保留为空）"""
        pass
    
    def update_status(self, status: str, info: str = ""):
        print(f"[VIEW-STATUS] 更新状态: {status}, {info}")
        if status == "sending":
            self.status_label.setText("📤 发送中...")
            self.status_label.setStyleSheet("color:#FF9800;font-size:11px;font-weight:bold;")
        elif status == "sent":
            self.status_label.setText("✅ 已发送")
            self.status_label.setStyleSheet("color:#4CAF50;font-size:11px;font-weight:bold;")
        elif status == "error":
            self.status_label.setText("❌ 发送失败")
            self.status_label.setStyleSheet("color:#f44336;font-size:11px;font-weight:bold;")
        else:
            self.status_label.setText(info if info else "就绪")
            self.status_label.setStyleSheet("color:#666;font-size:11px;")
    
    def set_send_enabled(self, enabled: bool):
        print(f"[VIEW-BUTTON] 设置发送按钮启用状态: {enabled}")
        self.btn_send.setEnabled(enabled)
        self.btn_dropdown.setEnabled(enabled)
    
    def set_connection_status(self, connected: bool):
        if connected:
            self.status_indicator.setText("🟢 已连接")
            self.status_indicator.setStyleSheet("color:#4CAF50;font-size:11px;padding:0 8px;")
        else:
            self.status_indicator.setText("🔴 未连接")
            self.status_indicator.setStyleSheet("color:#f44336;font-size:11px;padding:0 8px;")
    
    def update_history_menu(self, history: list):
        """更新历史记录数据"""
        print("[VIEW-HISTORY] ========== update_history_menu 被调用 ==========")
        print(f"[VIEW-HISTORY] 历史数据条数: {len(history)}")
        
        self._history_texts = history
        if history:
            print(f"[VIEW-HISTORY] 最新记录: {history[0][:50]}...")
        else:
            print("[VIEW-HISTORY] 历史记录为空")
        
        print("[VIEW-HISTORY] 历史数据已更新")