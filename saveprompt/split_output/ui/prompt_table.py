"""
分页表格组件
封装表格渲染、分页控件、行选择联动及详情面板更新逻辑。
"""
from PySide2.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QComboBox,
    QGroupBox, QPlainTextEdit, QApplication, QMessageBox
)
from PySide2.QtCore import Qt, Signal
from PySide2.QtGui import QFont

from config import (
    PAGE_SIZE_OPTIONS, DEFAULT_PAGE_SIZE,
    STYLE_BTN_PRIMARY, STYLE_BTN_DANGER,
    STYLE_CODE_FONT, STYLE_CODE_SIZE
)
from services._filter_service import paginate


class PromptTable(QWidget):
    """带分页功能的 Prompt 表格及详情预览面板。"""

    prompt_selected = Signal(dict)
    copy_requested = Signal(dict)
    edit_requested = Signal(dict)
    delete_requested = Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.filtered_prompts = []
        self.current_page = 1
        self.page_size = DEFAULT_PAGE_SIZE
        self.current_selected = None
        self._init_ui()

    def _init_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        splitter_v = QWidget()
        v_layout = QVBoxLayout(splitter_v)
        v_layout.setContentsMargins(0, 0, 0, 0)

        # -- 表格区 --
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["标题", "分类", "标签", "更新时间"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.itemSelectionChanged.connect(self.on_selection_changed)
        v_layout.addWidget(self.table)

        # -- 分页栏 --
        page_bar = QHBoxLayout()
        self.lbl_status = QLabel("共 0 条数据")
        self.btn_prev = QPushButton("< 上一页")
        self.btn_prev.setFixedWidth(80)
        self.btn_prev.clicked.connect(self.prev_page)
        self.lbl_page = QLabel("页次: 1/1")
        self.btn_next = QPushButton("下一页 >")
        self.btn_next.setFixedWidth(80)
        self.btn_next.clicked.connect(self.next_page)

        page_bar.addWidget(self.lbl_status)
        page_bar.addStretch()
        page_bar.addWidget(self.btn_prev)
        page_bar.addWidget(self.lbl_page)
        page_bar.addWidget(self.btn_next)
        page_bar.addWidget(QLabel(" 每页显示:"))

        self.combo_size = QComboBox()
        for s in PAGE_SIZE_OPTIONS:
            self.combo_size.addItem(f"{s} 条", s)
        self.combo_size.currentIndexChanged.connect(self.on_size_changed)
        page_bar.addWidget(self.combo_size)
        v_layout.addLayout(page_bar)

        outer.addWidget(splitter_v, 3)

        # -- 详情面板 --
        detail = QGroupBox("Prompt 详情与预览")
        d_layout = QVBoxLayout(detail)

        self.lbl_title = QLabel("<span style='font-size:14px; font-weight:bold;'>请选择一条 Prompt</span>")
        self.lbl_info = QLabel("<span style='color:#666;'>分类: - | 标签: - | 备注: -</span>")
        d_layout.addWidget(self.lbl_title)
        d_layout.addWidget(self.lbl_info)

        self.preview = QPlainTextEdit()
        self.preview.setFont(QFont(STYLE_CODE_FONT, STYLE_CODE_SIZE))
        self.preview.setReadOnly(True)
        d_layout.addWidget(self.preview)

        btn_row = QHBoxLayout()
        self.btn_copy = QPushButton("一键复制 Prompt")
        self.btn_copy.setFixedHeight(30)
        self.btn_copy.setStyleSheet(STYLE_BTN_PRIMARY)
        self.btn_copy.clicked.connect(self.on_copy)

        self.btn_edit = QPushButton("编辑")
        self.btn_edit.clicked.connect(self.on_edit)

        self.btn_del = QPushButton("删除")
        self.btn_del.setStyleSheet(STYLE_BTN_DANGER)
        self.btn_del.clicked.connect(self.on_delete)

        btn_row.addWidget(self.btn_copy)
        btn_row.addStretch()
        btn_row.addWidget(self.btn_edit)
        btn_row.addWidget(self.btn_del)
        d_layout.addLayout(btn_row)

        outer.addWidget(detail, 2)

    def render(self, filtered: list):
        """接收过滤后的数据并渲染当前页。"""
        self.filtered_prompts = filtered
        chunk, total_pages, self.current_page = paginate(
            filtered, self.current_page, self.page_size
        )

        self.table.setRowCount(0)
        for row, p in enumerate(chunk):
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(p.get("title", "")))
            self.table.setItem(row, 1, QTableWidgetItem(p.get("category", "")))
            self.table.setItem(row, 2, QTableWidgetItem(p.get("tags", "")))
            self.table.setItem(row, 3, QTableWidgetItem(p.get("updated_at", "")))

        self.lbl_status.setText(f"共 <b>{len(filtered)}</b> 条数据")
        self.lbl_page.setText(f"页次: <b>{self.current_page}</b> / {total_pages}")
        self.btn_prev.setEnabled(self.current_page > 1)
        self.btn_next.setEnabled(self.current_page < total_pages)

        if chunk:
            self.table.selectRow(0)
        else:
            self.clear_detail()

    def clear_detail(self):
        self.current_selected = None
        self.lbl_title.setText("<span style='font-size:14px; font-weight:bold;'>无匹配数据</span>")
        self.lbl_info.setText("<span style='color:#666;'>分类: - | 标签: - | 备注: -</span>")
        self.preview.clear()

    # ---- 事件处理 ----
    def on_selection_changed(self):
        rows = self.table.selectionModel().selectedRows()
        if not rows:
            self.clear_detail()
            return
        idx = (self.current_page - 1) * self.page_size + rows[0].row()
        if 0 <= idx < len(self.filtered_prompts):
            p = self.filtered_prompts[idx]
            self.current_selected = p
            self.lbl_title.setText(f"<span style='font-size:14px; font-weight:bold;'>{p.get('title','')}</span>")
            info = f"<b>分类:</b> {p.get('category','')} &nbsp;|&nbsp; <b>标签:</b> {p.get('tags','')}"
            if p.get("notes"):
                info += f" &nbsp;|&nbsp; <b>备注:</b> {p['notes']}"
            self.lbl_info.setText(info)
            self.preview.setPlainText(p.get("prompt", ""))
            self.prompt_selected.emit(p)

    def prev_page(self):
        if self.current_page > 1:
            self.current_page -= 1
            self.render(self.filtered_prompts)

    def next_page(self):
        self.current_page += 1
        self.render(self.filtered_prompts)

    def on_size_changed(self, index):
        self.page_size = self.combo_size.currentData()
        self.current_page = 1
        self.render(self.filtered_prompts)

    def on_copy(self):
        if self.current_selected:
            self.copy_requested.emit(self.current_selected)

    def on_edit(self):
        if self.current_selected:
            self.edit_requested.emit(self.current_selected)
        else:
            QMessageBox.warning(self, "提示", "请先选择要编辑的 Prompt！")

    def on_delete(self):
        if self.current_selected:
            self.delete_requested.emit(self.current_selected)
        else:
            QMessageBox.warning(self, "提示", "请先选择要删除的 Prompt！")
