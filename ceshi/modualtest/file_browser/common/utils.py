# -*- coding:utf-8 -*-
import os

def format_size(size: int) -> str:
    """格式化文件大小"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"

def get_file_icon(path: str) -> str:
    """获取文件图标（简单模拟）"""
    if os.path.isdir(path):
        return "📁"
    ext = os.path.splitext(path)[1].lower()
    icons = {
        '.py': '🐍', '.txt': '📄', '.md': '📝',
        '.json': '📋', '.html': '🌐', '.css': '🎨',
        '.js': '⚡', '.jpg': '🖼️', '.png': '🖼️',
        '.pdf': '📕', '.zip': '📦', '.exe': '⚙️'
    }
    return icons.get(ext, '📄')