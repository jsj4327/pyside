import sys
import os
import time
import traceback
import warnings
from PySide2.QtWidgets import *
from PySide2.QtCore import *
from PySide2.QtGui import *
import yt_dlp

warnings.filterwarnings("ignore", category=DeprecationWarning)

# 奇安信可信浏览器基于 Chromium，指定引擎类型与个人资料路径
# 如果不需要 Cookie 验证，可直接设为 COOKIES_CONFIG = None
COOKIES_CONFIG = ('chromium', '/home/user/.config/qaxbrowser')


class OutputRedirect(QObject):
    """将标准输出重定向到界面日志框"""
    output_signal = Signal(str)

    def __init__(self):
        super().__init__()

    def write(self, text):
        if text and text.strip():
            self.output_signal.emit(text)

    def flush(self):
        pass


class DownloadWorker(QThread):
    """下载线程，防止UI卡顿"""
    progress_updated = Signal(int, str)  # 进度百分比, 状态信息
    download_finished = Signal(str)      # 下载完成信号
    download_error = Signal(str)         # 错误信号
    output_signal = Signal(str)          # 输出信息

    def __init__(self, url, format_id, output_path):
        super().__init__()
        self.url = url
        self.format_id = format_id
        self.output_path = output_path
        self._is_cancelled = False
        self._last_update_time = 0  # 限制 UI 刷新频率

    def cancel(self):
        self._is_cancelled = True

    def progress_hook(self, d):
        """yt-dlp 进度钩子"""
        if self._is_cancelled:
            raise Exception("下载已由用户取消")

        current_time = time.time()
        # 限制 UI 刷新频率（每 0.1s 最多一次），防止高频刷新造成 UI 卡死
        if d['status'] == 'downloading':
            if current_time - self._last_update_time < 0.1:
                return
            self._last_update_time = current_time

            total = d.get('total_bytes') or d.get('total_bytes_estimate') or 0
            downloaded = d.get('downloaded_bytes', 0)

            if total > 0:
                percent = int(downloaded / total * 100)
                downloaded_str = self.format_size(downloaded)
                total_str = self.format_size(total)
                speed = d.get('speed', 0)
                speed_str = self.format_size(speed) + '/s' if speed else 'N/A'
                eta = d.get('eta', 0)
                eta_str = self.format_time(eta) if eta else 'N/A'

                msg = f"⬇ 下载中: {percent}% | {downloaded_str}/{total_str} | 速度: {speed_str} | 剩余: {eta_str}"
                self.output_signal.emit(msg)
                self.progress_updated.emit(percent, f"下载中... {percent}%")

        elif d['status'] == 'finished':
            self.output_signal.emit("✅ 下载完成，正在写入文件...")
            self.progress_updated.emit(100, "处理中...")

    @staticmethod
    def format_size(bytes_val):
        if not bytes_val:
            return "0 B"
        for unit in ['B', 'KB', 'MB', 'GB']:
            if bytes_val < 1024.0:
                return f"{bytes_val:.1f} {unit}"
            bytes_val /= 1024.0
        return f"{bytes_val:.1f} TB"

    @staticmethod
    def format_time(seconds):
        if not seconds:
            return "0s"
        seconds = int(seconds)
        if seconds < 60:
            return f"{seconds}s"
        elif seconds < 3600:
            return f"{seconds // 60}m {seconds % 60}s"
        else:
            return f"{seconds // 3600}h {(seconds % 3600) // 60}m"

    def run(self):
        try:
            self.output_signal.emit("=" * 60)
            self.output_signal.emit("🎵 开始下载音频...")
            self.output_signal.emit(f"📁 保存路径: {self.output_path}")

            ydl_opts = {
                'format': self.format_id,
                'outtmpl': os.path.join(self.output_path, '%(title)s.%(ext)s'),
                'progress_hooks': [self.progress_hook],
                'noplaylist': True,        # 禁用列表下载
                'quiet': True,             # 避免原生字符污染
                'no_warnings': True,
                'ignoreerrors': False,
                'socket_timeout': 15,      # 超时设置
                'retries': 5,              # 自动重试次数
            }

            # 挂载奇安信可信浏览器 Cookie 凭证
            if COOKIES_CONFIG:
                try:
                    ydl_opts['cookiesfrombrowser'] = COOKIES_CONFIG
                except Exception as c_err:
                    ydl_opts.pop('cookiesfrombrowser', None)
                    self.output_signal.emit(f"⚠️ 挂载 Cookie 失败，使用无 Cookie 模式下载: {c_err}")

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([self.url])

            if not self._is_cancelled:
                self.output_signal.emit("✅ 音频下载完成！")
                self.download_finished.emit("下载完成！")

        except Exception as e:
            if self._is_cancelled:
                self.output_signal.emit("⏹ 已取消下载操作")
            else:
                tb_str = traceback.format_exc()
                error_msg = f"❌ 下载报错信息:\n{tb_str}"
                self.output_signal.emit(error_msg)
                self.download_error.emit(str(e))


class AudioFormatFetcher(QThread):
    """解析 YouTube 链接格式线程"""
    formats_ready = Signal(list, str)
    fetch_error = Signal(str)
    output_signal = Signal(str)

    def __init__(self, url):
        super().__init__()
        self.url = url

    def run(self):
        try:
            self.output_signal.emit("=" * 60)
            self.output_signal.emit("🔍 开始解析 YouTube 链接...")
            self.output_signal.emit(f"📎 链接: {self.url}")

            ydl_opts = {
                'noplaylist': True,       # 仅解析单个视频，禁止提取完整 Playlist
                'quiet': True,
                'no_warnings': True,
                'ignoreerrors': False,
                'socket_timeout': 15,     # 网络请求超时设置 (秒)
                'retries': 3,             # 失败重试次数
            }

            # 安全挂载奇安信可信浏览器 Cookie 凭证
            if COOKIES_CONFIG:
                try:
                    test_opts = {'cookiesfrombrowser': COOKIES_CONFIG, 'quiet': True}
                    with yt_dlp.YoutubeDL(test_opts) as test_ydl:
                        _ = test_ydl.cookiejar
                    ydl_opts['cookiesfrombrowser'] = COOKIES_CONFIG
                    self.output_signal.emit(f"🍪 已挂载奇安信浏览器 Cookie 凭证: {COOKIES_CONFIG[1]}")
                except Exception as c_err:
                    # 读取 Cookie 失败时，彻底移除配置项，防止抛出 DownloadError 终止任务
                    ydl_opts.pop('cookiesfrombrowser', None)
                    self.output_signal.emit(f"⚠️ 未检测到有效 Cookie 数据库，自动降级为无 Cookie 模式")

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                self.output_signal.emit("⏳ 正在请求 API 并提取视频信息...")
                info = ydl.extract_info(self.url, download=False)

                if not info:
                    raise Exception("yt-dlp 返回数据为空，未能成功提取元数据。")

                video_title = info.get('title', '未知标题')
                video_duration = info.get('duration', 0)
                video_views = info.get('view_count', 0)
                uploader = info.get('uploader', '未知')

                duration_str = f"{video_duration // 60}:{video_duration % 60:02d}" if video_duration else '未知'

                self.output_signal.emit("📊 视频信息:")
                self.output_signal.emit(f"   • 标题: {video_title}")
                self.output_signal.emit(f"   • 时长: {duration_str}")
                self.output_signal.emit(f"   • 播放量: {video_views:,}")
                self.output_signal.emit(f"   • 上传者: {uploader}")

                formats = info.get('formats', [])
                self.output_signal.emit(f"🔎 找到 {len(formats)} 个总格式，筛选纯音频中...")

                audio_formats = []
                audio_count = 0
                for f in formats:
                    # 仅筛选纯音频格式 (无视频，有音频)
                    if f.get('vcodec') == 'none' and f.get('acodec') != 'none':
                        format_id = f.get('format_id')
                        ext = f.get('ext')
                        abr = f.get('abr')
                        format_note = f.get('format_note', '')
                        acodec = f.get('acodec', 'unknown')
                        filesize = f.get('filesize') or f.get('filesize_approx') or 0
                        filesize_str = f"{filesize / 1024 / 1024:.1f} MB" if filesize else '未知'

                        bitrate_str = f"{int(abr)} kbps" if abr else 'N/A'
                        display_text = f"ID: {format_id} | {ext} | {bitrate_str} | {format_note} | {filesize_str}"

                        audio_formats.append({
                            'format_id': format_id,
                            'display_text': display_text,
                            'ext': ext,
                            'bitrate': abr or 0,
                            'note': format_note,
                            'acodec': acodec,
                            'filesize': filesize
                        })
                        audio_count += 1

                # 按音频码率从高到低排序
                audio_formats.sort(key=lambda x: x['bitrate'], reverse=True)

                for idx, item in enumerate(audio_formats, 1):
                    self.output_signal.emit(f"   🎵 音频 #{idx}: {item['display_text']}")

                self.output_signal.emit(f"✅ 解析完成！共找到 {audio_count} 个纯音频格式")
                self.output_signal.emit("=" * 60)

                self.formats_ready.emit(audio_formats, video_title)

        except Exception as e:
            tb_str = traceback.format_exc()
            self.output_signal.emit(f"❌ 解析失败堆栈追踪:\n{tb_str}")
            self.output_signal.emit("=" * 60)
            self.fetch_error.emit(str(e))


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.download_worker = None
        self.fetch_worker = None
        self.current_formats = []
        self.current_video_title = ""
        self.download_path = os.path.expanduser("~/Downloads")

        # 重定向 sys.stdout 到界面
        self.output_redirect = OutputRedirect()
        self.output_redirect.output_signal.connect(self.append_output)
        sys.stdout = self.output_redirect

        self.init_ui()

    def init_ui(self):
        screen = QApplication.primaryScreen()
        screen_geometry = screen.availableGeometry()
        width = int(screen_geometry.width() * 0.85)
        height = int(screen_geometry.height() * 0.85)
        self.setGeometry(
            screen_geometry.x() + (screen_geometry.width() - width) // 2,
            screen_geometry.y() + (screen_geometry.height() - height) // 2,
            width,
            height
        )
        self.setWindowTitle("YouTube 音频下载器")
        self.setMinimumSize(900, 700)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(15, 15, 15, 15)

        # 顶部：URL输入
        url_group = QGroupBox("🎯 链接输入")
        url_layout = QHBoxLayout(url_group)

        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("请输入 YouTube 视频链接...")
        self.url_input.returnPressed.connect(self.fetch_formats)
        self.url_input.setMinimumHeight(30)

        self.fetch_btn = QPushButton("🔍 解析音频")
        self.fetch_btn.setFixedWidth(130)
        self.fetch_btn.setMinimumHeight(30)
        self.fetch_btn.clicked.connect(self.fetch_formats)
        self.fetch_btn.setStyleSheet("QPushButton { background-color: #4CAF50; color: white; font-weight: bold; }")

        url_layout.addWidget(self.url_input, 1)
        url_layout.addWidget(self.fetch_btn)
        main_layout.addWidget(url_group)

        # 视频标题
        self.title_label = QLabel("📺 视频标题: 等待解析...")
        self.title_label.setStyleSheet("font-weight: bold; font-size: 13px; padding: 5px; background-color: #f5f5f5; border-radius: 3px;")
        main_layout.addWidget(self.title_label)

        # 中间：格式列表与日志
        middle_split = QHBoxLayout()
        middle_split.setSpacing(10)

        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.addWidget(QLabel("🎵 可用音频格式 (双击下载):"))

        self.format_list = QListWidget()
        self.format_list.setSelectionMode(QAbstractItemView.SingleSelection)
        self.format_list.itemDoubleClicked.connect(self.download_selected)
        self.format_list.setMinimumWidth(300)
        left_layout.addWidget(self.format_list)

        middle_split.addWidget(left_widget, 1)

        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.addWidget(QLabel("📋 输出日志:"))

        self.output_text = QTextEdit()
        self.output_text.setReadOnly(True)
        self.output_text.setFont(QFont("Consolas", 9))
        self.output_text.setStyleSheet("QTextEdit { background-color: #1e1e1e; color: #d4d4d4; }")
        self.output_text.setMinimumWidth(350)
        self.output_text.setMinimumHeight(300)
        right_layout.addWidget(self.output_text)

        clear_btn = QPushButton("🗑 清除日志")
        clear_btn.setFixedWidth(100)
        clear_btn.clicked.connect(self.clear_output)
        right_layout.addWidget(clear_btn, 0, Qt.AlignRight)

        middle_split.addWidget(right_widget, 1)
        main_layout.addLayout(middle_split, 1)

        # 底部：路径与控制
        bottom_group = QGroupBox("⚙️ 下载控制")
        bottom_layout = QVBoxLayout(bottom_group)

        path_layout = QHBoxLayout()
        path_layout.addWidget(QLabel("📁 保存目录:"))
        self.path_display = QLineEdit()
        self.path_display.setText(self.download_path)
        self.path_display.setReadOnly(True)
        self.path_display.setMinimumWidth(300)
        path_layout.addWidget(self.path_display, 1)

        self.path_btn = QPushButton("📂 浏览...")
        self.path_btn.clicked.connect(self.select_output_path)
        path_layout.addWidget(self.path_btn)
        bottom_layout.addLayout(path_layout)

        control_layout = QHBoxLayout()

        self.download_btn = QPushButton("⬇ 下载选中")
        self.download_btn.setFixedWidth(130)
        self.download_btn.setEnabled(False)
        self.download_btn.clicked.connect(self.download_selected)
        self.download_btn.setStyleSheet("QPushButton { background-color: #2196F3; color: white; font-weight: bold; }")
        control_layout.addWidget(self.download_btn)

        self.cancel_btn = QPushButton("⏹ 取消")
        self.cancel_btn.setFixedWidth(100)
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.clicked.connect(self.cancel_download)
        self.cancel_btn.setStyleSheet("QPushButton { background-color: #f44336; color: white; font-weight: bold; }")
        control_layout.addWidget(self.cancel_btn)

        control_layout.addStretch()

        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedWidth(200)
        self.progress_bar.setValue(0)
        control_layout.addWidget(self.progress_bar)

        bottom_layout.addLayout(control_layout)
        main_layout.addWidget(bottom_group)

    def append_output(self, text):
        self.output_text.append(text)
        scrollbar = self.output_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def clear_output(self):
        self.output_text.clear()

    def select_output_path(self):
        path = QFileDialog.getExistingDirectory(self, "选择保存目录", self.download_path)
        if path:
            self.download_path = path
            self.path_display.setText(path)

    def fetch_formats(self):
        url = self.url_input.text().strip()
        if not url:
            QMessageBox.warning(self, "警告", "请输入 YouTube 链接")
            return

        self.format_list.clear()
        self.title_label.setText("📺 视频标题: 解析中...")
        self.fetch_btn.setEnabled(False)
        self.download_btn.setEnabled(False)
        self.progress_bar.setValue(0)
        self.output_text.clear()

        self.fetch_worker = AudioFormatFetcher(url)
        self.fetch_worker.formats_ready.connect(self.on_formats_ready)
        self.fetch_worker.fetch_error.connect(self.on_fetch_error)
        self.fetch_worker.output_signal.connect(self.append_output)
        self.fetch_worker.start()

    def on_formats_ready(self, formats, title):
        self.current_formats = formats
        self.current_video_title = title
        self.title_label.setText(f"📺 视频标题: {title}")

        self.format_list.clear()
        if formats:
            for f in formats:
                item = QListWidgetItem(f['display_text'])
                item.setData(Qt.UserRole, f['format_id'])
                self.format_list.addItem(item)

            self.format_list.setCurrentRow(0)
            self.download_btn.setEnabled(True)
            self.append_output(f"✅ 已成功加载 {len(formats)} 个音频格式")
        else:
            self.append_output("⚠️ 未找到纯音频格式，请确认链接是否为视频")
            self.download_btn.setEnabled(False)

        self.fetch_btn.setEnabled(True)

    def on_fetch_error(self, error_msg):
        self.fetch_btn.setEnabled(True)
        self.download_btn.setEnabled(False)
        self.title_label.setText("📺 视频标题: 解析失败 ❌")
        QMessageBox.critical(self, "解析失败", f"无法解析该链接，请查看右侧日志:\n{error_msg}")

    def download_selected(self):
        current_item = self.format_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "警告", "请先选择一个音频格式")
            return

        format_id = current_item.data(Qt.UserRole)
        if not format_id:
            QMessageBox.warning(self, "警告", "无法获取格式 ID")
            return

        url = self.url_input.text().strip()

        reply = QMessageBox.question(
            self,
            "确认下载",
            f"即将下载:\n{self.current_video_title}\n格式ID: {format_id}\n保存到: {self.download_path}",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return

        self.download_btn.setEnabled(False)
        self.fetch_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        self.progress_bar.setValue(0)

        self.download_worker = DownloadWorker(url, format_id, self.download_path)
        self.download_worker.progress_updated.connect(self.on_progress_updated)
        self.download_worker.download_finished.connect(self.on_download_finished)
        self.download_worker.download_error.connect(self.on_download_error)
        self.download_worker.output_signal.connect(self.append_output)
        self.download_worker.start()

    def cancel_download(self):
        if self.download_worker and self.download_worker.isRunning():
            self.download_worker.cancel()
            self.cancel_btn.setEnabled(False)

    def on_progress_updated(self, percent, status_msg):
        self.progress_bar.setValue(percent)

    def on_download_finished(self, msg):
        self.download_btn.setEnabled(True)
        self.fetch_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        self.progress_bar.setValue(100)
        QMessageBox.information(self, "下载完成", f"音频已保存到:\n{self.download_path}")

    def on_download_error(self, error_msg):
        self.download_btn.setEnabled(True)
        self.fetch_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        self.progress_bar.setValue(0)
        QMessageBox.critical(self, "下载失败", f"下载出错:\n{error_msg}")

    def closeEvent(self, event):
        if self.download_worker and self.download_worker.isRunning():
            self.download_worker.cancel()
            self.download_worker.wait()
        if self.fetch_worker and self.fetch_worker.isRunning():
            self.fetch_worker.terminate()
            self.fetch_worker.wait()

        sys.stdout = sys.__stdout__
        event.accept()


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("YouTube 音频下载器")
    app.setStyle('Fusion')

    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()