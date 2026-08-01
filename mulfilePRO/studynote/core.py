# -*- coding: utf-8 -*-

from PySide2 import QtGui, QtCore

class PythonHighlighter(QtGui.QSyntaxHighlighter):
    """自定义语法高亮器：实现 Python 关键字高亮"""
    def __init__(self, document):
        super().__init__(document)
        self.highlighting_rules = []

        keyword_format = QtGui.QTextCharFormat()
        keyword_format.setForeground(QtGui.QColor("#0000FF"))
        keyword_format.setFontWeight(QtGui.QFont.Bold)
        
        keywords = [
            r'\bdef\b', r'\bclass\b', r'\bimport\b', r'\bfrom\b', r'\breturn\b',
            r'\bif\b', r'\belif\b', r'\belse\b', r'\bwhile\b', r'\bfor\b', 
            r'\bin\b', r'\bnot\b', r'\band\b', r'\bor\b', r'\bTrue\b', r'\bFalse\b'
        ]
        
        for pattern in keywords:
            rule = (QtCore.QRegExp(pattern), keyword_format)
            self.highlighting_rules.append(rule)

        string_format = QtGui.QTextCharFormat()
        string_format.setForeground(QtGui.QColor("#A31515"))
        self.highlighting_rules.append((QtCore.QRegExp(r'".*?"'), string_format))
        self.highlighting_rules.append((QtCore.QRegExp(r"'.*?'"), string_format))

        comment_format = QtGui.QTextCharFormat()
        comment_format.setForeground(QtGui.QColor("#008000"))
        comment_format.setFontItalic(True)
        self.highlighting_rules.append((QtCore.QRegExp(r'#.*$'), comment_format))

    def highlightBlock(self, text):
        for pattern, fmt in self.highlighting_rules:
            expression = QtCore.QRegExp(pattern)
            index = expression.indexIn(text, 0)
            while index >= 0:
                length = expression.matchedLength()
                self.setFormat(index, length, fmt)
                index = expression.indexIn(text, index + length)


def get_code_block_html():
    return """
    <table style="width:100%; background-color: #f4f4f4; border: 1px solid #ddd; border-radius: 4px;">
        <tr>
            <td style="padding: 10px; font-family: Consolas, Courier, monospace; font-size: 13px; color: #333;">
                # 输入你的代码<br>
                def main():<br>
                &nbsp;&nbsp;&nbsp;&nbsp;print("Hello, Note!")
            </td>
        </tr>
    </table>
    <p></p>
    """


LIGHT_STYLE = """
QMainWindow { background-color: #f7f9fa; }
QWidget { background-color: #ffffff; color: #333333; font-family: "Microsoft YaHei", sans-serif; }
QListWidget, QTreeWidget { background-color: #f3f4f6; border: none; alternate-background-color: #e5e7eb; }
QListWidget::item:selected { background-color: #3b82f6; color: white; border-radius: 4px; }
QTreeWidget::item:selected { background-color: #3b82f6; color: white; border-radius: 4px; }
QLineEdit { border: 1px solid #d1d5db; border-radius: 4px; padding: 4px; background: #ffffff; }
QPushButton { background-color: #f3f4f6; border: 1px solid #d1d5db; border-radius: 4px; padding: 5px 10px; }
QPushButton:hover { background-color: #e5e7eb; }
QTextEdit { border: 1px solid #d1d5db; border-radius: 4px; background: #ffffff; }
"""

DARK_STYLE = """
QMainWindow { background-color: #1e1e1e; }
QWidget { background-color: #1e1e1e; color: #d4d4d4; font-family: "Microsoft YaHei", sans-serif; }
QListWidget, QTreeWidget { background-color: #252526; border: none; color: #d4d4d4; }
QListWidget::item:selected { background-color: #094771; color: white; border-radius: 4px; }
QTreeWidget::item:selected { background-color: #094771; color: white; border-radius: 4px; }
QLineEdit { border: 1px solid #3f3f46; border-radius: 4px; padding: 4px; background: #2d2d2d; color: #d4d4d4; }
QPushButton { background-color: #333333; border: 1px solid #3f3f46; border-radius: 4px; padding: 5px 10px; color: #d4d4d4; }
QPushButton:hover { background-color: #3f3f46; }
QTextEdit { border: 1px solid #3f3f46; border-radius: 4px; background: #1e1e1e; color: #d4d4d4; }
"""