# -*- coding:utf-8 -*-
import os
import sys
import traceback
from PySide2.QtCore import QObject, QTimer
from PySide2.QtWidgets import QMessageBox

from ..common.utils import validate_port, get_local_ip


class BridgeController(QObject):
    """Bridge 控制器"""
    
    def __init__(self, model, view, bridge_server_class, parent=None):
        super().__init__(parent)
        self.model = model
        self.view = view
        self.bridge_server_class = bridge_server_class
        self._server = None
        self._reconnect_timer = None
        
        print("[CONTROLLER-DEBUG] BridgeController 初始化开始")
        print(f"[CONTROLLER-DEBUG] bridge_server_class: {bridge_server_class}")
        
        self._connect_signals()
        self._initialize_view()
        
        print("[CONTROLLER-DEBUG] BridgeController 初始化完成")
    
    def _connect_signals(self):
        print("[CONTROLLER-DEBUG] 连接信号...")
        self.view.sig_start.connect(self._on_start)
        self.view.sig_stop.connect(self._on_stop)
        self.view.sig_port_changed.connect(self._on_port_changed)
        self.view.sig_ip_changed.connect(self._on_ip_changed)
        
        self.model.sig_status_changed.connect(self._on_status_changed)
        self.model.sig_clients_updated.connect(self._on_clients_updated)
        self.model.sig_log.connect(self._on_log)
        print("[CONTROLLER-DEBUG] 信号连接完成")
    
    def _initialize_view(self):
        print("[CONTROLLER-DEBUG] 初始化视图...")
        self.view.set_ip(self.model.ip)
        self.view.set_port(self.model.port)
        self.view.update_status("stopped", self.model.port, 0)
        self.view.append_log("🚀 Bridge 组件已加载", "info")
        self.view.append_log(f"📡 IP地址: {self.model.ip}:{self.model.port}", "info")
        self.view.append_log("💡 127.0.0.1 仅本地访问，0.0.0.0 允许外部连接", "info")
        self.view.append_log("⏳ 点击「启动」开始监听", "info")
        print("[CONTROLLER-DEBUG] 视图初始化完成")
    
    # ---------- View 事件 ----------
    def _on_start(self):
        """启动 Bridge 服务"""
        print("[CONTROLLER-DEBUG] ========================================")
        print("[CONTROLLER-DEBUG] _on_start 被调用")
        
        ip = self.view.get_ip()
        port = self.view.get_port()
        print(f"[CONTROLLER-DEBUG] IP: {ip}, 端口: {port}")
        
        if not validate_port(port):
            print(f"[CONTROLLER-DEBUG] 端口无效: {port}")
            self.view.append_log(f"端口 {port} 无效", "error")
            QMessageBox.warning(self.view, "错误", f"端口 {port} 无效")
            return
        
        if not ip or not ip.strip():
            print("[CONTROLLER-DEBUG] IP 为空")
            self.view.append_log("IP 地址为空", "error")
            QMessageBox.warning(self.view, "错误", "请输入有效的 IP 地址")
            return
        
        if self._server and self.model.is_running:
            print("[CONTROLLER-DEBUG] 服务已在运行中")
            self.view.append_log("⚠️ 服务已在运行中", "info")
            return
        
        print(f"[CONTROLLER-DEBUG] bridge_server_class: {self.bridge_server_class}")
        
        try:
            print("[CONTROLLER-DEBUG] 创建 BridgeServer 实例...")
            self._server = self.bridge_server_class(parent=self.view)
            print(f"[CONTROLLER-DEBUG] BridgeServer 实例创建成功: {self._server}")
            
            print(f"[CONTROLLER-DEBUG] 调用 listen({ip.strip()}, {port})...")
            success = self._server.listen(
                host=ip.strip(),
                port=port,
                connection_callback=self._on_client_connected,
                disconnection_callback=self._on_client_disconnected,
                message_callback=self._on_message_received
            )
            
            print(f"[CONTROLLER-DEBUG] listen 返回值: {success}")
            
            if success:
                # 检查服务器是否真的在监听
                is_listening = self._server.is_listening()
                print(f"[CONTROLLER-DEBUG] is_listening(): {is_listening}")
                
                if is_listening:
                    self.model.set_running(True)
                    self.model.set_server_instance(self._server)
                    self.view.set_running_state(True)
                    self.view.update_status("running", port, 0)
                    detail = f"IP: {ip}, 端口: {port}"
                    self.view.append_log(f"✅ 服务已启动，监听: {ip}:{port}", "info", detail)
                    self.view.append_log(f"📡 ws://{ip}:{port}", "info")
                    print("[CONTROLLER-DEBUG] ✅ 服务启动成功")
                else:
                    print("[CONTROLLER-DEBUG] ❌ 服务启动后未能正常监听")
                    self.view.append_log("❌ 服务启动后未能正常监听", "error")
                    self.view.update_status("error", port, 0)
                    self._server = None
            else:
                print("[CONTROLLER-DEBUG] ❌ listen 返回 False")
                self.view.append_log("❌ 服务启动失败，请检查端口是否被占用", "error")
                self.view.update_status("error", port, 0)
                self._server = None
                
        except Exception as e:
            print(f"[CONTROLLER-DEBUG] ❌ 启动异常: {e}")
            print(f"[CONTROLLER-DEBUG] 堆栈: {traceback.format_exc()}")
            self.view.append_log(f"❌ 启动异常: {str(e)}", "error")
            self.view.update_status("error", port, 0)
            QMessageBox.critical(self.view, "错误", f"启动服务失败:\n{str(e)}")
            self._server = None
        
        print("[CONTROLLER-DEBUG] _on_start 执行完成")
        print("[CONTROLLER-DEBUG] ========================================")
    
    def _on_stop(self):
        """停止 Bridge 服务"""
        print("[CONTROLLER-DEBUG] _on_stop 被调用")
        
        if self._server:
            try:
                print("[CONTROLLER-DEBUG] 关闭服务器...")
                self._server.close()
                print("[CONTROLLER-DEBUG] 服务器关闭成功")
            except Exception as e:
                print(f"[CONTROLLER-DEBUG] 关闭异常: {e}")
                self.view.append_log(f"⚠️ 关闭服务异常: {str(e)}", "error")
            
            self._server = None
            self.model.set_running(False)
            self.model.set_server_instance(None)
            self.model.clear_clients()
            
            self.view.set_running_state(False)
            self.view.update_status("stopped", self.model.port, 0)
            self.view.append_log("⏹ 服务已停止", "info")
            print("[CONTROLLER-DEBUG] 服务已停止")
        else:
            print("[CONTROLLER-DEBUG] _server 为 None，无需停止")
    
    def _on_port_changed(self, port: int):
        print(f"[CONTROLLER-DEBUG] _on_port_changed: {port}")
        if self.model.is_running:
            self.view.append_log("⚠️ 服务正在运行，停止后再修改端口", "info")
            self.view.set_port(self.model.port)
            return
        self.model.set_port(port)
        self.view.append_log(f"📡 端口已设置为: {port}", "info")
    
    def _on_ip_changed(self, ip: str):
        print(f"[CONTROLLER-DEBUG] _on_ip_changed: {ip}")
        if self.model.is_running:
            self.view.append_log("⚠️ 服务正在运行，停止后再修改IP", "info")
            self.view.set_ip(self.model.ip)
            return
        self.model.set_ip(ip)
        self.view.append_log(f"📡 IP已设置为: {ip}", "info")
    
    # ---------- Bridge Server 回调 ----------
    def _on_client_connected(self, count: int):
        print(f"[CONTROLLER-DEBUG] _on_client_connected: count={count}")
        client_info = self._get_last_client_info()
        if client_info:
            detail = f"IP: {client_info['ip']}, 端口: {client_info['port']}"
            self.view.append_log(
                f"客户端已连接 (ID: {client_info['id']})", 
                "connect", 
                detail
            )
            self.model.add_client(
                client_info['id'],
                client_info['ip'],
                client_info['port']
            )
        else:
            self.view.append_log("客户端已连接", "connect")
            self.model.add_client(0, "unknown", 0)
        self.view.update_status("running", self.model.port, len(self.model.get_clients()))
    
    def _on_client_disconnected(self, count: int):
        print(f"[CONTROLLER-DEBUG] _on_client_disconnected: count={count}")
        clients = self.model.get_clients()
        if clients:
            last_client = clients[-1]
            detail = f"IP: {last_client.ip}, 端口: {last_client.port}"
            self.view.append_log(
                f"客户端已断开 (ID: {last_client.client_id})", 
                "disconnect", 
                detail
            )
            self.model.remove_client(last_client.client_id)
        else:
            self.view.append_log("客户端已断开", "disconnect")
        self.view.update_status("running", self.model.port, len(self.model.get_clients()))
    
    def _on_message_received(self, data):
        print(f"[CONTROLLER-DEBUG] _on_message_received: {data}")
        detail = f"数据: {data}"
        self.view.append_log("收到消息", "receive", detail)
    
    def _get_last_client_info(self):
        print("[CONTROLLER-DEBUG] _get_last_client_info 被调用")
        if self._server and hasattr(self._server, 'clients'):
            clients = self._server.clients
            print(f"[CONTROLLER-DEBUG] 服务器 clients: {clients}")
            if clients:
                last = clients[-1]
                info = {
                    'id': id(last),
                    'ip': last.peerAddress().toString(),
                    'port': last.peerPort()
                }
                print(f"[CONTROLLER-DEBUG] 客户端信息: {info}")
                return info
        print("[CONTROLLER-DEBUG] 无法获取客户端信息")
        return None
    
    # ---------- Model 事件 ----------
    def _on_status_changed(self, status: str):
        print(f"[CONTROLLER-DEBUG] _on_status_changed: {status}")
        pass
    
    def _on_clients_updated(self, clients: list):
        print(f"[CONTROLLER-DEBUG] _on_clients_updated: {len(clients)} 个客户端")
        self.view.update_clients(clients)
        self.view.update_status(
            "running" if self.model.is_running else "stopped",
            self.model.port,
            len(clients)
        )
    
    def _on_log(self, message: str):
        self.view.append_log(message, "info")