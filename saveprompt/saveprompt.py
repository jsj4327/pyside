import sys
import os
import json
from datetime import datetime
from PySide2.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                               QHBoxLayout, QPushButton, QLabel, QLineEdit, 
                               QTreeWidget, QTreeWidgetItem, QTableWidget, 
                               QTableWidgetItem, QSplitter, QPlainTextEdit, 
                               QHeaderView, QMessageBox, QDialog, QFormLayout, 
                               QComboBox, QGroupBox, QMenu, QAction, QInputDialog,
                               QProgressBar, QStackedWidget)
from PySide2.QtCore import Qt, QThread, Signal
from PySide2.QtGui import QFont

DATA_FILE = "prompts_data.json"
PAGE_SIZE_OPTIONS = [50, 100, 200, 500]

# 默认预设初始数据
DEFAULT_DATA = {
    "categories": ["编程协同", "翻译润色", "文本写作", "角色扮演", "通用工具"],
    "prompts": [
        {
            "id": "1",
            "title": "Python 代码重构与架构分析",
            "category": "编程协同",
            "tags": "Python, 重构, 架构",
            "prompt": "你是一个资深的 Python 架构师。请分析以下代码的逻辑缺陷、性能瓶颈以及架构不合理之处，并给出遵循 PEP 8 和模块化单体原则的重构建议：\n\n[在此粘贴代码]",
            "notes": "适用于排查复杂业务逻辑或臃肿函数",
            "updated_at": "2026-07-29 10:00:00"
        },
        {
            "id": "2",
            "title": "专业技术文档翻译 (英译中)",
            "category": "翻译润色",
            "tags": "翻译, 技术文档",
            "prompt": "请将以下英文技术文档翻译为地道的中文。要求：\n1. 保持专业术语准确（如 Repository, Decorator, Dependency Injection 等）；\n2. 语句通顺，符合中文阅读习惯；\n3. 保留原有的 Markdown 格式。\n\n[粘贴英文内容]",
            "notes": "适合翻译 GitHub Readme 或 API 文档",
            "updated_at": "2026-07-29 11:30:00"
        }
    ]
}

# ==========================================
# 0. 异步数据加载线程 (QThread)
# ==========================================
class DataLoaderThread(QThread):
    """在后台子线程中进行 JSON 读取与解析，避免阻塞主 UI 线程"""
    loaded_signal = Signal(dict)
    error_signal = Signal(str)

    def run(self):
        try:
            if not os.path.exists(DATA_FILE):
                # 写入默认数据
                with open(DATA_FILE, 'w', encoding='utf-8') as f:
                    json.dump(DEFAULT_DATA, f, ensure_ascii=False, indent=2)
                self.loaded_signal.emit(DEFAULT_DATA)
            else:
                with open(DATA_FILE, 'r', encoding='utf-8') as f:
                    raw = json.load(f)
                    if isinstance(raw, dict):
                        categories = raw.get("categories", ["编程协同", "翻译润色", "文本写作", "角色扮演", "通用工具"])
                        prompts = raw.get("prompts", [])
                    elif isinstance(raw, list):
                        prompts = raw
                        cats = set(["编程协同", "翻译润色", "文本写作", "角色扮演", "通用工具"])
                        for p in prompts:
                            if p.get("category"):
                                cats.add(p["category"])
                        categories = sorted(list(cats))
                    else:
                        categories, prompts = DEFAULT_DATA["categories"], DEFAULT_DATA["prompts"]

                    self.loaded_signal.emit({"categories": categories, "prompts": prompts})
        except Exception as e:
            self.error_signal.emit(str(e))

# ==========================================
# 1. 新增 / 编辑 Prompt 对话框
# ==========================================
class PromptEditDialog(QDialog):
    def __init__(self, parent=None, categories=None, prompt_data=None):
        super().__init__(parent)
        self.setWindowTitle("编辑 Prompt" if prompt_data else "新增 Prompt")
        self.resize(600, 480)
        self.categories = categories or ["编程协同", "文本写作", "翻译润色", "角色扮演", "通用工具"]
        self.prompt_data = prompt_data or {}

        layout = QVBoxLayout(self)
        form_layout = QFormLayout()

        self.input_title = QLineEdit(self.prompt_data.get("title", ""))
        
        self.combo_category = QComboBox()
        self.combo_category.setEditable(True)
        self.combo_category.addItems(self.categories)
        if "category" in self.prompt_data:
            self.combo_category.setCurrentText(self.prompt_data["category"])

        self.input_tags = QLineEdit(self.prompt_data.get("tags", ""))
        self.input_tags.setPlaceholderText("用逗号分隔，如: Python, Qt, 架构")

        # 使用 QPlainTextEdit 替代 QTextEdit
        self.input_prompt = QPlainTextEdit(self.prompt_data.get("prompt", ""))
        self.input_prompt.setFont(QFont("Consolas", 10))

        self.input_notes = QLineEdit(self.prompt_data.get("notes", ""))

        form_layout.addRow("标题 (*):", self.input_title)
        form_layout.addRow("分类:", self.combo_category)
        form_layout.addRow("标签:", self.input_tags)
        form_layout.addRow("Prompt 内容 (*):", self.input_prompt)
        form_layout.addRow("备注说明:", self.input_notes)

        layout.addLayout(form_layout)

        btn_layout = QHBoxLayout()
        btn_save = QPushButton("保存")
        btn_save.setStyleSheet("background-color: #007ACC; color: white; font-weight: bold;")
        btn_save.clicked.connect(self.accept)
        
        btn_cancel = QPushButton("取消")
        btn_cancel.clicked.connect(self.reject)

        btn_layout.addStretch()
        btn_layout.addWidget(btn_save)
        btn_layout.addWidget(btn_cancel)
        layout.addLayout(btn_layout)

    def get_data(self):
        return {
            "id": self.prompt_data.get("id", str(int(datetime.now().timestamp()))),
            "title": self.input_title.text().strip(),
            "category": self.combo_category.currentText().strip() or "通用工具",
            "tags": self.input_tags.text().strip(),
            # 保留原始文本格式（换行、首尾空格等都不做强制裁切）
            "prompt": self.input_prompt.toPlainText(),
            "notes": self.input_notes.text().strip(),
            "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

# ==========================================
# 2. 主界面类
# ==========================================
class PromptManagerApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Prompt 提示词分类与搜索管理")
        
        self.categories = []
        self.prompts = []
        self.filtered_prompts = []
        self.current_selected_prompt = None

        # 分页/分段控制变量
        self.current_page = 1
        self.page_size = 50

        self.init_ui()
        self.center_on_screen()
        self.load_data_async()

    def center_on_screen(self):
        """主界面大小设置为屏幕可用区域（不含工具栏/任务栏）的 85% 并居中"""
        screen = QApplication.primaryScreen()
        avail_geo = screen.availableGeometry()
        
        width = int(avail_geo.width() * 0.85)
        height = int(avail_geo.height() * 0.85)
        
        x = avail_geo.x() + (avail_geo.width() - width) // 2
        y = avail_geo.y() + (avail_geo.height() - height) // 2
        
        self.setGeometry(x, y, width, height)

    # ------------------------------------------
    # 异步加载与保存数据
    # ------------------------------------------
    def load_data_async(self):
        """启动后台线程加载数据"""
        self.stack_widget.setCurrentIndex(0) # 显示加载过渡界面
        self.loading_bar.setRange(0, 0)      # 跑马灯效果

        self.loader_thread = DataLoaderThread()
        self.loader_thread.loaded_signal.connect(self.on_data_loaded)
        self.loader_thread.error_signal.connect(self.on_data_load_error)
        self.loader_thread.start()

    def on_data_loaded(self, data):
        self.categories = data.get("categories", [])
        self.prompts = data.get("prompts", [])
        
        self.stack_widget.setCurrentIndex(1) # 切换到主功能界面
        self.refresh_all()

    def on_data_load_error(self, err_msg):
        self.stack_widget.setCurrentIndex(1)
        QMessageBox.critical(self, "数据加载错误", f"读取数据文件失败: {err_msg}")

    def save_data(self):
        try:
            data = {
                "categories": self.categories,
                "prompts": self.prompts
            }
            with open(DATA_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            QMessageBox.critical(self, "保存错误", f"保存数据失败: {str(e)}")

    # ------------------------------------------
    # 界面初始化
    # ------------------------------------------
    def init_ui(self):
        # 使用 QStackedWidget 切换“加载页面”和“主内容页面”
        self.stack_widget = QStackedWidget()
        self.setCentralWidget(self.stack_widget)

        # 页面 0: 加载状态屏
        loading_widget = QWidget()
        loading_layout = QVBoxLayout(loading_widget)
        loading_layout.addStretch()
        
        lbl_load = QLabel("<b>正在异步加载数据，请稍候...</b>")
        lbl_load.setAlignment(Qt.AlignCenter)
        self.loading_bar = QProgressBar()
        self.loading_bar.setFixedWidth(300)
        
        loading_layout.addWidget(lbl_load)
        loading_layout.addWidget(self.loading_bar, alignment=Qt.AlignCenter)
        loading_layout.addStretch()
        
        self.stack_widget.addWidget(loading_widget)

        # 页面 1: 主功能界面
        main_widget = QWidget()
        main_layout = QHBoxLayout(main_widget)

        main_splitter = QSplitter(Qt.Horizontal)

        # ====================
        # 左侧：分类导航
        # ====================
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)

        cat_header = QHBoxLayout()
        cat_header.addWidget(QLabel("<b>分类导航</b>"))
        
        btn_add_cat = QPushButton("+ 新增分类")
        btn_add_cat.setFixedHeight(24)
        btn_add_cat.clicked.connect(self.add_category_dialog)
        cat_header.addWidget(btn_add_cat)
        
        left_layout.addLayout(cat_header)

        self.category_tree = QTreeWidget()
        self.category_tree.setHeaderHidden(True)
        self.category_tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.category_tree.customContextMenuRequested.connect(self.show_category_context_menu)
        self.category_tree.itemClicked.connect(self.on_category_selected)
        
        left_layout.addWidget(self.category_tree)
        main_splitter.addWidget(left_widget)

        # ====================
        # 右侧：搜索 + 分页表格 + 详情
        # ====================
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)

        # 1. 顶部控制条 (搜索框)
        top_bar = QHBoxLayout()
        top_bar.addWidget(QLabel("搜索:"))
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("实时搜索标题、标签、Prompt 或备注...")
        self.search_input.textChanged.connect(self.filter_prompts)
        top_bar.addWidget(self.search_input)

        btn_add_prompt = QPushButton("+ 新增 Prompt")
        btn_add_prompt.setStyleSheet("background-color: #28A745; color: white; font-weight: bold;")
        btn_add_prompt.clicked.connect(self.add_prompt)
        top_bar.addWidget(btn_add_prompt)

        right_layout.addLayout(top_bar)

        # 2. 右侧垂直 Splitter
        right_splitter = QSplitter(Qt.Vertical)

        # 表格 + 分页栏面板
        table_container = QWidget()
        table_vbox = QVBoxLayout(table_container)
        table_vbox.setContentsMargins(0, 0, 0, 0)

        self.table_widget = QTableWidget()
        self.table_widget.setColumnCount(4)
        self.table_widget.setHorizontalHeaderLabels(["标题", "分类", "标签", "更新时间"])
        self.table_widget.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table_widget.setSelectionBehavior(QTableWidget.SelectRows)
        self.table_widget.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table_widget.itemSelectionChanged.connect(self.on_table_selection_changed)
        table_vbox.addWidget(self.table_widget)

        # ---- 分页控制工具栏 ----
        page_bar = QHBoxLayout()
        self.lbl_page_status = QLabel("共 0 条数据")
        
        self.btn_prev_page = QPushButton("< 上一页")
        self.btn_prev_page.setFixedWidth(80)
        self.btn_prev_page.clicked.connect(self.prev_page)

        self.lbl_page_info = QLabel("页次: 1/1")
        
        self.btn_next_page = QPushButton("下一页 >")
        self.btn_next_page.setFixedWidth(80)
        self.btn_next_page.clicked.connect(self.next_page)

        page_bar.addWidget(self.lbl_page_status)
        page_bar.addStretch()
        page_bar.addWidget(self.btn_prev_page)
        page_bar.addWidget(self.lbl_page_info)
        page_bar.addWidget(self.btn_next_page)

        page_bar.addWidget(QLabel(" 每页显示:"))
        self.combo_page_size = QComboBox()
        for size in PAGE_SIZE_OPTIONS:
            self.combo_page_size.addItem(f"{size} 条", size)
        self.combo_page_size.currentIndexChanged.connect(self.on_page_size_changed)
        page_bar.addWidget(self.combo_page_size)

        table_vbox.addLayout(page_bar)
        right_splitter.addWidget(table_container)

        # 3. 底部详情面板
        detail_group = QGroupBox("Prompt 详情与预览")
        detail_layout = QVBoxLayout(detail_group)

        self.lbl_detail_title = QLabel("<span style='font-size:14px; font-weight:bold;'>请选择一条 Prompt</span>")
        self.lbl_detail_info = QLabel("<span style='color:#666;'>分类: - | 标签: - | 备注: -</span>")
        
        detail_layout.addWidget(self.lbl_detail_title)
        detail_layout.addWidget(self.lbl_detail_info)

        # 使用 QPlainTextEdit 替代 QTextEdit
        self.text_preview = QPlainTextEdit()
        self.text_preview.setFont(QFont("Consolas", 10))
        self.text_preview.setReadOnly(True)
        detail_layout.addWidget(self.text_preview)

        # 详情按钮区
        btn_detail_layout = QHBoxLayout()
        self.btn_copy = QPushButton("一键复制 Prompt")
        self.btn_copy.setFixedHeight(30)
        self.btn_copy.setStyleSheet("font-weight: bold; background-color: #007ACC; color: white;")
        self.btn_copy.clicked.connect(self.copy_to_clipboard)

        self.btn_edit = QPushButton("编辑")
        self.btn_edit.clicked.connect(self.edit_prompt)

        self.btn_delete = QPushButton("删除")
        self.btn_delete.setStyleSheet("color: red;")
        self.btn_delete.clicked.connect(self.delete_prompt)

        btn_detail_layout.addWidget(self.btn_copy)
        btn_detail_layout.addStretch()
        btn_detail_layout.addWidget(self.btn_edit)
        btn_detail_layout.addWidget(self.btn_delete)

        detail_layout.addLayout(btn_detail_layout)
        right_splitter.addWidget(detail_group)

        right_splitter.setStretchFactor(0, 3)
        right_splitter.setStretchFactor(1, 2)

        right_layout.addWidget(right_splitter)
        main_splitter.addWidget(right_widget)

        main_splitter.setStretchFactor(0, 1)
        main_splitter.setStretchFactor(1, 4)

        main_layout.addWidget(main_splitter)
        self.stack_widget.addWidget(main_widget)

    # ------------------------------------------
    # 分类管理 Core
    # ------------------------------------------
    def add_category_dialog(self):
        name, ok = QInputDialog.getText(self, "新增分类", "请输入新分类名称:")
        if ok and name.strip():
            cat_name = name.strip()
            if cat_name in self.categories:
                QMessageBox.warning(self, "提示", f"分类 [{cat_name}] 已存在！")
                return
            
            self.categories.append(cat_name)
            self.save_data()
            self.refresh_all()

    def rename_category_dialog(self, old_name):
        if not old_name or old_name == "ALL":
            return

        new_name, ok = QInputDialog.getText(self, "重命名分类", f"请输入 [{old_name}] 的新名称:", text=old_name)
        if ok and new_name.strip():
            new_name = new_name.strip()
            if new_name == old_name:
                return
            if new_name in self.categories:
                QMessageBox.warning(self, "提示", f"分类名称 [{new_name}] 已存在！")
                return

            if old_name in self.categories:
                idx = self.categories.index(old_name)
                self.categories[idx] = new_name

            for p in self.prompts:
                if p.get("category") == old_name:
                    p["category"] = new_name

            self.save_data()
            self.refresh_all()

    def delete_category_dialog(self, cat_name):
        if not cat_name or cat_name == "ALL":
            return

        count = sum(1 for p in self.prompts if p.get("category") == cat_name)
        msg = f"确定要删除分类 [{cat_name}] 吗？"
        if count > 0:
            msg += f"\n\n注意：该分类下存在 {count} 条 Prompt，删除后它们将被重定向为 '未分类'。"

        reply = QMessageBox.question(self, "确认删除分类", msg, QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            if cat_name in self.categories:
                self.categories.remove(cat_name)

            if count > 0:
                if "未分类" not in self.categories:
                    self.categories.append("未分类")
                for p in self.prompts:
                    if p.get("category") == cat_name:
                        p["category"] = "未分类"

            self.save_data()
            self.refresh_all()

    def show_category_context_menu(self, pos):
        item = self.category_tree.itemAt(pos)
        menu = QMenu(self)

        action_add = QAction("新增分类", self)
        action_add.triggered.connect(self.add_category_dialog)
        menu.addAction(action_add)

        if item:
            cat_name = item.data(0, Qt.UserRole)
            if cat_name and cat_name != "ALL":
                menu.addSeparator()
                
                action_rename = QAction(f"重命名 '{cat_name}'", self)
                action_rename.triggered.connect(lambda: self.rename_category_dialog(cat_name))
                menu.addAction(action_rename)

                action_delete = QAction(f"删除分类 '{cat_name}'", self)
                action_delete.triggered.connect(lambda: self.delete_category_dialog(cat_name))
                menu.addAction(action_delete)

        menu.exec_(self.category_tree.viewport().mapToGlobal(pos))

    # ------------------------------------------
    # 刷新与过滤 + 分段渲染核心逻辑
    # ------------------------------------------
    def refresh_all(self):
        self.update_category_tree()
        self.filter_prompts()

    def update_category_tree(self):
        current_selected = self.category_tree.currentItem()
        selected_cat = current_selected.data(0, Qt.UserRole) if current_selected else "ALL"

        self.category_tree.clear()
        
        total_count = len(self.prompts)
        all_item = QTreeWidgetItem([f"全部分类 ({total_count})"])
        all_item.setData(0, Qt.UserRole, "ALL")
        self.category_tree.addTopLevelItem(all_item)

        for cat in self.categories:
            count = sum(1 for p in self.prompts if p.get("category") == cat)
            item = QTreeWidgetItem([f"{cat} ({count})"])
            item.setData(0, Qt.UserRole, cat)
            self.category_tree.addTopLevelItem(item)

        self.category_tree.expandAll()

        target_item = all_item
        for i in range(self.category_tree.topLevelItemCount()):
            it = self.category_tree.topLevelItem(i)
            if it.data(0, Qt.UserRole) == selected_cat:
                target_item = it
                break
        self.category_tree.setCurrentItem(target_item)

    def filter_prompts(self):
        search_kw = self.search_input.text().lower().strip()
        
        selected_item = self.category_tree.currentItem()
        selected_cat = selected_item.data(0, Qt.UserRole) if selected_item else "ALL"

        self.filtered_prompts = []

        for p in self.prompts:
            if selected_cat != "ALL" and p.get("category") != selected_cat:
                continue

            if search_kw:
                match_target = f"{p.get('title', '')} {p.get('tags', '')} {p.get('prompt', '')} {p.get('notes', '')}".lower()
                if search_kw not in match_target:
                    continue

            self.filtered_prompts.append(p)

        # 重置回第 1 页并渲染
        self.current_page = 1
        self.render_table_chunk()

    def render_table_chunk(self):
        """分段渲染：只向表格中插入当前页的切片数据，极速绘制"""
        total_count = len(self.filtered_prompts)
        total_pages = max(1, (total_count + self.page_size - 1) // self.page_size)
        
        if self.current_page > total_pages:
            self.current_page = total_pages

        start_idx = (self.current_page - 1) * self.page_size
        end_idx = min(start_idx + self.page_size, total_count)
        
        chunk_data = self.filtered_prompts[start_idx:end_idx]

        self.table_widget.setRowCount(0)
        for row, p in enumerate(chunk_data):
            self.table_widget.insertRow(row)
            self.table_widget.setItem(row, 0, QTableWidgetItem(p.get("title", "")))
            self.table_widget.setItem(row, 1, QTableWidgetItem(p.get("category", "")))
            self.table_widget.setItem(row, 2, QTableWidgetItem(p.get("tags", "")))
            self.table_widget.setItem(row, 3, QTableWidgetItem(p.get("updated_at", "")))

        # 更新分页控件状态
        self.lbl_page_status.setText(f"共 <b>{total_count}</b> 条数据")
        self.lbl_page_info.setText(f"页次: <b>{self.current_page}</b> / {total_pages}")
        self.btn_prev_page.setEnabled(self.current_page > 1)
        self.btn_next_page.setEnabled(self.current_page < total_pages)

        if chunk_data:
            self.table_widget.selectRow(0)
        else:
            self.lbl_detail_title.setText("<span style='font-size:14px; font-weight:bold;'>无匹配数据</span>")
            self.lbl_detail_info.setText("<span style='color:#666;'>分类: - | 标签: - | 备注: -</span>")
            self.text_preview.clear()
            self.current_selected_prompt = None

    # ---- 分页事件 ----
    def prev_page(self):
        if self.current_page > 1:
            self.current_page -= 1
            self.render_table_chunk()

    def next_page(self):
        total_pages = (len(self.filtered_prompts) + self.page_size - 1) // self.page_size
        if self.current_page < total_pages:
            self.current_page += 1
            self.render_table_chunk()

    def on_page_size_changed(self, index):
        self.page_size = self.combo_page_size.currentData()
        self.current_page = 1
        self.render_table_chunk()

    # ------------------------------------------
    # Prompt 联动与响应
    # ------------------------------------------
    def on_category_selected(self, item, column):
        self.filter_prompts()

    def on_table_selection_changed(self):
        selected_rows = self.table_widget.selectionModel().selectedRows()
        if not selected_rows:
            self.current_selected_prompt = None
            self.lbl_detail_title.setText("<span style='font-size:14px; font-weight:bold;'>请选择一条 Prompt</span>")
            self.lbl_detail_info.setText("<span style='color:#666;'>分类: - | 标签: - | 备注: -</span>")
            self.text_preview.clear()
            return

        row_in_chunk = selected_rows[0].row()
        actual_idx = (self.current_page - 1) * self.page_size + row_in_chunk

        if 0 <= actual_idx < len(self.filtered_prompts):
            self.current_selected_prompt = self.filtered_prompts[actual_idx]
            
            title = self.current_selected_prompt.get('title', '')
            category = self.current_selected_prompt.get('category', '')
            tags = self.current_selected_prompt.get('tags', '')
            notes = self.current_selected_prompt.get('notes', '')
            prompt_content = self.current_selected_prompt.get('prompt', '')

            self.lbl_detail_title.setText(f"<span style='font-size:14px; font-weight:bold;'>{title}</span>")
            
            info_text = f"<b>分类:</b> {category} &nbsp;&nbsp;|&nbsp;&nbsp; <b>标签:</b> {tags}"
            if notes:
                info_text += f" &nbsp;&nbsp;|&nbsp;&nbsp; <b>备注:</b> {notes}"
            self.lbl_detail_info.setText(info_text)

            self.text_preview.setPlainText(prompt_content)

    def copy_to_clipboard(self):
        if not self.current_selected_prompt:
            QMessageBox.warning(self, "提示", "未选中任何 Prompt！")
            return

        clipboard = QApplication.clipboard()
        prompt_content = self.current_selected_prompt.get("prompt", "")
        clipboard.setText(prompt_content)
        QMessageBox.information(self, "成功", "Prompt 内容已复制到剪贴板！")

    def add_prompt(self):
        dialog = PromptEditDialog(self, categories=self.categories)
        if dialog.exec_() == QDialog.Accepted:
            data = dialog.get_data()
            if not data["title"] or not data["prompt"].strip():
                QMessageBox.warning(self, "错误", "标题和 Prompt 内容不能为空！")
                return
            
            if data["category"] not in self.categories:
                self.categories.append(data["category"])

            self.prompts.insert(0, data)
            self.save_data()
            self.refresh_all()

    def edit_prompt(self):
        if not self.current_selected_prompt:
            QMessageBox.warning(self, "提示", "请先选择要编辑的 Prompt！")
            return

        dialog = PromptEditDialog(self, categories=self.categories, prompt_data=self.current_selected_prompt)
        if dialog.exec_() == QDialog.Accepted:
            updated_data = dialog.get_data()
            if not updated_data["title"] or not updated_data["prompt"].strip():
                QMessageBox.warning(self, "错误", "标题和 Prompt 内容不能为空！")
                return

            if updated_data["category"] not in self.categories:
                self.categories.append(updated_data["category"])

            for idx, p in enumerate(self.prompts):
                if p["id"] == updated_data["id"]:
                    self.prompts[idx] = updated_data
                    break

            self.save_data()
            self.refresh_all()

    def delete_prompt(self):
        if not self.current_selected_prompt:
            QMessageBox.warning(self, "提示", "请先选择要删除的 Prompt！")
            return

        reply = QMessageBox.question(
            self, "确认删除", 
            f"确定要删除 Prompt '{self.current_selected_prompt.get('title')}' 吗？",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            target_id = self.current_selected_prompt["id"]
            self.prompts = [p for p in self.prompts if p["id"] != target_id]
            self.save_data()
            self.refresh_all()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = PromptManagerApp()
    window.show()
    sys.exit(app.exec_())