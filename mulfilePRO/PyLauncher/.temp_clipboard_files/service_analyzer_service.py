# -*- coding: utf-8 -*-

import ast  # 导入 Python 内置的抽象语法树解析模块

class AnalyzerService:
    """代码分析服务：负责静态解析源码，提取类、函数定义及行号信息"""

    @staticmethod
    def extract_symbols(file_path):
        """静态方法：解析指定路径的 Python 文件，返回结构化的大纲符号列表"""
        symbols = []  # 初始化空列表，用于存储解析出的符号（字典格式）
        try:
            # 以只读模式打开文件，强制使用 UTF-8 编码，忽略无法解析的字符
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()  # 读取文件全部源码内容
                # 将源码字符串解析为 AST 语法树对象
                tree = ast.parse(content, filename=file_path)
            
            # 遍历 AST 语法树中的每一个节点
            for node in ast.walk(tree):
                # 判断当前节点是否为“类定义”
                if isinstance(node, ast.ClassDef):
                    symbols.append({
                        "type": "class",      # 符号类型为类
                        "name": node.name,    # 提取类名
                        "lineno": node.lineno # 提取该类在代码中的起始行号
                    })
                # 判断当前节点是否为“函数定义”
                elif isinstance(node, ast.FunctionDef):
                    symbols.append({
                        "type": "function",   # 符号类型为函数
                        "name": node.name,    # 提取函数名
                        "lineno": node.lineno # 提取该函数在代码中的起始行号
                    })
            
            # 解析完成后，按照行号从小到大对符号列表进行排序
            symbols.sort(key=lambda x: x["lineno"])
        except Exception:
            # 如果解析失败（例如语法错误的文件），捕获异常并静默处理
            pass
        
        return symbols  # 返回整理好的大纲符号列表