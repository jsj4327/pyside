# -*- coding: utf-8 -*-

from PySide2 import QtWidgets, QtGui, QtCore

class CurrentLineHighlighter:
    """文本编辑器当前活动行高亮辅助类"""
    def __init__(self, text_edit: QtWidgets.QTextEdit, is_dark=False):
        self.text_edit = text_edit
        self.is_dark = is_dark
        self.text_edit.cursorPositionChanged.connect(self.highlight_current_line)
        self.highlight_current_line()

    def highlight_current_line(self):
        extra_selections = []
        if not self.text_edit.isReadOnly():
            selection = QtWidgets.QTextEdit.ExtraSelection()
            line_color = QtGui.QColor("#1e293b" if self.is_dark else "#f1f5f9")
            selection.format.setBackground(line_color)
            selection.format.setProperty(QtGui.QTextFormat.FullWidthSelection, True)
            selection.cursor = self.text_edit.textCursor()
            selection.cursor.clearSelection()
            extra_selections.append(selection)
        self.text_edit.setExtraSelections(extra_selections)

    def update_theme(self, is_dark):
        self.is_dark = is_dark
        self.highlight_current_line()


def get_modern_scrollbar_style(is_dark=False):
    """获取现代纤细圆角滚动条与微交互及卡片化块级元素 QSS 样式"""
    if is_dark:
        bg_color = "#0f172a"
        handle_color = "#334155"
        handle_hover_color = "#475569"
        block_bg = "#1e293b"
        block_border = "#3b82f6"
        code_bg = "#090d16"
        text_color = "#e2e8f0"
    else:
        bg_color = "#f8fafc"
        handle_color = "#cbd5e1"
        handle_hover_color = "#94a3b8"
        block_bg = "#f1f5f9"
        block_border = "#3b82f6"
        code_bg = "#f8fafc"
        text_color = "#1e293b"

    return f"""
        QScrollBar:vertical {{
            background: {bg_color};
            width: 8px;
            margin: 0px;
            border-radius: 4px;
        }}
        QScrollBar::handle:vertical {{
            background: {handle_color};
            min-height: 20px;
            border-radius: 4px;
        }}
        QScrollBar::handle:vertical:hover {{
            background: {handle_hover_color};
        }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0px; }}
        QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: none; }}

        QScrollBar:horizontal {{
            background: {bg_color};
            height: 8px;
            margin: 0px;
            border-radius: 4px;
        }}
        QScrollBar::handle:horizontal {{
            background: {handle_color};
            min-width: 20px;
            border-radius: 4px;
        }}
        QScrollBar::handle:horizontal:hover {{
            background: {handle_hover_color};
        }}
        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0px; }}
        QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{ background: none; }}

        QLineEdit, QTextEdit {{
            selection-background-color: #3b82f6;
            selection-color: #ffffff;
            color: {text_color};
        }}
        
        QLineEdit:focus {{
            border: 1px solid #3b82f6;
        }}

        QTextEdit blockquote {{
            background-color: {block_bg};
            border-left: 4px solid {block_border};
            margin: 10px 0px;
            padding: 8px 12px;
            border-radius: 0px 6px 6px 0px;
        }}

        QTextEdit pre, QTextEdit code {{
            background-color: {code_bg};
            border: 1px solid {handle_color};
            border-radius: 6px;
            padding: 6px;
            font-family: 'JetBrains Mono', 'Fira Code', 'Consolas', monospace;
        }}
    """