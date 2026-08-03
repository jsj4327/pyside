# -*- coding:utf-8 -*-
import sys
import os
import json
import platform
import datetime

from PySide2.QtWidgets import (
    QApplication, QWidget, QLabel, QTextEdit, QLineEdit, QPushButton,
    QComboBox, QListWidget, QListWidgetItem, QVBoxLayout, QHBoxLayout,
    QMessageBox, QSplitter, QGridLayout, QShortcut, QTabWidget,
    QMainWindow, QStatusBar, QMenu, QAction, QFrame
)
from PySide2.QtCore import Qt, Signal
from PySide2.QtGui import QKeySequence, QFont, QCursor

ISSUE_DIR = "debug_issues"
TEMPLATE_FILE = "prompt_template.md"
LABEL_WIDTH = 45

DEFAULT_TEMPLATE = """## 🐛 问题分析请求

### 上下文信息
- **所属模块**: `{modules}`
- **问题类型**: {type}
- **严重等级**: {level}
- **运行环境**: {environment}

### 问题标题
{title}

### 详细描述
{description}

### 标签
{tags}

---
请作为一名高级软件工程师，按以下结构输出分析结果：
1. **根因分析**：问题产生的根本原因是什么？
2. **修复方案**：具体的代码修改或架构调整建议
3. **涉及文件**：列出可能需要修改的文件清单
4. **风险评估**：本次修改可能带来的副作用或影响范围
5. **测试方案**：如何验证修复有效且未引入新问题
"""


class IssueManager:
    def __init__(self):
        if not os.path.exists(ISSUE_DIR):
            os.makedirs(ISSUE_DIR)

    def save(self, data):
        filename = datetime.datetime.now().strftime("issue_%Y%m%d_%H%M%S.json")
        path = os.path.join(ISSUE_DIR, filename)
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return path
        except Exception as e:
            print(f"Save Error: {e}")
            return None

    def overwrite(self, filepath, data):
        """覆盖已有文件（编辑保存）"""
        if not os.path.exists(filepath):
            return False
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"Overwrite Error: {e}")
            return False

    def delete(self, filepath):
        try:
            if os.path.exists(filepath):
                os.remove(filepath)
                return True
        except Exception as e:
            print(f"Delete Error: {e}")
        return False

    def load_all(self):
        result = []
        if not os.path.exists(ISSUE_DIR):
            return result
        for filename in os.listdir(ISSUE_DIR):
            if not filename.endswith(".json"):
                continue
            path = os.path.join(ISSUE_DIR, filename)
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    data["_filepath"] = path
                    result.append(data)
            except Exception as e:
                print(f"Load Error [{filename}]: {e}")
        return sorted(result, key=lambda x: x.get("time", ""), reverse=True)


class TemplateManager:
    @staticmethod
    def load():
        if os.path.exists(TEMPLATE_FILE):
            try:
                with open(TEMPLATE_FILE, "r", encoding="utf-8") as f:
                    return f.read()
            except Exception:
                pass
        return DEFAULT_TEMPLATE

    @staticmethod
    def save(content):
        try:
            with open(TEMPLATE_FILE, "w", encoding="utf-8") as f:
                f.write(content)
        except Exception as e:
            print(f"Template Save Error: {e}")


class BugNoteTab(QWidget):
    """✅ 独立封装的 BugNote 功能面板，可嵌入任意 Tab"""
    status_message = Signal(str)  # 向主窗口状态栏发送消息

    def __init__(self, parent=None):
        super().__init__(parent)
        self.manager = IssueManager()
        self.template_mgr = TemplateManager()
        self.current_image = None
        self.is_loading = False
        self._all_issues = []  # 缓存全量数据用于搜索过滤
        self.edit_file_path = None  # 当前正在编辑的记录路径（选中历史条目时赋值）
        self.init_ui()
        self.bind_signals()
        self.load_issue_list()
        self.update_prompt_preview()

    def init_ui(self):
        # --- 输入控件 ---
        self.title = QLineEdit()
        self.title.setPlaceholderText("简明扼要的问题标题...")
        self.description = QTextEdit()
        self.description.setPlaceholderText("详细描述复现步骤、预期结果与实际结果...")
        self.description.setMinimumHeight(120)
        self.tag = QLineEdit()
        self.tag.setPlaceholderText("标签 (逗号分隔, 如: AI,UI,Database)")
        self.type_box = QComboBox()
        self.type_box.addItems(["Bug", "优化", "新功能", "疑问", "重构"])
        self.level_box = QComboBox()
        self.level_box.addItems(["Low", "Medium", "High", "Critical"])

        # --- 模块多选 ---
        self.module_list = QListWidget()
        self.module_list.setSelectionMode(QListWidget.MultiSelection)
        self.module_list.setMaximumHeight(90)
        self.module_list.setFlow(QListWidget.LeftToRight)
        self.module_list.setWrapping(True)
        for m in ["agent", "workspace", "bridge", "shell", "database", "ui", "other"]:
            self.module_list.addItem(m)

        btn_mod_layout = QHBoxLayout()
        btn_sa = QPushButton("全选"); btn_sa.setFixedWidth(50)
        btn_cl = QPushButton("清除"); btn_cl.setFixedWidth(50)
        btn_sa.clicked.connect(lambda: self.module_list.selectAll())
        btn_cl.clicked.connect(lambda: self.module_list.clearSelection())
        btn_mod_layout.addWidget(btn_sa); btn_mod_layout.addWidget(btn_cl); btn_mod_layout.addStretch()

        # --- 操作按钮：新增提交按钮 ---
        self.save_button = QPushButton("💾 保存修改 (Ctrl+S)")
        self.save_button.setStyleSheet("""
            QPushButton { background-color: #4CAF50; color: white; font-weight: bold; 
                          padding: 6px 15px; border-radius: 4px; }
            QPushButton:hover { background-color: #45a049; }""")
        self.save_button.clicked.connect(self.save_edit_issue)

        self.submit_button = QPushButton("✅ 提交新建 (Ctrl+Enter)")
        self.submit_button.setStyleSheet("""
            QPushButton { background-color: #3B82F6; color: white; font-weight: bold; 
                          padding: 6px 15px; border-radius: 4px; }
            QPushButton:hover { background-color: #2563EB; }""")
        self.submit_button.clicked.connect(self.submit_new_issue)

        self.prompt_button = QPushButton("📋 复制 Prompt (Ctrl+Shift+C)")
        self.prompt_button.setStyleSheet("padding: 6px 15px;")
        self.prompt_button.clicked.connect(self.copy_prompt)

        # --- 预览区 ---
        self.prompt_preview = QTextEdit()
        self.prompt_preview.setReadOnly(True)
        self.prompt_preview.setStyleSheet("""
            QTextEdit { background-color: #FAFAFA; color: #2E2E2E; 
                font-family: 'Consolas','Monaco','Microsoft YaHei',monospace; font-size: 13px; 
                border: 1px solid #D0D0D0; border-radius: 4px; padding: 8px;
                selection-background-color: #B3D7FF; selection-color: #000; }""")

        # ✅ --- 历史列表 + 搜索框 ---
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("🔍 搜索历史记录...")
        self.search_box.setClearButtonEnabled(True)
        self.issue_list = QListWidget()
        self.issue_list.setAlternatingRowColors(True)
        self.issue_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.issue_list.customContextMenuRequested.connect(self.show_context_menu)
        self.issue_list.itemClicked.connect(self.show_issue)

        # ✅ --- 模板编辑器 + 变量提示 ---
        tpl_hint = QLabel("<span style='color:#888;font-size:11px'>"
                          "可用变量: <code>{modules}</code> <code>{type}</code> <code>{level}</code> "
                          "<code>{environment}</code> <code>{title}</code> <code>{description}</code> <code>{tags}</code>"
                          "</span>")
        tpl_hint.setWordWrap(True)
        self.template_editor = QTextEdit()
        self.template_editor.setPlaceholderText("在此编辑 AI Prompt 模板...")
        self.template_editor.setStyleSheet("""
            QTextEdit { background-color: #FFF9E6; color: #333; font-size: 12px; 
                border: 1px solid #E0D5A0; border-radius: 4px; padding: 6px; }""")
        self.template_editor.setText(self.template_mgr.load())

        btn_tpl_layout = QHBoxLayout()
        btn_reset_tpl = QPushButton("🔄 恢复默认模板")
        btn_reset_tpl.setStyleSheet("font-size: 11px; padding: 3px 10px;")
        btn_reset_tpl.clicked.connect(self.reset_template)
        btn_tpl_layout.addStretch()
        btn_tpl_layout.addWidget(btn_reset_tpl)

        # ================= 布局编排 =================
        main_splitter = QSplitter(Qt.Horizontal)

        # 左侧：搜索 + 历史 + 模板（垂直分割）
        left_splitter = QSplitter(Qt.Vertical)

        left_top = QWidget()
        lt_layout = QVBoxLayout(left_top)
        lt_layout.setContentsMargins(0, 0, 0, 0)
        lt_layout.setSpacing(4)
        lt_layout.addWidget(QLabel("<b>📜 历史记录</b>"))
        lt_layout.addWidget(self.search_box)
        lt_layout.addWidget(self.issue_list)

        left_bottom = QWidget()
        lb_layout = QVBoxLayout(left_bottom)
        lb_layout.setContentsMargins(0, 0, 0, 0)
        lb_layout.setSpacing(2)
        lb_layout.addWidget(QLabel("<b>✏️ Prompt 模板</b>"))
        lb_layout.addWidget(tpl_hint)
        lb_layout.addWidget(self.template_editor)
        lb_layout.addLayout(btn_tpl_layout)

        left_splitter.addWidget(left_top)
        left_splitter.addWidget(left_bottom)
        left_splitter.setStretchFactor(0, 2)
        left_splitter.setStretchFactor(1, 1)

        # 中间编辑面板
        center_widget = QWidget()
        cl = QGridLayout(center_widget)
        cl.setContentsMargins(5, 0, 5, 0)
        cl.setHorizontalSpacing(10); cl.setVerticalSpacing(8)

        def mk_lbl(t):
            l = QLabel(t); l.setFixedWidth(LABEL_WIDTH); return l

        cl.addWidget(mk_lbl("标题:"), 0, 0); cl.addWidget(self.title, 0, 1, 1, 3)
        cl.addWidget(mk_lbl("描述:"), 1, 0, Qt.AlignTop); cl.addWidget(self.description, 1, 1, 1, 3)
        cl.addWidget(mk_lbl("类型:"), 2, 0); cl.addWidget(self.type_box, 2, 1)
        cl.addWidget(mk_lbl("等级:"), 2, 2); cl.addWidget(self.level_box, 2, 3)
        cl.addWidget(mk_lbl("模块:"), 3, 0, Qt.AlignTop)
        mc = QWidget(); mv = QVBoxLayout(mc); mv.setContentsMargins(0, 0, 0, 0); mv.setSpacing(2)
        mv.addWidget(self.module_list); mv.addLayout(btn_mod_layout)
        cl.addWidget(mc, 3, 1, 1, 3)
        cl.addWidget(mk_lbl("标签:"), 4, 0); cl.addWidget(self.tag, 4, 1, 1, 3)
        # 按钮行：保存 + 提交 + 复制prompt
        al = QHBoxLayout()
        al.addStretch()
        al.addWidget(self.save_button)
        al.addWidget(self.submit_button)
        al.addWidget(self.prompt_button)
        cl.addLayout(al, 5, 0, 1, 4)
        cl.setRowStretch(1, 1)

        # 右侧预览
        right_widget = QWidget()
        rl = QVBoxLayout(right_widget); rl.setContentsMargins(0, 0, 0, 0)
        rl.addWidget(QLabel("<b>🤖 AI Prompt 实时预览</b>"))
        rl.addWidget(self.prompt_preview)

        main_splitter.addWidget(left_splitter)
        main_splitter.addWidget(center_widget)
        main_splitter.addWidget(right_widget)
        main_splitter.setStretchFactor(0, 1)
        main_splitter.setStretchFactor(1, 2)
        main_splitter.setStretchFactor(2, 2)
        main_splitter.setSizes([240, 400, 400])

        ml = QHBoxLayout(self); ml.setContentsMargins(8, 8, 8, 8); ml.addWidget(main_splitter)

        # 快捷键
        QShortcut(QKeySequence("Ctrl+S"), self, self.save_edit_issue)
        QShortcut(QKeySequence("Ctrl+Enter"), self, self.submit_new_issue)
        QShortcut(QKeySequence("Ctrl+Shift+C"), self, self.copy_prompt)
        QShortcut(QKeySequence.Delete, self, self.delete_selected_issue)

    def bind_signals(self):
        self.title.textChanged.connect(self.update_prompt_preview)
        self.description.textChanged.connect(self.update_prompt_preview)
        self.tag.textChanged.connect(self.update_prompt_preview)
        self.type_box.currentTextChanged.connect(self.update_prompt_preview)
        self.level_box.currentTextChanged.connect(self.update_prompt_preview)
        self.module_list.itemSelectionChanged.connect(self.update_prompt_preview)
        self.template_editor.textChanged.connect(self._on_template_changed)
        self.search_box.textChanged.connect(self.filter_issue_list)

    def _on_template_changed(self):
        if self.is_loading:
            return
        TemplateManager.save(self.template_editor.toPlainText())
        self.update_prompt_preview()

    def reset_template(self):
        reply = QMessageBox.question(
            self, "确认重置", "确定要恢复默认 Prompt 模板吗？\n当前自定义内容将被覆盖。",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.is_loading = True
            self.template_editor.setText(DEFAULT_TEMPLATE)
            self.is_loading = False
            TemplateManager.save(DEFAULT_TEMPLATE)
            self.update_prompt_preview()
            self.status_message.emit("✅ 已恢复默认 Prompt 模板")

    # ✅ 搜索过滤
    def filter_issue_list(self, keyword):
        keyword = keyword.strip().lower()
        self.issue_list.clear()
        for item in self._all_issues:
            if not keyword:
                match = True
            else:
                title = item.get("title", "").lower()
                tags = item.get("tag", "").lower()
                desc = item.get("description", "").lower()
                match = keyword in title or keyword in tags or keyword in desc
            if match:
                ts = item.get("time", "")[:16].replace("T", " ")
                li = QListWidgetItem(f"[{ts}] {item.get('title', '无标题')}")
                li.setData(Qt.UserRole, item.get("_filepath"))
                li.setToolTip(item.get("description", "")[:200])
                self.issue_list.addItem(li)

    # ✅ 右键菜单 & 删除
    def show_context_menu(self, pos):
        item = self.issue_list.itemAt(pos)
        if not item:
            return
        menu = QMenu(self)
        act_load = QAction("📂 加载到编辑器", self)
        act_del = QAction("🗑️ 删除此记录", self)
        act_load.triggered.connect(lambda: self.show_issue(item))
        act_del.triggered.connect(lambda: self.delete_issue_by_item(item))
        menu.addAction(act_load)
        menu.addSeparator()
        menu.addAction(act_del)
        menu.exec_(QCursor.pos())

    def delete_selected_issue(self):
        item = self.issue_list.currentItem()
        if item:
            self.delete_issue_by_item(item)

    def delete_issue_by_item(self, item):
        fp = item.data(Qt.UserRole)
        if not fp:
            return
        reply = QMessageBox.question(
            self, "确认删除", f"确定要删除这条记录吗？\n{os.path.basename(fp)}",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            if self.manager.delete(fp):
                # 如果删除的是当前编辑条目，清空编辑标记
                if self.edit_file_path == fp:
                    self.edit_file_path = None
                self.status_message.emit(f"🗑️ 已删除: {os.path.basename(fp)}")
                self.load_issue_list()
            else:
                self.status_message.emit("❌ 删除失败")

    def get_selected_modules(self):
        return [item.text() for item in self.module_list.selectedItems()]

    def set_selected_modules(self, names):
        self.module_list.clearSelection()
        for i in range(self.module_list.count()):
            it = self.module_list.item(i)
            if it.text() in names:
                it.setSelected(True)

    def environment_info(self):
        return {
            "OS": f"{platform.system()} {platform.release()}",
            "Python": platform.python_version(),
            "Time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

    def generate_prompt(self):
        template = self.template_editor.toPlainText()
        modules = self.get_selected_modules()
        try:
            return template.format(
                modules=", ".join(modules) if modules else "未指定",
                type=self.type_box.currentText(),
                level=self.level_box.currentText(),
                environment=json.dumps(self.environment_info(), ensure_ascii=False),
                title=self.title.text() or "(未填写标题)",
                description=self.description.toPlainText() or "(未填写描述)",
                tags=self.tag.text() or "无"
            )
        except KeyError as e:
            return f"⚠️ 模板变量错误: 缺少 {{{e}}}\n\n支持的变量: {{modules}} {{type}} {{level}} {{environment}} {{title}} {{description}} {{tags}}"
        except Exception as e:
            return f"⚠️ 模板渲染失败: {e}"

    def update_prompt_preview(self):
        if self.is_loading:
            return
        self.prompt_preview.setText(self.generate_prompt())

    def copy_prompt(self):
        text = self.prompt_preview.toPlainText()
        QApplication.clipboard().setText(text)
        self.status_message.emit("📋 AI Prompt 已复制到剪贴板")

    # 【保存修改】覆盖当前加载的历史条目
    def save_edit_issue(self):
        t = self.title.text().strip()
        if not t:
            self.status_message.emit("⚠️ 标题不能为空！")
            self.title.setFocus()
            return
        if not self.edit_file_path or not os.path.exists(self.edit_file_path):
            QMessageBox.information(self, "提示", "当前未加载任何历史记录，无法保存修改，请使用【提交新建】")
            return

        data = {
            "title": t, "description": self.description.toPlainText(),
            "type": self.type_box.currentText(), "level": self.level_box.currentText(),
            "module": self.get_selected_modules(), "tag": self.tag.text(),
            "time": datetime.datetime.now().isoformat(),
            "environment": self.environment_info(), "screenshot": self.current_image
        }
        ok = self.manager.overwrite(self.edit_file_path, data)
        if ok:
            self.status_message.emit(f"✅ 已保存修改: {os.path.basename(self.edit_file_path)}")
            self.load_issue_list()
        else:
            self.status_message.emit("❌ 保存修改失败")

    # 【提交新建】生成全新独立记录，清空表单
    def submit_new_issue(self):
        t = self.title.text().strip()
        if not t:
            self.status_message.emit("⚠️ 标题不能为空！")
            self.title.setFocus()
            return
        data = {
            "title": t, "description": self.description.toPlainText(),
            "type": self.type_box.currentText(), "level": self.level_box.currentText(),
            "module": self.get_selected_modules(), "tag": self.tag.text(),
            "time": datetime.datetime.now().isoformat(),
            "environment": self.environment_info(), "screenshot": self.current_image
        }
        path = self.manager.save(data)
        if path:
            self.status_message.emit(f"✅ 提交成功，新建记录: {os.path.basename(path)}")
            self.load_issue_list()
            self.clear_form()
        else:
            self.status_message.emit("❌ 提交失败，请检查磁盘权限")

    def clear_form(self):
        self.is_loading = True
        self.title.clear(); self.description.clear(); self.tag.clear()
        self.type_box.setCurrentIndex(0); self.level_box.setCurrentIndex(0)
        self.module_list.clearSelection()
        self.edit_file_path = None  # 清空编辑标记
        self.is_loading = False
        self.update_prompt_preview()

    def load_issue_list(self):
        self._all_issues = self.manager.load_all()
        current_keyword = self.search_box.text().strip()
        self.filter_issue_list(current_keyword)

    def show_issue(self, item):
        fp = item.data(Qt.UserRole)
        if not fp or not os.path.exists(fp):
            self.status_message.emit("⚠️ 文件不存在或已被移动")
            return
        try:
            with open(fp, 'r', encoding='utf-8') as f:
                data = json.load(f)
            self.is_loading = True
            self.edit_file_path = fp  # 标记当前编辑文件
            self.title.setText(data.get("title", ""))
            self.description.setText(data.get("description", ""))
            self.tag.setText(data.get("tag", ""))
            idx = self.type_box.findText(data.get("type", ""))
            if idx >= 0: self.type_box.setCurrentIndex(idx)
            idx = self.level_box.findText(data.get("level", ""))
            if idx >= 0: self.level_box.setCurrentIndex(idx)
            mods = data.get("module", [])
            if isinstance(mods, str):
                mods = [m.strip() for m in mods.split(",") if m.strip()]
            self.set_selected_modules(mods)
            self.is_loading = False
            self.update_prompt_preview()
            self.status_message.emit(f"📂 已加载编辑: {data.get('title', '')}")
        except Exception as e:
            self.status_message.emit(f"❌ 加载失败: {e}")


class MainWindow(QMainWindow):
    """✅ 顶层主窗口：Tab 容器 + 状态栏 + 全局窗口尺寸控制"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("AI Debug Assistant Pro")
        self.init_ui()
        self._resize_to_available_screen(0.85)

    def _resize_to_available_screen(self, ratio=0.85):
        screen = QApplication.primaryScreen()
        if screen is None:
            self.resize(1280, 800)
            return
        geo = screen.availableGeometry()
        w, h = int(geo.width() * ratio), int(geo.height() * ratio)
        x = geo.x() + (geo.width() - w) // 2
        y = geo.y() + (geo.height() - h) // 2
        self.setGeometry(x, y, w, h)

    def init_ui(self):
        # ✅ Tab 容器
        self.tab_widget = QTabWidget()
        self.tab_widget.setTabsClosable(False)
        self.tab_widget.setMovable(True)

        # Tab 1: BugNote
        self.bugnote_tab = BugNoteTab()
        self.bugnote_tab.status_message.connect(self.show_status)
        self.tab_widget.addTab(self.bugnote_tab, "🐛 Bug Note")

        # ✅ 未来扩展示例（取消注释即可启用）
        # self.knowledge_tab = QWidget()
        # self.tab_widget.addTab(self.knowledge_tab, "📚 知识库")
        # self.chat_tab = QWidget()
        # self.tab_widget.addTab(self.chat_tab, "💬 AI 对话")

        self.setCentralWidget(self.tab_widget)

        # ✅ 状态栏
        self.statusBar().showMessage("就绪")
        self.statusBar().setStyleSheet("QStatusBar { font-size: 12px; color: #555; padding: 2px 8px; }")

    def show_status(self, msg):
        self.statusBar().showMessage(msg, 5000)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setFont(QFont("Microsoft YaHei", 10))

    win = MainWindow()
    win.show()
    sys.exit(app.exec_())