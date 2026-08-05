import os
from config.constants import BASE_DIR

def get_relative_path(absolute_path: str) -> str:
    """将绝对路径转换为相对于程序目录的路径"""
    if not absolute_path:
        return None
    try:
        return os.path.relpath(absolute_path, BASE_DIR)
    except ValueError:
        # 如果在不同驱动器上（Windows），无法计算相对路径，则返回绝对路径
        return absolute_path

def get_absolute_path(relative_path: str) -> str:
    """将相对路径转换为绝对路径"""
    if not relative_path:
        return None
    if os.path.isabs(relative_path):
        return relative_path
    return os.path.join(BASE_DIR, relative_path)

def validate_file_extension(path: str, accept_mode: str) -> bool:
    """验证文件扩展名是否符合要求"""
    if not os.path.isfile(path):
        return False
    ext = os.path.splitext(path)[1].lower()
    if accept_mode == "exe":
        return ext in [".py", ".pyw"]
    elif accept_mode == "image":
        return ext in [".png", ".jpg", ".jpeg", ".svg", ".ico", ".webp", ".gif"]
    return True
