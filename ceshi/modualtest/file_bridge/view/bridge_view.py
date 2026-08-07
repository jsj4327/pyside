# -*- coding:utf-8 -*-
import os
from PySide2.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLineEdit, QLabel, QSpinBox, QTextEdit, QGroupBox,
    QTableWidget, QTableWidgetItem, QHeaderView,
    QAbstractItemView, QStyle, QMainWindow, QPlainTextEdit,
    QCheckBox
)
from PySide2.QtCore import Qt, Signal, QTimer
from PySide2.QtGui import QIcon, QFont, QTextCursor

from ..common.utils import validate_port, get_local_ip


class DetailLogWindow(QMainWindow):
    """详细日志窗口 - 非模态，独立显示所有日志数据"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("详细日志 - Bridge")
        self.resize(800, 500)
        self.setWindowFlags(Qt.Window)
        
        # 中央控件
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(4, 4, 4, 4)
        
        # 工具栏
        toolbar = QHBoxLayout()
        
        # 日志数量统计
        self.stats_label = QLabel("总: 0  |  连接: 0  |  断开: 0  |  发送: 0  |  接收: 0  |  错误: 0")
        self.stats_label.setStyleSheet("color:#666;font-size:11px;")
        toolbar.addWidget(self.stats_label)
        
        toolbar.addStretch()
        
        # 自动滚动复选框
        self.auto_scroll_check = QCheckBox("自动滚动")
        self.auto_scroll_check.setChecked(True)
        toolbar.addWidget(self.auto_scroll_check)
        
        # 清空按钮
        btn_clear = QPushButton("清空")
        btn_clear.clicked.connect(self.clear_log)
        toolbar.addWidget(btn_clear)
        
        layout.addLayout(toolbar)
        
        # 日志显示区域（使用 PlainTextEdit 性能更好）
        self.log_display = QPlainTextEdit()
        self.log_display.setReadOnly(True)
        self.log_display.setFont(QFont("Consolas", 10))
        self.log_display.setStyleSheet("""
            QPlainTextEdit {
                background: #1e1e1e;
                color: #d4d4d4;
                border: 1px solid #333;
                border-radius: 3px;
            }
        """)
        layout.addWidget(self.log_display)
        
        # 颜色方案 - 不同日志类型不同颜色
        self.color_scheme = {
            'connect': '#4CAF50',   # 绿色
            'disconnect': '#FF9800', # 橙色
            'send': '#2196F3',      # 蓝色
            'receive': '#9C27B0',   # 紫色
            'error': '#f44336',     # 红色
            'info': '#d4d4d4'       # 默认白色
        }
        
        # 日志统计
        self.stats = {
            'total': 0,
            'connect': 0,
            'disconnect': 0,
            'send': 0,
            'receive': 0,
            'error': 0
        }
    
    def append_log(self, log_type: str, time_str: str, message: str, detail: str = ""):
        """
        添加日志到详细窗口
        log_type: connect, disconnect, send, receive, error, info
        time_str: 时间字符串
        message: 简要消息（显示在普通日志区）
        detail: 详细数据（显示在详细窗口）
        """
        # 更新统计
        self.stats['total'] += 1
        if log_type in self.stats:
            self.stats[log_type] += 1
        self._update_stats()
        
        # 获取颜色
        color = self.color_scheme.get(log_type, '#d4d4d4')
        
        # 构建日志行
        log_line = f'<span style="color:#888888;">[{time_str}]</span>'
        
        # 类型标签
        type_labels = {
            'connect': '🔗 连接',
            'disconnect': '🔌 断开',
            'send': '📤 发送',
            'receive': '📥 接收',
            'error': '❌ 错误',
            'info': 'ℹ️ 信息'
        }
        label = type_labels.get(log_type, 'ℹ️ 信息')
        log_line += f' <span style="color:{color};font-weight:bold;">{label}</span>'
        log_line += f' <span style="color:#d4d4d4;">{message}</span>'
        
        # 如果有详细数据，追加
        if detail:
            log_line += f'\n  <span style="color:#888888;font-size:11px;">└── {detail}</span>'
        
        # 添加到显示（使用 HTML）
        self.log_display.appendHtml(log_line)
        
        # 自动滚动到底部
        if self.auto_scroll_check.isChecked():
            cursor = self.log_display.textCursor()
            cursor.movePosition(QTextCursor.End)
            self.log_display.setTextCursor(cursor)
    
    def clear_log(self):
        """清空日志"""
        self.log_display.clear()
        for key in self.stats:
            self.stats[key] = 0
        self._update_stats()
    
    def _update_stats(self):
        """更新统计信息"""
        self.stats_label.setText(
            f"总: {self.stats['total']}  |  "
            f"连接: {self.stats['connect']}  |  "
            f"断开: {self.stats['disconnect']}  |  "
            f"发送: {self.stats['send']}  |  "
            f"接收: {self.stats['receive']}  |  "
            f"错误: {self.stats['error']}"
        )
    
    def closeEvent(self, event):
        """关闭窗口时隐藏而不是销毁"""
        self.hide()
        event.ignore()


class BridgeCoreView(QWidget):
    """Bridge 核心视图（IP设置、端口设置、连接列表、日志）"""
    
    # 信号
    sig_start = Signal()
    sig_stop = Signal()
    sig_port_changed = Signal(int)
    sig_ip_changed = Signal(str)
    # 详细日志信号
    sig_detail_log = Signal(str, str, str, str)  # log_type, time_str, message, detail
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._detail_window = None
        self._init_ui()
        self._connect_signals()
        self._setup_detail_log()
    
    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(6)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # ---- 服务器设置 ----
        server_group = QGroupBox("服务器设置")
        server_layout = QVBoxLayout(server_group)
        
        # IP 和端口一行
        ip_port_layout = QHBoxLayout()
        ip_port_layout.addWidget(QLabel("IP地址:"))
        
        self.ip_edit = QLineEdit()
        self.ip_edit.setText("127.0.0.1")
        self.ip_edit.setPlaceholderText("0.0.0.0 或 127.0.0.1")
        self.ip_edit.setFixedWidth(150)
        ip_port_layout.addWidget(self.ip_edit)
        
        ip_port_layout.addSpacing(20)
        ip_port_layout.addWidget(QLabel("端口:"))
        
        self.port_spin = QSpinBox()
        self.port_spin.setRange(1024, 65535)
        self.port_spin.setValue(9002)
        self.port_spin.setFixedWidth(80)
        ip_port_layout.addWidget(self.port_spin)
        
        ip_port_layout.addStretch()
        server_layout.addLayout(ip_port_layout)
        
        # ---- 提示 + 操作按钮（同一行） ----
        hint_btn_layout = QHBoxLayout()
        
        # 提示信息
        self.hint_label = QLabel("🔒 仅本地访问 (127.0.0.1)")
        self.hint_label.setStyleSheet("color:#4CAF50;font-size:11px;")
        hint_btn_layout.addWidget(self.hint_label)
        
        hint_btn_layout.addStretch()
        
        # 启动按钮（纯图标）
        self.btn_start = QPushButton()
        self.btn_start.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
        self.btn_start.setToolTip("启动服务")
        self.btn_start.setFixedSize(32, 32)
        self.btn_start.setStyleSheet("background:#4CAF50;border-radius:4px;")
        hint_btn_layout.addWidget(self.btn_start)
        
        # 停止按钮（纯图标）
        self.btn_stop = QPushButton()
        self.btn_stop.setIcon(self.style().standardIcon(QStyle.SP_MediaStop))
        self.btn_stop.setToolTip("停止服务")
        self.btn_stop.setFixedSize(32, 32)
        self.btn_stop.setEnabled(False)
        self.btn_stop.setStyleSheet("background:#f44336;border-radius:4px;")
        hint_btn_layout.addWidget(self.btn_stop)
        
        server_layout.addLayout(hint_btn_layout)
        layout.addWidget(server_group)
        
        # ---- 连接列表 ----
        client_group = QGroupBox("已连接客户端")
        client_layout = QVBoxLayout(client_group)
        
        self.client_table = QTableWidget()
        self.client_table.setColumnCount(4)
        self.client_table.setHorizontalHeaderLabels(["ID", "IP地址", "端口", "连接时间"])
        self.client_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.client_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.client_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.client_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.client_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.client_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        
        client_layout.addWidget(self.client_table)
        layout.addWidget(client_group)
        
        # ---- 日志输出 ----
        log_group = QGroupBox("日志输出")
        log_layout = QVBoxLayout(log_group)
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(120)
        self.log_text.setStyleSheet("font-family:monospace;font-size:11px;background:#f8f8f8;")
        log_layout.addWidget(self.log_text)
        
        # 按钮行：查看详细日志 + 清空日志
        log_btn_layout = QHBoxLayout()
        
        self.btn_view_detail = QPushButton("📋 查看详细日志")
        self.btn_view_detail.setToolTip("打开详细日志窗口")
        self.btn_view_detail.setFixedWidth(120)
        log_btn_layout.addWidget(self.btn_view_detail)
        
        log_btn_layout.addStretch()
        
        self.btn_clear_log = QPushButton("清空日志")
        self.btn_clear_log.setFixedWidth(80)
        log_btn_layout.addWidget(self.btn_clear_log)
        
        log_layout.addLayout(log_btn_layout)
        
        layout.addWidget(log_group)
        
        # 更新 IP 提示
        self.ip_edit.textChanged.connect(self._update_hint)
    
    def _connect_signals(self):
        self.btn_start.clicked.connect(self.sig_start.emit)
        self.btn_stop.clicked.connect(self.sig_stop.emit)
        self.port_spin.valueChanged.connect(self.sig_port_changed.emit)
        self.btn_clear_log.clicked.connect(self.log_text.clear)
        self.btn_view_detail.clicked.connect(self._show_detail_window)
        self.ip_edit.textChanged.connect(self.sig_ip_changed.emit)
    
    def _setup_detail_log(self):
        """设置详细日志"""
        # 连接详细日志信号
        self.sig_detail_log.connect(self._on_detail_log)
    
    def _show_detail_window(self):
        """显示详细日志窗口"""
        if self._detail_window is None:
            self._detail_window = DetailLogWindow(self)
        self._detail_window.show()
        self._detail_window.raise_()
        self._detail_window.activateWindow()
    
    def _on_detail_log(self, log_type: str, time_str: str, message: str, detail: str):
        """接收详细日志信号并添加到详细窗口"""
        if self._detail_window is not None:
            self._detail_window.append_log(log_type, time_str, message, detail)
    
    def _update_hint(self, ip: str):
        """更新提示信息"""
        if ip == "127.0.0.1" or ip == "localhost":
            self.hint_label.setText("🔒 仅本地访问 (127.0.0.1)")
            self.hint_label.setStyleSheet("color:#4CAF50;font-size:11px;")
        elif ip == "0.0.0.0":
            self.hint_label.setText("🌐 允许外部连接 (0.0.0.0)")
            self.hint_label.setStyleSheet("color:#FF9800;font-size:11px;")
        else:
            self.hint_label.setText(f"📡 绑定到: {ip}")
            self.hint_label.setStyleSheet("color:#888;font-size:11px;")
    
    def append_log(self, message: str, log_type: str = "info", detail: str = ""):
        """
        追加日志
        log_type: connect, disconnect, send, receive, error, info
        detail: 详细数据（仅显示在详细日志窗口）
        """
        from datetime import datetime
        time_str = datetime.now().strftime("%H:%M:%S")
        
        # 显示在主日志区（不显示具体数据）
        display_msg = message
        self.log_text.append(f"[{time_str}] {display_msg}")
        self.log_text.verticalScrollBar().setValue(
            self.log_text.verticalScrollBar().maximum()
        )
        
        # 发送到详细日志窗口
        self.sig_detail_log.emit(log_type, time_str, message, detail)
    
    # ---------- 更新方法 ----------
    def update_clients(self, clients: list):
        """更新客户端列表"""
        self.client_table.setRowCount(0)
        for client in clients:
            row = self.client_table.rowCount()
            self.client_table.insertRow(row)
            
            self.client_table.setItem(row, 0, QTableWidgetItem(str(client['id'])))
            self.client_table.setItem(row, 1, QTableWidgetItem(client['ip']))
            self.client_table.setItem(row, 2, QTableWidgetItem(str(client['port'])))
            self.client_table.setItem(row, 3, QTableWidgetItem(client['connected_at']))
    
    def set_port(self, port: int):
        """设置端口号（不触发信号）"""
        self.port_spin.setValue(port)
    
    def get_port(self) -> int:
        """获取当前端口号"""
        return self.port_spin.value()
    
    def set_ip(self, ip: str):
        """设置IP地址（不触发信号）"""
        self.ip_edit.setText(ip)
    
    def get_ip(self) -> str:
        """获取当前IP地址"""
        return self.ip_edit.text().strip()
    
    def set_running_state(self, is_running: bool):
        """设置运行状态"""
        self.btn_start.setEnabled(not is_running)
        self.btn_stop.setEnabled(is_running)
        self.port_spin.setEnabled(not is_running)
        self.ip_edit.setEnabled(not is_running)