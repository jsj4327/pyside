"""ui/crawler_tab.py — 支持双占位符范围配置的爬虫界面"""

import os
from datetime import datetime
from PySide2.QtCore import QSettings, Qt, QTimer, Signal
from PySide2.QtGui import QTextCursor
from PySide2.QtWidgets import (
    QCheckBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QSpinBox,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from config import APP_NAME, BATCH_SIZE, MAX_LOG_LINES
from database import DatabaseManager
from threads import CrawlerThread

DEFAULT_TEMPLATE_URL = (
    "http://paper.people.com.cn/rmrb/pc/layout/202607/{0}/node_{1}.html"
)


class CrawlerTab(QWidget):
    status_message = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.settings = QSettings(APP_NAME, "Crawler")
        self.save_dir = self.settings.value(
            "save_dir",
            os.path.join(os.path.expanduser("~"), "CrawledArticles"),
        )
        self.db_path = os.path.join(self.save_dir, "articles.db")
        self.thread = None
        self._log_count = 0
        self._init_ui()
        self.refresh_db_stats()

    def _init_ui(self):
        main_splitter = QSplitter(Qt.Vertical)

        top_widget = QWidget()
        top_layout = QVBoxLayout(top_widget)
        top_layout.setContentsMargins(10, 10, 10, 10)
        top_layout.setSpacing(10)

        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(10)

        target_box = QGroupBox("🌐 URL 模板与双占位符范围")
        target_layout = QVBoxLayout(target_box)
        target_layout.setSpacing(8)

        tmpl_form = QFormLayout()
        self.edit_template = QLineEdit(DEFAULT_TEMPLATE_URL)
        self.edit_template.textChanged.connect(self._update_url_preview)
        tmpl_form.addRow("目标 URL 模板:", self.edit_template)
        target_layout.addLayout(tmpl_form)

        lbl_tip = QLabel(
            "💡 使用 {0} 和 {1} 作为占位符（如 {0}=日期天数，{1}=版面编号 node_01）"
        )
        lbl_tip.setStyleSheet("color: #666; font-size: 11px;")
        target_layout.addWidget(lbl_tip)

        p1_row = QHBoxLayout()
        self.chk_p1 = QCheckBox("启用 {0}")
        self.chk_p1.setChecked(True)
        self.chk_p1.stateChanged.connect(self._update_url_preview)

        self.spin_p1_start = QSpinBox()
        self.spin_p1_start.setRange(1, 9999)
        self.spin_p1_start.setValue(1)
        self.spin_p1_start.valueChanged.connect(self._update_url_preview)

        self.spin_p1_end = QSpinBox()
        self.spin_p1_end.setRange(1, 9999)
        self.spin_p1_end.setValue(31)
        self.spin_p1_end.valueChanged.connect(self._update_url_preview)

        self.spin_p1_pad = QSpinBox()
        self.spin_p1_pad.setRange(1, 10)
        self.spin_p1_pad.setValue(2)
        self.spin_p1_pad.setSuffix(" 位")
        self.spin_p1_pad.valueChanged.connect(self._update_url_preview)

        p1_row.addWidget(self.chk_p1)
        p1_row.addWidget(QLabel("范围:"))
        p1_row.addWidget(self.spin_p1_start)
        p1_row.addWidget(QLabel("~"))
        p1_row.addWidget(self.spin_p1_end)
        p1_row.addWidget(QLabel("补零:"))
        p1_row.addWidget(self.spin_p1_pad)
        target_layout.addLayout(p1_row)

        p2_row = QHBoxLayout()
        self.chk_p2 = QCheckBox("启用 {1}")
        self.chk_p2.setChecked(True)
        self.chk_p2.stateChanged.connect(self._update_url_preview)

        self.spin_p2_start = QSpinBox()
        self.spin_p2_start.setRange(1, 9999)
        self.spin_p2_start.setValue(1)
        self.spin_p2_start.valueChanged.connect(self._update_url_preview)

        self.spin_p2_end = QSpinBox()
        self.spin_p2_end.setRange(1, 9999)
        self.spin_p2_end.setValue(12)
        self.spin_p2_end.valueChanged.connect(self._update_url_preview)

        self.spin_p2_pad = QSpinBox()
        self.spin_p2_pad.setRange(1, 10)
        self.spin_p2_pad.setValue(2)
        self.spin_p2_pad.setSuffix(" 位")
        self.spin_p2_pad.valueChanged.connect(self._update_url_preview)

        p2_row.addWidget(self.chk_p2)
        p2_row.addWidget(QLabel("范围:"))
        p2_row.addWidget(self.spin_p2_start)
        p2_row.addWidget(QLabel("~"))
        p2_row.addWidget(self.spin_p2_end)
        p2_row.addWidget(QLabel("补零:"))
        p2_row.addWidget(self.spin_p2_pad)
        target_layout.addLayout(p2_row)

        self.lbl_preview = QLabel("预估生成: -- 个 URL")
        self.lbl_preview.setStyleSheet(
            "color: #2E7D32; font-weight: bold; font-size: 11px;"
        )
        target_layout.addWidget(self.lbl_preview)

        cards_layout.addWidget(target_box, stretch=3)

        setting_box = QGroupBox("⚙️ 保存路径与抓取策略")
        setting_form = QFormLayout(setting_box)
        setting_form.setSpacing(10)

        path_layout = QHBoxLayout()
        self.edit_save_dir = QLineEdit(self.save_dir)
        self.edit_save_dir.setReadOnly(True)
        self.btn_browse = QPushButton("📁 浏览...")
        self.btn_browse.clicked.connect(self._select_save_dir)
        path_layout.addWidget(self.edit_save_dir)
        path_layout.addWidget(self.btn_browse)
        setting_form.addRow("数据目录:", path_layout)

        self.chk_content = QCheckBox("解析并下载文章正文")
        self.chk_content.setChecked(True)
        setting_form.addRow("抓取选项:", self.chk_content)

        self.spin_batch = QSpinBox()
        self.spin_batch.setRange(10, 500)
        self.spin_batch.setValue(BATCH_SIZE)
        self.spin_batch.setSuffix(" 条/批")
        setting_form.addRow("批处理量:", self.spin_batch)

        self.lbl_db_total = QLabel("0 条")
        self.lbl_db_total.setStyleSheet("font-weight: bold; color: #1976D2;")
        self.lbl_db_size = QLabel("0.0 MB")
        setting_form.addRow("数据库已存:", self.lbl_db_total)
        setting_form.addRow("文件占用:", self.lbl_db_size)

        cards_layout.addWidget(setting_box, stretch=2)
        top_layout.addLayout(cards_layout)

        action_box = QGroupBox("🚀 任务控制中心")
        action_layout = QVBoxLayout(action_box)

        btn_row = QHBoxLayout()
        self.btn_start = QPushButton("▶ 开始爬取任务")
        self.btn_start.setFixedHeight(36)
        self.btn_start.setStyleSheet("""
            QPushButton { background-color: #2E7D32; color: white; font-weight: bold; border-radius: 4px; }
            QPushButton:hover { background-color: #388E3C; }
            QPushButton:disabled { background-color: #C8E6C9; color: #81C784; }
        """)
        self.btn_start.clicked.connect(self.start_crawl)

        self.btn_stop = QPushButton("⏹ 停止抓取")
        self.btn_stop.setFixedHeight(36)
        self.btn_stop.setEnabled(False)
        self.btn_stop.setStyleSheet("""
            QPushButton { background-color: #C62828; color: white; font-weight: bold; border-radius: 4px; }
            QPushButton:hover { background-color: #D32F2F; }
            QPushButton:disabled { background-color: #FFCDD2; color: #E57373; }
        """)
        self.btn_stop.clicked.connect(self.stop_crawl)

        btn_row.addWidget(self.btn_start, stretch=2)
        btn_row.addWidget(self.btn_stop, stretch=1)
        action_layout.addLayout(btn_row)

        prog_layout = QHBoxLayout()
        self.lbl_status = QLabel("就绪 (等待开始)")
        self.lbl_status.setStyleSheet("color: #666;")

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)

        prog_layout.addWidget(self.lbl_status, stretch=1)
        prog_layout.addWidget(self.progress_bar, stretch=2)
        action_layout.addLayout(prog_layout)

        top_layout.addWidget(action_box)
        main_splitter.addWidget(top_widget)

        log_widget = QWidget()
        log_layout = QVBoxLayout(log_widget)
        log_layout.setContentsMargins(10, 5, 10, 10)

        log_header = QHBoxLayout()
        log_header.addWidget(QLabel("📋 运行日志输出"))
        log_header.addStretch()

        self.chk_autoscroll = QCheckBox("自动滚动")
        self.chk_autoscroll.setChecked(True)
        log_header.addWidget(self.chk_autoscroll)

        btn_clear_log = QPushButton("🧹 清空日志")
        btn_clear_log.setFixedHeight(24)
        btn_clear_log.clicked.connect(self.clear_log)
        log_header.addWidget(btn_clear_log)
        log_layout.addLayout(log_header)

        self.log_text = QPlainTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setStyleSheet("""
            QPlainTextEdit {
                background-color: #1E1E1E;
                color: #D4D4D4;
                font-family: "Consolas", "Microsoft YaHei Mono", monospace;
                font-size: 12px;
                border: 1px solid #333;
                border-radius: 4px;
            }
        """)
        log_layout.addWidget(self.log_text)

        main_splitter.addWidget(log_widget)
        main_splitter.setStretchFactor(0, 4)
        main_splitter.setStretchFactor(1, 6)

        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.addWidget(main_splitter)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self.refresh_db_stats)
        self._timer.start(5000)

        self._update_url_preview()

    def _update_url_preview(self):
        c1 = (
            (self.spin_p1_end.value() - self.spin_p1_start.value() + 1)
            if self.chk_p1.isChecked()
            else 1
        )
        c2 = (
            (self.spin_p2_end.value() - self.spin_p2_start.value() + 1)
            if self.chk_p2.isChecked()
            else 1
        )
        total = max(c1, 1) * max(c2, 1)

        p1_val = str(self.spin_p1_start.value()).zfill(
            self.spin_p1_pad.value()
        )
        p2_val = str(self.spin_p2_start.value()).zfill(
            self.spin_p2_pad.value()
        )
        tmpl = self.edit_template.text().strip()

        try:
            demo_url = tmpl.format(p1_val, p2_val)
        except Exception:
            demo_url = tmpl

        self.lbl_preview.setText(
            f"预估生成 {total} 个 URL | 首个示例: {demo_url}"
        )

    def append_log(self, text, level="INFO"):
        now = datetime.now().strftime("%H:%M:%S")
        self.log_text.appendPlainText(f"[{now}] [{level}] {text}")
        self._log_count += 1

        if self._log_count > MAX_LOG_LINES:
            lines = self.log_text.toPlainText().split("\n")
            self.log_text.setPlainText("\n".join(lines[-MAX_LOG_LINES:]))
            self._log_count = MAX_LOG_LINES

        if self.chk_autoscroll.isChecked():
            self.log_text.moveCursor(QTextCursor.End)

    def clear_log(self):
        self.log_text.clear()
        self._log_count = 0

    def _select_save_dir(self):
        selected = QFileDialog.getExistingDirectory(
            self, "选择数据保存目录", self.save_dir
        )
        if selected:
            self.save_dir = selected
            self.db_path = os.path.join(self.save_dir, "articles.db")
            self.edit_save_dir.setText(self.save_dir)
            self.settings.setValue("save_dir", self.save_dir)
            self.refresh_db_stats()
            self.append_log(f"修改存储路径为: {self.save_dir}")

    def refresh_db_stats(self):
        if os.path.exists(self.db_path):
            try:
                db = DatabaseManager(self.db_path)
                stats = db.get_stats()
                db.close()
                self.lbl_db_total.setText(f"{stats['total']} 条")
                self.lbl_db_size.setText(f"{stats['db_size_mb']:.2f} MB")
            except Exception:
                pass

    def start_crawl(self):
        url_template = self.edit_template.text().strip()
        if not url_template:
            self.append_log("⚠️ 目标 URL 模板不能为空！", "WARN")
            return

        p1_cfg = {
            "enabled": self.chk_p1.isChecked(),
            "start": self.spin_p1_start.value(),
            "end": self.spin_p1_end.value(),
            "pad": self.spin_p1_pad.value(),
        }

        p2_cfg = {
            "enabled": self.chk_p2.isChecked(),
            "start": self.spin_p2_start.value(),
            "end": self.spin_p2_end.value(),
            "pad": self.spin_p2_pad.value(),
        }

        os.makedirs(self.save_dir, exist_ok=True)
        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self.lbl_status.setText("正在准备初始化任务...")

        self.append_log("=" * 40)
        self.append_log(f"开始抓取任务 | 模板: {url_template}")

        self.thread = CrawlerThread(
            url_template,
            p1_cfg,
            p2_cfg,
            self.db_path,
            self.chk_content.isChecked(),
            self.spin_batch.value(),
        )
        self.thread.progress_signal.connect(self.on_progress)
        self.thread.batch_saved_signal.connect(self.on_batch_saved)
        self.thread.finished_signal.connect(self.on_finished)
        self.thread.start()

    def stop_crawl(self):
        if self.thread and self.thread.isRunning():
            self.append_log("正在发送停止指令...", "WARN")
            self.btn_stop.setEnabled(False)
            self.lbl_status.setText("正在停止任务...")
            self.thread.cancel()

    def on_progress(self, current, total, stage_msg):
        pct = int((current / max(total, 1)) * 100)
        self.progress_bar.setValue(pct)
        self.lbl_status.setText(f"{stage_msg} ({current}/{total})")

    def on_batch_saved(self, inserted, skipped):
        self.append_log(f"写入数据库: 新增 {inserted} 条 / 跳过重复 {skipped} 条")
        self.refresh_db_stats()

    def on_finished(self, result):
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self.refresh_db_stats()

        status = result.get("status")
        if status == "success":
            self.progress_bar.setValue(100)
            self.lbl_status.setText("任务已完成！")
            self.append_log("🎉 抓取任务顺利完成！")
            self.append_log(
                f"统计: 成功提取={result.get('count')} 条, 插入={result.get('inserted')}, 正文={result.get('content_ok')}"
            )
        elif status == "cancelled":
            self.lbl_status.setText("任务已被用户取消")
            self.append_log("⏹ 任务已被取消", "WARN")
        elif status == "empty":
            self.lbl_status.setText("未发现有效数据")
            self.append_log("⚠️ 未在生成的 URL 中解析到文章", "WARN")
        else:
            self.lbl_status.setText("任务发生异常")
            self.append_log(f"❌ 错误: {result.get('message')}", "ERROR")

        self.status_message.emit(f"任务结束: {status}")

    def cleanup(self):
        if self.thread and self.thread.isRunning():
            self.thread.cancel()
            self.thread.wait(2000)