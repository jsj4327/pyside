import sys
import os
import socket
import struct
import zipfile
import threading
import time
import hashlib
import json
from PySide2.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                               QHBoxLayout, QLineEdit, QPushButton, QTextEdit, 
                               QLabel, QFileDialog, QMessageBox, QGroupBox, 
                               QRadioButton, QButtonGroup, QSpinBox, QListWidget, QProgressBar, QGridLayout, QSizePolicy)
from PySide2.QtCore import Qt, Signal, QObject

class EmitLog(QObject):
    log_signal = Signal(str)
    peer_signal = Signal(list)
    progress_signal = Signal(int)

class LanTransferUltimateProApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("局域网文件/文件夹对传工具 (完美优化版)")

        self.init_window_size_and_position(scale=0.8)

        self.logger = EmitLog()
        self.logger.log_signal.connect(self.append_log)
        self.logger.peer_signal.connect(self.update_peer_list)
        self.logger.progress_signal.connect(self.update_progress_bar)

        self.server_socket = None
        self.is_server_running = False
        self.discovered_peers = {}
        self.my_hostname = socket.gethostname()

        self.init_ui()
        
        threading.Thread(target=self.udp_broadcast_sender, daemon=True).start()
        threading.Thread(target=self.udp_broadcast_listener, daemon=True).start()
        threading.Thread(target=self.peer_cleaner_loop, daemon=True).start()

    def init_window_size_and_position(self, scale=0.8):
        screen = QApplication.primaryScreen().availableGeometry()
        width = int(screen.width() * scale)
        height = int(screen.height() * scale)
        x = screen.left() + (screen.width() - width) // 2
        y = screen.top() + (screen.height() - height) // 2
        self.setGeometry(x, y, width, height)

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # 1. 顶部：接收端设置与局域网发现并排布局
        top_layout = QHBoxLayout()

        # 接收端设置组
        server_group = QGroupBox("1. 接收端设置")
        server_layout = QGridLayout(server_group)
        
        self.lbl_local_ip = QLabel(f"<b>本机IP:</b> {self.get_local_ip()}")
        self.spin_port = QSpinBox()
        self.spin_port.setRange(1024, 65535)
        self.spin_port.setValue(8888)
        
        self.btn_toggle_server = QPushButton("启动接收服务")
        self.btn_toggle_server.setStyleSheet("background-color: #204a87; color: white; font-weight: bold;")
        
        self.btn_open_recv_dir = QPushButton("📂 打开接收保存目录")

        server_layout.addWidget(self.lbl_local_ip, 0, 0, 1, 2)
        server_layout.addWidget(QLabel("监听端口:"), 1, 0)
        server_layout.addWidget(self.spin_port, 1, 1)
        server_layout.addWidget(self.btn_toggle_server, 2, 0, 1, 2)
        server_layout.addWidget(self.btn_open_recv_dir, 3, 0, 1, 2)
        server_layout.setRowStretch(4, 1)
        
        top_layout.addWidget(server_group, 1)

        # 局域网在线设备列表组
        peer_group = QGroupBox("🔍 局域网在线设备")
        peer_layout = QVBoxLayout(peer_group)
        
        peer_top_layout = QHBoxLayout()
        peer_top_layout.addWidget(QLabel("点击设备直接选中"))
        self.btn_scan_peers = QPushButton("🔄 手动扫描")
        peer_top_layout.addStretch()
        peer_top_layout.addWidget(self.btn_scan_peers)
        peer_layout.addLayout(peer_top_layout)

        self.list_peers = QListWidget()
        self.list_peers.itemClicked.connect(self.on_peer_clicked)
        peer_layout.addWidget(self.list_peers)
        top_layout.addWidget(peer_group, 1)

        main_layout.addLayout(top_layout)

        # 2. 发送端设置区域
        client_group = QGroupBox("2. 发送端设置")
        client_layout = QVBoxLayout(client_group)

        target_layout = QHBoxLayout()
        self.input_ip = QLineEdit()
        self.input_ip.setPlaceholderText("请输入接收方 IP 或从右侧在线设备中点击选择")
        self.btn_local_test = QPushButton("本机自测")
        self.btn_local_test.setStyleSheet("background-color: #c4a000; color: white; font-weight: bold;")
        
        target_layout.addWidget(QLabel("接收方IP:"))
        target_layout.addWidget(self.input_ip, 1)
        target_layout.addWidget(self.btn_local_test)
        client_layout.addLayout(target_layout)

        # 传输模式移至“本机自测”下方
        mode_layout = QHBoxLayout()
        mode_layout.addWidget(QLabel("传输模式:"))
        self.radio_zip = QRadioButton("压缩传输 (自带 MD5 校验与实时网速)")
        self.radio_direct = QRadioButton("直接传输 (免压缩)")
        self.radio_zip.setChecked(True)
        
        self.mode_group = QButtonGroup(self)
        self.mode_group.addButton(self.radio_zip)
        self.mode_group.addButton(self.radio_direct)

        mode_layout.addWidget(self.radio_zip)
        mode_layout.addWidget(self.radio_direct)
        mode_layout.addStretch()
        client_layout.addLayout(mode_layout)

        path_layout = QHBoxLayout()
        self.input_path = QLineEdit()
        self.input_path.setPlaceholderText("点击右侧按钮选择要发送的文件或文件夹...")
        
        self.btn_select_file = QPushButton("选择文件...")
        self.btn_select_folder = QPushButton("选择文件夹...")
        self.btn_send = QPushButton("开始发送")
        self.btn_send.setStyleSheet("background-color: #4e9a06; color: white; font-weight: bold; padding: 5px 15px;")

        path_layout.addWidget(QLabel("发送内容:"))
        path_layout.addWidget(self.input_path, 1)
        path_layout.addWidget(self.btn_select_file)
        path_layout.addWidget(self.btn_select_folder)
        path_layout.addWidget(self.btn_send)
        client_layout.addLayout(path_layout)

        main_layout.addWidget(client_group)

        # 3. 日志与进度条合并区域
        log_layout = QVBoxLayout()
        log_header = QHBoxLayout()
        log_header.addWidget(QLabel("实时传输日志:"))
        
        self.btn_clear = QPushButton("清屏")
        self.btn_clear.setFixedWidth(70)
        log_header.addWidget(self.btn_clear)

        log_header.addWidget(QLabel("进度:"))
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setFixedHeight(16)
        self.progress_bar.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        log_header.addWidget(self.progress_bar)
        
        log_layout.addLayout(log_header)

        self.text_log = QTextEdit()
        self.text_log.setReadOnly(True)
        self.text_log.setStyleSheet("""
            background-color: #2e3436; 
            color: #eeeeec; 
            font-family: 'Monospace', 'Consolas';
            font-size: 10pt;
        """)
        log_layout.addWidget(self.text_log)
        main_layout.addLayout(log_layout, 1)

        # 绑定事件
        self.btn_toggle_server.clicked.connect(self.toggle_server)
        self.btn_scan_peers.clicked.connect(self.manual_scan_peers)
        self.btn_open_recv_dir.clicked.connect(self.open_receive_directory)
        self.btn_local_test.clicked.connect(self.fill_local_loopback)
        self.btn_select_file.clicked.connect(self.select_single_file)
        self.btn_select_folder.clicked.connect(self.select_target_folder)
        self.btn_send.clicked.connect(self.start_send_thread)
        self.btn_clear.clicked.connect(self.text_log.clear)

    def append_log(self, text):
        self.text_log.append(text)
        self.text_log.verticalScrollBar().setValue(self.text_log.verticalScrollBar().maximum())

    def update_progress_bar(self, val):
        self.progress_bar.setValue(val)

    def get_local_ip(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "127.0.0.1"

    def broadcast_presence(self):
        try:
            udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            udp_sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            data = json.dumps({"hostname": self.my_hostname, "ip": self.get_local_ip()}).encode("utf-8")
            udp_sock.sendto(data, ("<broadcast>", 8890))
            udp_sock.close()
        except:
            pass

    def udp_broadcast_sender(self):
        while True:
            self.broadcast_presence()
            time.sleep(3)

    def manual_scan_peers(self):
        self.broadcast_presence()
        self.logger.log_signal.emit("[扫描] 已向局域网发送探测广播，请稍候...")

    def udp_broadcast_listener(self):
        udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        udp_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            udp_sock.bind(("", 8890))
        except:
            return
        while True:
            try:
                data, addr = udp_sock.recvfrom(1024)
                info = json.loads(data.decode("utf-8"))
                peer_ip = info.get("ip")
                peer_name = info.get("hostname", "Unknown")
                
                if peer_ip and peer_ip != self.get_local_ip():
                    self.discovered_peers[peer_ip] = (peer_name, time.time())
                    peers_list = [f"{name} ({ip})" for ip, (name, _) in self.discovered_peers.items()]
                    self.logger.peer_signal.emit(peers_list)
            except:
                break

    def peer_cleaner_loop(self):
        while True:
            time.sleep(5)
            now = time.time()
            offline_ips = [ip for ip, (_, t) in self.discovered_peers.items() if now - t > 12]
            if offline_ips:
                for ip in offline_ips:
                    del self.discovered_peers[ip]
                peers_list = [f"{name} ({ip})" for ip, (name, _) in self.discovered_peers.items()]
                self.logger.peer_signal.emit(peers_list)

    def update_peer_list(self, peers_list):
        self.list_peers.clear()
        for p in peers_list:
            self.list_peers.addItem(p)

    def on_peer_clicked(self, item):
        text = item.text()
        if "(" in text and ")" in text:
            ip = text.split("(")[-1].strip(")")
            self.input_ip.setText(ip)
            self.logger.log_signal.emit(f"[发现] 已选择目标设备 IP: {ip}")

    def fill_local_loopback(self):
        self.input_ip.setText("127.0.0.1")
        if not self.is_server_running:
            self.toggle_server()
        self.logger.log_signal.emit("[测试提示] 已自动填入 127.0.0.1 并确保服务开启！")

    def open_receive_directory(self):
        save_root = os.path.join(os.getcwd(), "received_files_zip")
        if not os.path.exists(save_root):
            save_root = os.path.join(os.getcwd(), "received_files_direct")
            os.makedirs(save_root, exist_ok=True)
        if sys.platform == "win32":
            os.startfile(save_root)
        elif sys.platform == "darwin":
            os.system(f"open {repr(save_root)}")
        else:
            os.system(f"xdg-open {repr(save_root)}")

    def toggle_server(self):
        port = self.spin_port.value()
        if not self.is_server_running:
            self.is_server_running = True
            self.spin_port.setEnabled(False)
            self.btn_toggle_server.setText("停止接收服务")
            self.btn_toggle_server.setStyleSheet("background-color: #a40000; color: white; font-weight: bold;")
            threading.Thread(target=self.run_server_listener, args=(port,), daemon=True).start()
            self.logger.log_signal.emit(f"[提示] 接收服务已启动，监听端口: {port}")
        else:
            self.stop_server()

    def stop_server(self):
        self.is_server_running = False
        if self.server_socket:
            try:
                self.server_socket.shutdown(socket.SHUT_RDWR)
                self.server_socket.close()
            except:
                try:
                    self.server_socket.close()
                except:
                    pass
            self.server_socket = None
        
        self.spin_port.setEnabled(True)
        self.btn_toggle_server.setText("启动接收服务")
        self.btn_toggle_server.setStyleSheet("background-color: #204a87; color: white; font-weight: bold;")
        self.logger.log_signal.emit(f"[提示] 接收服务已停止，端口已释放。")

    def run_server_listener(self, port):
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            self.server_socket.bind(("0.0.0.0", port))
            self.server_socket.listen(5)
        except Exception as e:
            self.logger.log_signal.emit(f"[错误] 监听失败: {e}")
            self.is_server_running = False
            self.spin_port.setEnabled(True)
            return

        while self.is_server_running:
            try:
                conn, addr = self.server_socket.accept()
                threading.Thread(target=self.handle_receive_client, args=(conn, addr), daemon=True).start()
            except:
                break

    def handle_receive_client(self, conn, addr):
        self.logger.log_signal.emit(f"[连接成功] 收到来自 {addr[0]} 的传输请求...")
        try:
            mode_bytes = conn.recv(1)
            if not mode_bytes:
                conn.close()
                return
            transfer_mode = mode_bytes[0]
        except Exception as e:
            self.logger.log_signal.emit(f"[错误] 读取模式失败: {e}")
            conn.close()
            return

        if transfer_mode == 1:
            save_dir = os.path.join(os.getcwd(), "received_files_zip")
            os.makedirs(save_dir, exist_ok=True)
            zip_path = os.path.join(save_dir, f"temp_{addr[0].replace('.', '_')}.zip")
            try:
                expected_md5 = conn.recv(32).decode("utf-8")
                
                with open(zip_path, "wb") as f:
                    while True:
                        data = conn.recv(1024 * 64)
                        if not data: break
                        f.write(data)
                
                self.logger.log_signal.emit(f"[校验中] 正在校验 MD5 指纹...")
                hasher = hashlib.md5()
                with open(zip_path, "rb") as f:
                    hasher.update(f.read())
                actual_md5 = hasher.hexdigest()

                if expected_md5 and actual_md5 != expected_md5:
                    self.logger.log_signal.emit(f"[错误] MD5 校验失败！\n")
                    conn.close()
                    return
                else:
                    self.logger.log_signal.emit(f"[成功] MD5 校验通过，正在解压/释放...")

                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    extract_path = os.path.join(save_dir, f"content_{addr[0].replace('.', '_')}")
                    os.makedirs(extract_path, exist_ok=True)
                    zip_ref.extractall(extract_path)

                self.logger.log_signal.emit(f"[成功] 内容已保存至:\n{extract_path}\n")
            except Exception as e:
                self.logger.log_signal.emit(f"[错误] 接收异常: {e}\n")
            finally:
                if os.path.exists(zip_path):
                    os.remove(zip_path)
        else:
            save_root = os.path.join(os.getcwd(), "received_files_direct")
            os.makedirs(save_root, exist_ok=True)
            try:
                while True:
                    path_len_bytes = conn.recv(4)
                    if not path_len_bytes: break
                    path_len = struct.unpack("!I", path_len_bytes)[0]
                    rel_path = conn.recv(path_len).decode("utf-8")

                    file_size_bytes = conn.recv(8)
                    file_size = struct.unpack("!Q", file_size_bytes)[0]

                    target_file_path = os.path.join(save_root, rel_path)
                    os.makedirs(os.path.dirname(target_file_path), exist_ok=True)

                    received_bytes = 0
                    with open(target_file_path, "wb") as f:
                        while received_bytes < file_size:
                            chunk_size = min(1024 * 64, file_size - received_bytes)
                            chunk = conn.recv(chunk_size)
                            if not chunk: break
                            f.write(chunk)
                            received_bytes += len(chunk)
                self.logger.log_signal.emit(f"[成功] 免压缩直传接收完毕，保存在: {save_root}\n")
            except Exception as e:
                self.logger.log_signal.emit(f"[错误] 直传中断: {e}\n")
        conn.close()

    def select_single_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "选择要发送的文件", os.getcwd())
        if file_path:
            self.input_path.setText(file_path)

    def select_target_folder(self):
        dir_path = QFileDialog.getExistingDirectory(self, "选择要发送的文件夹", os.getcwd())
        if dir_path:
            self.input_path.setText(dir_path)

    def start_send_thread(self):
        target_ip = self.input_ip.text().strip()
        path = self.input_path.text().strip()
        use_zip = self.radio_zip.isChecked()
        port = self.spin_port.value()

        if not target_ip:
            QMessageBox.warning(self, "警告", "请输入或选择接收方 IP 地址！")
            return
        if not path or not os.path.exists(path):
            QMessageBox.warning(self, "警告", "请先选择一个有效的文件或文件夹！")
            return

        self.btn_send.setEnabled(False)
        self.progress_bar.setValue(0)
        threading.Thread(target=self.send_process, args=(target_ip, port, path, use_zip), daemon=True).start()

    def send_process(self, target_ip, port, path, use_zip):
        try:
            self.logger.log_signal.emit(f"[连接中] 正在连接目标主机 {target_ip}:{port} ...")
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect((target_ip, port))

            is_dir = os.path.isdir(path)

            if use_zip:
                s.sendall(struct.pack("B", 1))
                temp_zip = os.path.join(os.getcwd(), "sending_temp.zip")
                
                if is_dir:
                    self.logger.log_signal.emit(f"[打包中] 正在压缩文件夹: {os.path.basename(path)} ...")
                    with zipfile.ZipFile(temp_zip, 'w', zipfile.ZIP_DEFLATED) as zip_ref:
                        for root, dirs, files in os.walk(path):
                            for file in files:
                                full_path = os.path.join(root, file)
                                relative_path = os.path.relpath(full_path, os.path.dirname(path))
                                zip_ref.write(full_path, relative_path)
                else:
                    self.logger.log_signal.emit(f"[打包中] 正在打包文件: {os.path.basename(path)} ...")
                    with zipfile.ZipFile(temp_zip, 'w', zipfile.ZIP_DEFLATED) as zip_ref:
                        zip_ref.write(path, os.path.basename(path))

                total_size = os.path.getsize(temp_zip)
                
                hasher = hashlib.md5()
                with open(temp_zip, "rb") as f:
                    hasher.update(f.read())
                file_md5 = hasher.hexdigest()

                s.sendall(file_md5.encode("utf-8"))

                sent_size = 0
                start_time = time.time()
                self.logger.log_signal.emit(f"[传输中] 开始发送数据流 (总计: {total_size / 1024 / 1024:.2f} MB)...")
                
                with open(temp_zip, "rb") as f:
                    while True:
                        chunk = f.read(1024 * 64)
                        if not chunk: break
                        s.sendall(chunk)
                        sent_size += len(chunk)
                        
                        percent = int((sent_size / total_size) * 100)
                        self.logger.progress_signal.emit(percent)

                        elapsed = time.time() - start_time
                        if elapsed > 0 and sent_size % (1024 * 512) == 0:
                            speed = sent_size / elapsed
                            speed_str = f"{speed / 1024 / 1024:.2f} MB/s" if speed > 1024*1024 else f"{speed / 1024:.2f} KB/s"
                            self.logger.log_signal.emit(f"   [进度] {percent}% | 网速: {speed_str}")

                s.close()
                if os.path.exists(temp_zip):
                    os.remove(temp_zip)
                self.logger.progress_signal.emit(100)
                self.logger.log_signal.emit(f"[成功] 传输及校验全部完成！\n")

            else:
                s.sendall(struct.pack("B", 0))
                if is_dir:
                    self.logger.log_signal.emit(f"[传输中] 开始免压缩直传文件夹...")
                    all_files = []
                    for root, dirs, files in os.walk(path):
                        for file in files:
                            all_files.append(os.path.join(root, file))
                    
                    total_files = len(all_files)
                    for idx, full_path in enumerate(all_files):
                        rel_path = os.path.relpath(full_path, os.path.dirname(path))
                        path_bytes = rel_path.encode("utf-8")
                        file_size = os.path.getsize(full_path)

                        s.sendall(struct.pack("!I", len(path_bytes)))
                        s.sendall(path_bytes)
                        s.sendall(struct.pack("!Q", file_size))

                        with open(full_path, "rb") as f:
                            while True:
                                chunk = f.read(1024 * 64)
                                if not chunk: break
                                s.sendall(chunk)
                        
                        percent = int(((idx + 1) / total_files) * 100)
                        self.logger.progress_signal.emit(percent)
                else:
                    self.logger.log_signal.emit(f"[传输中] 开始免压缩直传单文件...")
                    file_name = os.path.basename(path)
                    path_bytes = file_name.encode("utf-8")
                    file_size = os.path.getsize(path)

                    s.sendall(struct.pack("!I", len(path_bytes)))
                    s.sendall(path_bytes)
                    s.sendall(struct.pack("!Q", file_size))

                    with open(path, "rb") as f:
                        while True:
                            chunk = f.read(1024 * 64)
                            if not chunk: break
                            s.sendall(chunk)
                    
                    self.logger.progress_signal.emit(100)

                s.close()
                self.logger.log_signal.emit(f"[成功] 直接传输完成！\n")

        except Exception as e:
            self.logger.log_signal.emit(f"[错误] 传输异常: {e}\n")
        finally:
            self.btn_send.setEnabled(True)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = LanTransferUltimateProApp()
    window.show()
    sys.exit(app.exec_())
