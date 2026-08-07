# -*- coding:utf-8 -*-
import os


def build_file_prompt(file_paths: list, base_path: str = "") -> str:
    """
    构建文件内容的 Prompt 格式
    file_paths: 文件路径列表
    base_path: 基础路径（用于计算相对路径）
    """
    if not file_paths:
        return ""
    
    parts = []
    parts.append("\n\n【附加文件内容】")
    
    for file_path in file_paths:
        if not os.path.exists(file_path):
            continue
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception:
            continue
        
        rel_path = os.path.relpath(file_path, base_path) if base_path else os.path.basename(file_path)
        parts.append(f"\n--- 文件: {rel_path} ---")
        parts.append(f"```\n{content}\n```")
    
    parts.append("\n【文件内容结束】")
    return "\n".join(parts)


def get_file_browser_selection(window) -> tuple:
    """
    从文件浏览器获取选中文件或当前目录
    返回: (files: list, current_dir: str)
    """
    files = []
    current_dir = ""
    
    # 尝试从主窗口获取文件浏览器
    if hasattr(window, 'browser') and hasattr(window.browser, 'get_selected_files'):
        files = window.browser.get_selected_files()
        current_dir = window.browser.get_current_path()
    elif hasattr(window, 'file_manager') and hasattr(window.file_manager, 'get_selected_files'):
        files = window.file_manager.get_selected_files()
        current_dir = window.file_manager.get_current_path()
    
    return files, current_dir