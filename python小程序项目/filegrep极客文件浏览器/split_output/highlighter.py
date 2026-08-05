"""
代码语法高亮器模块
为QTextEdit提供C/C++和Python关键字的语法高亮功能。
"""
from PySide2.QtGui import QSyntaxHighlighter, QTextCharFormat, QColor, QFont
from PySide2.QtCore import QRegExp
from typing import List, Tuple, Optional


class CodeHighlighter(QSyntaxHighlighter):
    """
    代码语法高亮器
    支持C/C++和Python关键字、数字、字符串、注释的高亮显示，
    以及搜索关键字的背景高亮。
    """

    # C/C++ 和 Python 关键字列表
    KEYWORDS = [
        "char", "class", "const", "double", "enum", "explicit", "friend",
        "inline", "int", "long", "namespace", "operator", "private",
        "protected", "public", "short", "signed", "static", "struct",
        "template", "this", "typedef", "typename", "union", "unsigned",
        "virtual", "void", "def", "import", "from", "if", "else",
        "elif", "return", "for", "while", "try", "except"
    ]

    def __init__(self, parent=None, search_keyword: str = ""):
        """
        初始化语法高亮器。
        
        Args:
            parent: 父级QTextDocument对象
            search_keyword: 需要额外高亮的搜索关键字
        """
        super().__init__(parent)
        self.highlighting_rules: List[Tuple[QRegExp, QTextCharFormat]] = []
        self._setup_highlighting_rules(search_keyword)

    def _create_format(self, color: str, bold: bool = False, italic: bool = False) -> QTextCharFormat:
        """
        创建文本格式对象。
        
        Args:
            color: 前景色（十六进制颜色字符串）
            bold: 是否加粗
            italic: 是否斜体
            
        Returns:
            QTextCharFormat: 配置好的文本格式
        """
        fmt = QTextCharFormat()
        fmt.setForeground(QColor(color))
        if bold:
            fmt.setFontWeight(QFont.Bold)
        if italic:
            fmt.setFontItalic(True)
        return fmt

    def _setup_highlighting_rules(self, search_keyword: str) -> None:
        """
        配置所有高亮规则。
        
        Args:
            search_keyword: 搜索关键字（可选）
        """
        # 关键字高亮规则
        keyword_format = self._create_format("#0056b3", bold=True)
        for word in self.KEYWORDS:
            pattern = rf"\b{word}\b"
            self.highlighting_rules.append((QRegExp(pattern), keyword_format))

        # 数字高亮规则
        number_format = self._create_format("#D35400")
        self.highlighting_rules.append(
            (QRegExp(r"\b[0-9]+L?\b"), number_format)
        )

        # 字符串高亮规则（双引号和单引号）
        string_format = self._create_format("#A31515")
        self.highlighting_rules.append((QRegExp(r'".*"'), string_format))
        self.highlighting_rules.append((QRegExp(r"'.*'"), string_format))

        # 注释高亮规则（C风格 // 和 Python风格 #）
        comment_format = self._create_format("#008000", italic=True)
        self.highlighting_rules.append((QRegExp(r"//[^\n]*"), comment_format))
        self.highlighting_rules.append((QRegExp(r"#[^\n]*"), comment_format))

        # 搜索关键字高亮规则
        if search_keyword:
            search_format = QTextCharFormat()
            search_format.setBackground(QColor("#FFF176"))
            search_format.setForeground(QColor("#000000"))
            search_format.setFontWeight(QFont.Bold)
            escaped_keyword = QRegExp.escape(search_keyword)
            self.highlighting_rules.append((QRegExp(escaped_keyword), search_format))

    def highlightBlock(self, text: str) -> None:
        """
        对文本块应用高亮规则。
        由QSyntaxHighlighter框架自动调用。
        
        Args:
            text: 当前文本块的内容
        """
        for pattern, fmt in self.highlighting_rules:
            expression = QRegExp(pattern)
            index = expression.indexIn(text)
            while index >= 0:
                length = expression.matchedLength()
                self.setFormat(index, length, fmt)
                index = expression.indexIn(text, index + length)
