# -*- coding:utf-8 -*-
from PySide2.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTextEdit, QGroupBox, QSplitter,
    QListWidget, QSizePolicy, QTreeWidget, QProgressBar,
    QRadioButton, QButtonGroup, QLineEdit
)
from PySide2.QtCore import Qt, QSettings
from PySide2.QtGui import QFont

from .file_manager import FileManagerWidget
from ..source_viewer.code_editor import CodeEditor


class ProjectCreatorUI:
    """UI 构建器"""

    @staticmethod
    def setup_ui(parent):
        parent.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        layout = QVBoxLayout(parent)
        layout.setContentsMargins(3, 3, 3, 3)
        layout.setSpacing(3)

        main_splitter = QSplitter(Qt.Horizontal)
        main_splitter.setChildrenCollapsible(False)
        main_splitter.setHandleWidth(3)

        left_panel, left_controls = ProjectCreatorUI._create_left_panel()
        main_splitter.addWidget(left_panel)

        middle_panel, mid_controls = ProjectCreatorUI._create_middle_panel()
        main_splitter.addWidget(middle_panel)

        right_panel, right_controls = ProjectCreatorUI._create_right_panel()
        main_splitter.addWidget(right_panel)

        main_splitter.setSizes([180, 350, 370])
        layout.addWidget(main_splitter)

        # 底部状态栏
        bottom_bar = QHBoxLayout()
        bottom_bar.setSpacing(5)

        status_label = QLabel("就绪")
        status_label.setStyleSheet("color:#666;padding:2px 6px;")

        progress_bar = QProgressBar()
        progress_bar.setVisible(False)
        progress_bar.setMaximumHeight(16)
        progress_bar.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)

        bottom_bar.addWidget(status_label)
        bottom_bar.addStretch()
        bottom_bar.addWidget(progress_bar)
        layout.addLayout(bottom_bar)

        return {
            'file_manager': left_controls['file_manager'],
            'upload_group': left_controls['upload_group'],
            'radio_no_upload': left_controls['radio_no_upload'],
            'radio_single_file': left_controls['radio_single_file'],
            'radio_folder': left_controls['radio_folder'],
            'blacklist_input': left_controls['blacklist_input'],
            'desc_edit': mid_controls['desc_edit'],
            'btn_build': mid_controls['btn_build'],
            'btn_improve': mid_controls['btn_improve'],
            'btn_clear': mid_controls['btn_clear'],
            'btn_unblock': mid_controls['btn_unblock'],  # 新增
            'btn_view_build_prompt': mid_controls['btn_view_build_prompt'],
            'btn_view_improve_prompt': mid_controls['btn_view_improve_prompt'],
            'prompt_display': mid_controls['prompt_display'],
            'code_editor': mid_controls['code_editor'],
            'outline_tree': mid_controls['outline_tree'],
            'file_path_display': mid_controls['file_path_display'],
            'btn_run': mid_controls['btn_run'],
            'status_label': status_label,
            'progress_bar': progress_bar,
            'log_text': left_panel.log_text,
            'output_text': right_controls['output_text'],
            'btn_feedback_ai': right_controls['btn_feedback_ai'],
            'btn_view_feedback_prompt': right_controls['btn_view_feedback_prompt'],
            'feedback_list': right_controls['feedback_list'],
            'feedback_content': right_controls['feedback_content'],
            'btn_apply_selected': right_controls['btn_apply_selected'],
            'btn_undo_selected': right_controls['btn_undo_selected'],
            'btn_apply_all': right_controls['btn_apply_all'],
            'btn_undo_all': right_controls['btn_undo_all'],
        }

    @staticmethod
    def _create_left_panel():
        # ...（与之前相同，未改变）...
        panel = QWidget()
        panel.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        title = QLabel("📁 项目文件")
        title.setStyleSheet("font-weight:bold;padding:2px 4px;background:#e8e8e8;border-bottom:1px solid #ccc;")
        title.setFixedHeight(24)
        layout.addWidget(title)

        file_manager = FileManagerWidget()
        file_manager.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout.addWidget(file_manager)

        upload_widget = QWidget()
        upload_widget.setStyleSheet("border:1px solid #ddd; border-radius:3px;")
        upload_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        upload_layout = QHBoxLayout(upload_widget)
        upload_layout.setContentsMargins(6, 3, 6, 3)
        upload_layout.setSpacing(10)

        upload_button_group = QButtonGroup()
        radio_no_upload = QRadioButton("无")
        radio_single_file = QRadioButton("单")
        radio_folder = QRadioButton("多")

        radio_no_upload.setChecked(True)
        upload_button_group.addButton(radio_no_upload, 0)
        upload_button_group.addButton(radio_single_file, 1)
        upload_button_group.addButton(radio_folder, 2)

        upload_layout.addWidget(radio_no_upload)
        upload_layout.addWidget(radio_single_file)
        upload_layout.addWidget(radio_folder)
        upload_layout.addStretch()

        layout.addWidget(upload_widget)

        blacklist_widget = QWidget()
        blacklist_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        blacklist_layout = QHBoxLayout(blacklist_widget)
        blacklist_layout.setContentsMargins(4, 2, 4, 2)
        blacklist_layout.setSpacing(4)

        blacklist_label = QLabel("排除后缀:")
        blacklist_label.setFixedWidth(70)
        blacklist_label.setStyleSheet("font-size:11px;color:#555;")
        blacklist_layout.addWidget(blacklist_label)

        blacklist_input = QLineEdit()
        blacklist_input.setPlaceholderText(".pyc, .log, .tmp")
        blacklist_input.setStyleSheet("font-size:11px;padding:2px 4px;")
        blacklist_input.setToolTip("输入要排除的文件后缀，用逗号或空格分隔")
        blacklist_layout.addWidget(blacklist_input)

        layout.addWidget(blacklist_widget)

        log_group = QGroupBox("📋 日志")
        log_group.setStyleSheet("QGroupBox{margin-top:0px;border:1px solid #ddd;}")
        log_group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        log_layout = QVBoxLayout(log_group)
        log_layout.setContentsMargins(2, 2, 2, 2)
        log_text = QTextEdit()
        log_text.setReadOnly(True)
        log_text.setMaximumHeight(50)
        log_text.setStyleSheet("font-size:10px;background:#f8f8f8;border:none;")
        log_layout.addWidget(log_text)
        layout.addWidget(log_group)

        panel.log_text = log_text

        settings = QSettings("ProjectBuilder", "ProjectCreator")
        blacklist_input.setText(settings.value("blacklist", "", type=str))

        def save_blacklist():
            settings.setValue("blacklist", blacklist_input.text().strip())
            settings.sync()

        blacklist_input.editingFinished.connect(save_blacklist)

        return panel, {
            'file_manager': file_manager,
            'upload_group': upload_button_group,
            'radio_no_upload': radio_no_upload,
            'radio_single_file': radio_single_file,
            'radio_folder': radio_folder,
            'blacklist_input': blacklist_input,
        }

    @staticmethod
    def _create_middle_panel():
        # ...（修改按钮行，增加取消阻塞按钮）...
        panel = QWidget()
        panel.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        top_container = QWidget()
        top_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        top_layout = QVBoxLayout(top_container)
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.setSpacing(2)

        input_group = QGroupBox("📝 项目需求 / 改进意见")
        input_group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        input_layout = QVBoxLayout(input_group)
        input_layout.setContentsMargins(2, 4, 2, 2)
        desc_edit = QTextEdit()
        desc_edit.setMinimumHeight(80)
        desc_edit.setMaximumHeight(120)
        desc_edit.setPlaceholderText(
            "描述您想要创建的项目...\n"
            "示例: 创建一个Python命令行工具，用于批量重命名文件\n\n"
            "或输入改进意见（需先在文件管理器中打开目标文件）\n"
            "示例: 添加日志记录功能"
        )
        input_layout.addWidget(desc_edit)
        top_layout.addWidget(input_group)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(5)

        btn_build = QPushButton("🏗️ 构建")
        btn_build.setStyleSheet(
            "QPushButton{background:#4CAF50;color:#fff;font-weight:bold;padding:4px 12px;border-radius:4px;}"
            "QPushButton:disabled{background:#a5d6a7;}"
        )
        btn_build.setFixedSize(80, 30)

        btn_improve = QPushButton("🔧 改进")
        btn_improve.setStyleSheet(
            "QPushButton{background:#2196F3;color:#fff;font-weight:bold;padding:4px 12px;border-radius:4px;}"
            "QPushButton:disabled{background:#90caf9;}"
        )
        btn_improve.setFixedSize(80, 30)
        btn_improve.setEnabled(False)

        btn_clear = QPushButton("🗑 清空")
        btn_clear.setFixedSize(70, 30)

        btn_unblock = QPushButton("🔓 取消阻塞")
        btn_unblock.setFixedSize(90, 30)
        btn_unblock.setStyleSheet("QPushButton{background:#ff9800;color:#fff;font-weight:bold;border-radius:4px;}")

        btn_view_build_prompt = QPushButton("📄 构建Prompt")
        btn_view_build_prompt.setFixedSize(100, 30)

        btn_view_improve_prompt = QPushButton("📄 改进Prompt")
        btn_view_improve_prompt.setFixedSize(100, 30)
        btn_view_improve_prompt.setEnabled(False)

        btn_row.addWidget(btn_build)
        btn_row.addWidget(btn_improve)
        btn_row.addWidget(btn_clear)
        btn_row.addWidget(btn_unblock)  # 新增
        btn_row.addWidget(btn_view_build_prompt)
        btn_row.addWidget(btn_view_improve_prompt)
        btn_row.addStretch()
        top_layout.addLayout(btn_row)

        prompt_group = QGroupBox("📤 发送给AI的Prompt")
        prompt_group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        prompt_layout = QVBoxLayout(prompt_group)
        prompt_layout.setContentsMargins(2, 4, 2, 2)
        prompt_display = QTextEdit()
        prompt_display.setReadOnly(True)
        prompt_display.setMinimumHeight(60)
        prompt_display.setMaximumHeight(100)
        prompt_display.setStyleSheet("font-family:monospace;font-size:11px;background:#f5f5f5;")
        prompt_display.setPlaceholderText("发送请求后，此处显示完整Prompt...")
        prompt_layout.addWidget(prompt_display)
        top_layout.addWidget(prompt_group)

        layout.addWidget(top_container)

        editor_group = QGroupBox("📄 代码预览/编辑")
        editor_group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        editor_layout = QVBoxLayout(editor_group)
        editor_layout.setContentsMargins(2, 4, 2, 2)
        editor_layout.setSpacing(2)

        editor_toolbar = QHBoxLayout()
        editor_toolbar.setSpacing(4)
        btn_run = QPushButton("▶ 运行")
        btn_run.setEnabled(False)
        btn_run.setFixedSize(70, 26)
        editor_toolbar.addWidget(btn_run)

        file_path_display = QLabel("未打开文件")
        file_path_display.setStyleSheet("color:#666;font-size:11px;padding:0 4px;")
        editor_toolbar.addWidget(file_path_display)
        editor_toolbar.addStretch()
        editor_layout.addLayout(editor_toolbar)

        outline_tree = QTreeWidget()
        outline_tree.setHeaderHidden(True)
        outline_tree.setMaximumHeight(60)
        outline_tree.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        editor_layout.addWidget(outline_tree)

        code_editor = CodeEditor()
        code_editor.setReadOnly(False)
        code_editor.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        editor_layout.addWidget(code_editor)

        layout.addWidget(editor_group)

        return panel, {
            'desc_edit': desc_edit,
            'btn_build': btn_build,
            'btn_improve': btn_improve,
            'btn_clear': btn_clear,
            'btn_unblock': btn_unblock,  # 新增
            'btn_view_build_prompt': btn_view_build_prompt,
            'btn_view_improve_prompt': btn_view_improve_prompt,
            'prompt_display': prompt_display,
            'code_editor': code_editor,
            'outline_tree': outline_tree,
            'file_path_display': file_path_display,
            'btn_run': btn_run,
        }

    @staticmethod
    def _create_right_panel():
        # ...（与之前相同，未改变）...
        panel = QWidget()
        panel.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        debug_group = QGroupBox("🐞 调试输出")
        debug_group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        debug_layout = QVBoxLayout(debug_group)
        debug_layout.setContentsMargins(2, 4, 2, 2)
        debug_layout.setSpacing(2)

        debug_header = QHBoxLayout()
        debug_header.addWidget(QLabel("运行输出"))

        btn_view_feedback_prompt = QPushButton("📄 反馈Prompt")
        btn_view_feedback_prompt.setEnabled(False)
        btn_view_feedback_prompt.setFixedSize(100, 24)

        btn_feedback_ai = QPushButton("🤖 反馈")
        btn_feedback_ai.setEnabled(False)
        btn_feedback_ai.setFixedSize(80, 24)

        debug_header.addStretch()
        debug_header.addWidget(btn_view_feedback_prompt)
        debug_header.addWidget(btn_feedback_ai)
        debug_layout.addLayout(debug_header)

        output_text = QTextEdit()
        output_text.setReadOnly(True)
        output_text.setFont(QFont("Consolas", 10))
        output_text.setPlaceholderText("运行输出将显示在这里...")
        output_text.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        debug_layout.addWidget(output_text)

        layout.addWidget(debug_group)

        feedback_group = QGroupBox("📨 AI反馈与修改记录")
        feedback_group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        feedback_layout = QVBoxLayout(feedback_group)
        feedback_layout.setContentsMargins(2, 4, 2, 2)
        feedback_layout.setSpacing(2)

        feedback_header = QHBoxLayout()
        feedback_header.addWidget(QLabel("修改列表"))
        feedback_header.addStretch()
        btn_apply_selected = QPushButton("✅ 应用")
        btn_apply_selected.setEnabled(False)
        btn_apply_selected.setFixedSize(60, 22)
        btn_undo_selected = QPushButton("↩ 撤销")
        btn_undo_selected.setEnabled(False)
        btn_undo_selected.setFixedSize(60, 22)
        btn_apply_all = QPushButton("全部应用")
        btn_apply_all.setEnabled(False)
        btn_apply_all.setFixedSize(70, 22)
        btn_undo_all = QPushButton("全部撤销")
        btn_undo_all.setEnabled(False)
        btn_undo_all.setFixedSize(70, 22)
        feedback_header.addWidget(btn_apply_selected)
        feedback_header.addWidget(btn_undo_selected)
        feedback_header.addWidget(btn_apply_all)
        feedback_header.addWidget(btn_undo_all)
        feedback_layout.addLayout(feedback_header)

        feedback_list = QListWidget()
        feedback_list.setSelectionMode(QListWidget.SingleSelection)
        feedback_list.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        feedback_layout.addWidget(feedback_list)

        feedback_content = QTextEdit()
        feedback_content.setReadOnly(True)
        feedback_content.setMaximumHeight(100)
        feedback_content.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        feedback_content.setPlaceholderText("点击列表项查看内容...")
        feedback_layout.addWidget(feedback_content)

        layout.addWidget(feedback_group)

        return panel, {
            'output_text': output_text,
            'btn_feedback_ai': btn_feedback_ai,
            'btn_view_feedback_prompt': btn_view_feedback_prompt,
            'feedback_list': feedback_list,
            'feedback_content': feedback_content,
            'btn_apply_selected': btn_apply_selected,
            'btn_undo_selected': btn_undo_selected,
            'btn_apply_all': btn_apply_all,
            'btn_undo_all': btn_undo_all,
        }