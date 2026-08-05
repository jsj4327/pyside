# -*- coding:utf-8 -*-
import re
from typing import List, Tuple


class SymbolParser:
    @staticmethod
    def parse_symbols(content: str, ext: str) -> List[Tuple[str, str, int]]:
        symbols = []
        lines = content.splitlines()
        ext_lower = ext.lower()
        if ext_lower in ['.py']:
            class_pattern = re.compile(r'^(\s*)class\s+(\w+)')
            method_pattern = re.compile(r'^(\s*)def\s+(\w+)\s*\(')
            for idx, line in enumerate(lines):
                c_match = class_pattern.match(line)
                if c_match:
                    symbols.append(('class', c_match.group(2), idx + 1))
                m_match = method_pattern.match(line)
                if m_match:
                    symbols.append(('method', m_match.group(2), idx + 1))
        elif ext_lower in ['.cpp', '.c', '.h', '.hpp', '.java', '.js', '.ts', '.cs']:
            class_pattern = re.compile(r'\b(class|struct|interface)\s+(\w+)')
            method_pattern = re.compile(r'\b([a-zA-Z_]\w*\s+)+([a-zA-Z_]\w*)\s*\([^;]*\)\s*\{?')
            for idx, line in enumerate(lines):
                if any(kw in line for kw in ['if', 'for', 'while', 'switch', 'return', 'sizeof']):
                    continue
                c_match = class_pattern.search(line)
                if c_match:
                    symbols.append(('class', c_match.group(2), idx + 1))
                m_match = method_pattern.search(line)
                if m_match:
                    func_name = m_match.group(2)
                    if func_name not in ['if', 'for', 'while', 'switch', 'return']:
                        symbols.append(('method', func_name, idx + 1))
        return symbols