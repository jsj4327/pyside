# -*- coding: utf-8 -*-

import os
import ast

class ScannerService:
    """项目扫描服务类：封装了文件系统遍历与 AST 语法树静态分析逻辑"""

    @staticmethod
    def is_main_script(file_path):
        """静态方法：利用 Python AST（抽象语法树）分析文件是否包含 if __name__ == '__main__': 入口"""
        try:
            # 以只读方式打开 Python 脚本文件
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                file_content = f.read()
            
            # 将源码解析为抽象语法树
            tree = ast.parse(file_content, filename=file_path)
            
            # 遍历语法树中的每一个节点
            for node in ast.walk(tree):
                # 检查节点是否为条件判断语句 (if 语句)
                if isinstance(node, ast.If):
                    test_expr = node.test
                    # 检查是否为比较表达式
                    if isinstance(test_expr, ast.Compare):
                        # 检查左侧是否为变量名 '__name__'
                        is_name_match = (isinstance(test_expr.left, ast.Name) and test_expr.left.id == '__name__')
                        
                        # 检查右侧比较值是否为字符串 '__main__'
                        for comp in test_expr.comparators:
                            if isinstance(comp, ast.Constant) and comp.value == '__main__':
                                return True
                            elif isinstance(comp, ast.Str) and comp.s == '__main__':
                                return True
        except Exception:
            # 解析出错时忽略，防止单文件异常导致整个扫描崩溃
            pass
        return False

    @classmethod
    def scan_directory(cls, root_dir):
        """类方法：递归扫描指定目录下的所有 Python 文件并找出推荐入口"""
        py_files_list = []      # 用于存放所有找到的 .py 相对路径
        probable_mains_list = [] # 用于存放推荐的 main 入口文件列表

        # 使用 os.walk 深度遍历目录
        for root, _, files in os.walk(root_dir):
            # 过滤掉常见的虚拟环境、缓存以及版本控制目录
            if any(exclude_dir in root for exclude_dir in ['.git', '__pycache__', '.venv', 'venv', 'env']):
                continue
            
            for file in files:
                # 仅处理以 .py 结尾的文件
                if file.endswith('.py'):
                    full_path = os.path.join(root, file)
                    # 计算相对于项目根目录的相对路径
                    rel_path = os.path.relpath(full_path, root_dir)
                    py_files_list.append(rel_path)
                    
                    # 规则判断：如果文件名为 main.py 或者 AST 分析包含主入口特征，则加入推荐列表
                    if file == 'main.py' or cls.is_main_script(full_path):
                        probable_mains_list.append(rel_path)

        # 返回包含所有文件与推荐入口的字典
        return {
            "files": py_files_list,
            "mains": probable_mains_list
        }