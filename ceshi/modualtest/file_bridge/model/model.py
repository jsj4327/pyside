# -*- coding:utf-8 -*-
from PySide2.QtCore import QObject, Signal
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional


@dataclass
class ClientInfo:
    """客户端信息数据类"""
    client_id: int
    ip: str
    port: int
    connected_at: datetime
    last_active: datetime
    is_connected: bool = True


class BridgeModel(QObject):
    """Bridge 数据模型"""
    
    # 信号
    sig_status_changed = Signal(str)           # 状态变化 (running/stopped/error)
    sig_port_changed = Signal(int)             # 端口变化
    sig_ip_changed = Signal(str)               # IP 变化
    sig_client_connected = Signal(dict)        # 客户端连接
    sig_client_disconnected = Signal(int)      # 客户端断开 (client_id)
    sig_clients_updated = Signal(list)         # 客户端列表更新
    sig_log = Signal(str)                      # 日志输出
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._is_running = False
        self._ip = "127.0.0.1"
        self._port = 9002
        self._clients: List[ClientInfo] = []
        self._client_id_counter = 0
        self._server_instance = None
    
    @property
    def is_running(self) -> bool:
        return self._is_running
    
    @property
    def ip(self) -> str:
        return self._ip
    
    @property
    def port(self) -> int:
        return self._port
    
    def set_ip(self, ip: str):
        if self._is_running:
            self.sig_log.emit("⚠️ 服务正在运行，无法修改IP")
            return
        self._ip = ip
        self.sig_ip_changed.emit(ip)
        self.sig_log.emit(f"📡 IP已设置为: {ip}")
    
    def set_port(self, port: int):
        if self._is_running:
            self.sig_log.emit("⚠️ 服务正在运行，无法修改端口")
            return
        self._port = port
        self.sig_port_changed.emit(port)
        self.sig_log.emit(f"📡 端口已设置为: {port}")
    
    def set_running(self, running: bool):
        self._is_running = running
        status = "running" if running else "stopped"
        self.sig_status_changed.emit(status)
    
    def set_server_instance(self, server):
        self._server_instance = server
    
    def get_server_instance(self):
        return self._server_instance
    
    def add_client(self, client_id: int, ip: str, port: int):
        now = datetime.now()
        client = ClientInfo(
            client_id=client_id,
            ip=ip,
            port=port,
            connected_at=now,
            last_active=now
        )
        self._clients.append(client)
        self.sig_client_connected.emit({
            'id': client_id,
            'ip': ip,
            'port': port,
            'time': now.strftime("%H:%M:%S")
        })
        self.sig_clients_updated.emit(self.get_clients_summary())
        self.sig_log.emit(f"✅ 客户端已连接: {ip}:{port} (ID: {client_id})")
    
    def remove_client(self, client_id: int):
        for client in self._clients:
            if client.client_id == client_id:
                self._clients.remove(client)
                self.sig_client_disconnected.emit(client_id)
                self.sig_clients_updated.emit(self.get_clients_summary())
                self.sig_log.emit(f"❌ 客户端已断开: {client.ip}:{client.port} (ID: {client_id})")
                return
    
    def get_clients(self) -> List[ClientInfo]:
        return self._clients.copy()
    
    def get_clients_summary(self) -> List[dict]:
        """获取客户端摘要信息（用于显示）"""
        summary = []
        for client in self._clients:
            summary.append({
                'id': client.client_id,
                'ip': client.ip,
                'port': client.port,
                'connected_at': client.connected_at.strftime("%H:%M:%S"),
                'is_connected': client.is_connected
            })
        return summary
    
    def clear_clients(self):
        self._clients.clear()
        self.sig_clients_updated.emit([])