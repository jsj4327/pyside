"""
符号解析器：使用正则表达式提取多种常见语言的类和方法/函数结构
"""

import re
from typing import List, Tuple

class SymbolParser:
    """多语言类与方法解析器"""

    @staticmethod
    def parse_symbols(content: str, file_extension: str) -> List[Tuple[str, str, int]]:
        """
        解析源码中的符号
        返回格式: [(symbol_type, symbol_name, line_number), ...]
        symbol_type: 'class' 或 'method'
        """
        symbols = []
        lines = content.splitlines()
        ext = file_extension.lower()

        # 根据不同文件后缀选择匹配策略
        if ext in ['.py']:
            # Python 类和函数定义
            class_pattern = re.compile(r'^(\s*)class\s+(\w+)')
            method_pattern = re.compile(r'^(\s*)def\s+(\w+)\s*\(')

            for idx, line in enumerate(lines):
                c_match = class_pattern.match(line)
                if c_match:
                    symbols.append(('class', c_match.group(2), idx + 1))
                    continue
                m_match = method_pattern.match(line)
                if m_match:
                    symbols.append(('method', m_match.group(2), idx + 1))

        elif ext in ['.cpp', '.cc', '.cxx', '.h', '.hpp', '.c', '.java', '.js', '.ts', '.cs']:
            # C++/Java/JS 类及常见函数大括号定义
            class_pattern = re.compile(r'\b(class|struct|interface)\s+(\w+)')
            method_pattern = re.compile(r'\b([a-zA-Z_]\w*\s+)+([a-zA-Z_]\w*)\s*\([^;]*\)\s*\{?')

            for idx, line in enumerate(lines):
                if any(kw in line for kw in ['if', 'for', 'while', 'switch', 'return', 'sizeof']):
                    continue
                c_match = class_pattern.search(line)
                if c_match:
                    symbols.append(('class', c_match.group(2), idx + 1))
                    continue
                m_match = method_pattern.search(line)
                if m_match:
                    func_name = m_match.group(2)
                    if func_name not in ['if', 'for', 'while', 'switch', 'return']:
                        symbols.append(('method', func_name, idx + 1))

        return symbols