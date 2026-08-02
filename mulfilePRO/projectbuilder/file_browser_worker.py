# file_browser_worker.py
import os
from datetime import datetime

from PySide2.QtCore import QThread, Signal


# 非文本文件扩展名（图片、音视频、二进制等）
NON_TEXT_EXTENSIONS = {
    # 图片
    '.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff', '.tif',
    '.webp', '.svg', '.ico', '.icns', '.heic', '.heif',
    '.raw', '.cr2', '.nef', '.arw', '.dng',
    
    # 音视频
    '.mp3', '.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv',
    '.webm', '.m4a', '.m4v', '.3gp', '.ogg', '.wav', '.flac',
    '.aac', '.wma', '.opus', '.mka', '.mk3d',
    
    # 压缩包
    '.zip', '.rar', '.7z', '.tar', '.gz', '.bz2', '.xz',
    '.zst', '.lz', '.lzma', '.cab', '.arj', '.z',
    
    # 可执行文件/二进制
    '.exe', '.dll', '.so', '.dylib', '.bin', '.out',
    '.elf', '.msi', '.apk', '.app', '.deb', '.rpm',
    
    # 文档
    '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
    '.odt', '.ods', '.odp', '.rtf', '.epub', '.mobi',
    
    # 字体
    '.ttf', '.otf', '.woff', '.woff2', '.eot',
    
    # 其他二进制
    '.iso', '.img', '.dmg', '.pkg', '.nupkg',
    '.pyc', '.pyo', '.pyd', '.so', '.a', '.lib',
    '.o', '.obj', '.class', '.jar', '.war',
    '.dat', '.db', '.sqlite', '.sqlite3',
}

# 扩展名白名单（明确是文本文件）
TEXT_EXTENSIONS = {
    '.txt', '.py', '.js', '.jsx', '.ts', '.tsx', '.java',
    '.c', '.cpp', '.cc', '.cxx', '.h', '.hpp', '.hh',
    '.cs', '.go', '.rs', '.rb', '.php', '.html', '.htm',
    '.css', '.scss', '.sass', '.less', '.styl',
    '.json', '.xml', '.yml', '.yaml', '.toml', '.ini',
    '.cfg', '.conf', '.log', '.md', '.rst', '.tex',
    '.sh', '.bat', '.cmd', '.ps1', '.vim', '.lua',
    '.pl', '.pm', '.t', '.swift', '.kt', '.kts',
    '.dart', '.groovy', '.gradle', '.properties',
    '.env', '.gitignore', '.gitattributes', '.editorconfig',
    '.sql', '.r', '.m', '.mm', '.pas', '.d', '.nim',
    '.v', '.scala', '.clj', '.erl', '.hs', '.ml',
    '.f90', '.f95', '.for', '.adb', '.ads', '.bzl',
    '.bazel', '.mk', '.cmake', '.doxyfile',
}


class FileSystemWorker(QThread):
    """
    文件系统加载工作线程
    不阻塞主UI线程
    """
    finished = Signal(list)  # 文件列表
    error = Signal(str)      # 错误信息
    progress = Signal(int)   # 进度 (0-100)
    status = Signal(str)     # 状态信息

    def __init__(self, path, exclude_patterns=None, show_hidden=False, count_lines=False):
        super().__init__()
        self.path = path
        self.exclude_patterns = exclude_patterns or []  # 排除模式列表
        self.show_hidden = show_hidden
        self.count_lines = count_lines  # 是否统计行数
        self._is_running = True

    def stop(self):
        """停止线程"""
        self._is_running = False

    def _is_text_file(self, file_path):
        """
        判断文件是否为文本文件
        基于扩展名判断，非文本文件不统计行数
        """
        ext = os.path.splitext(file_path)[1].lower()
        
        # 如果在文本扩展名白名单中，是文本文件
        if ext in TEXT_EXTENSIONS:
            return True
        
        # 如果在非文本扩展名黑名单中，不是文本文件
        if ext in NON_TEXT_EXTENSIONS:
            return False
        
        # 未知扩展名：尝试读取少量字节检测是否为文本
        try:
            with open(file_path, 'rb') as f:
                sample = f.read(1024)
                # 如果包含空字节（\x00），很可能是二进制文件
                if b'\x00' in sample:
                    return False
                # 尝试解码为 UTF-8
                try:
                    sample.decode('utf-8')
                    return True
                except UnicodeDecodeError:
                    return False
        except Exception:
            return False

    def _count_file_lines(self, file_path):
        """统计文件行数（仅对文本文件）"""
        # 先判断是否为文本文件
        if not self._is_text_file(file_path):
            return -1
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                return sum(1 for _ in f)
        except Exception:
            return -1  # 统计失败返回 -1

    def _should_exclude(self, name, full_path):
        """
        判断文件/文件夹是否应该被排除
        支持扩展名排除 (*.py) 和关键词排除 (test)
        """
        # 如果是文件夹，只按名称关键词排除（不按扩展名）
        if os.path.isdir(full_path):
            for pattern in self.exclude_patterns:
                # 如果模式以 *. 开头，是扩展名模式，文件夹不匹配
                if pattern.startswith('*.'):
                    continue
                # 关键词匹配（不区分大小写）
                if pattern.lower() in name.lower():
                    return True
            return False

        # 如果是文件
        name_lower = name.lower()
        for pattern in self.exclude_patterns:
            # 扩展名模式：*.py, *.json 等
            if pattern.startswith('*.'):
                # 获取文件扩展名（包含点号）
                ext = os.path.splitext(name)[1].lower()
                # 比较扩展名（不包含 *）
                pattern_ext = pattern[1:].lower()
                if ext == pattern_ext:
                    return True
            else:
                # 关键词匹配（不区分大小写）
                if pattern.lower() in name_lower:
                    return True
        return False

    def run(self):
        """在工作线程中加载文件列表"""
        try:
            if not os.path.exists(self.path):
                self.error.emit(f"路径不存在: {self.path}")
                return

            if not os.path.isdir(self.path):
                self.error.emit(f"不是目录: {self.path}")
                return

            file_list = []
            try:
                entries = os.listdir(self.path)
            except PermissionError:
                self.error.emit(f"权限不足: {self.path}")
                return

            total = len(entries)
            for idx, name in enumerate(entries):
                if not self._is_running:
                    return

                # 更新进度
                if total > 0:
                    self.progress.emit(int((idx + 1) / total * 100))

                # 跳过隐藏文件（除非显式要求显示）
                if not self.show_hidden and name.startswith('.'):
                    continue

                full_path = os.path.join(self.path, name)
                
                # 检查是否应该排除
                if self.exclude_patterns and self._should_exclude(name, full_path):
                    continue

                try:
                    is_dir = os.path.isdir(full_path)
                    is_file = os.path.isfile(full_path)

                    # 获取文件信息
                    file_info = {
                        'name': name,
                        'path': full_path,
                        'is_dir': is_dir,
                        'size': os.path.getsize(full_path) if is_file else 0,
                        'modified': os.path.getmtime(full_path),
                        'is_hidden': name.startswith('.'),
                        'lines': -1  # 默认 -1 表示未统计
                    }

                    # 如果是文件且需要统计行数
                    if is_file and self.count_lines:
                        file_info['lines'] = self._count_file_lines(full_path)

                    file_list.append(file_info)
                except (OSError, PermissionError):
                    # 跳过无法访问的文件
                    continue

            # 排序：文件夹在前，然后按名称排序
            file_list.sort(key=lambda x: (not x['is_dir'], x['name'].lower()))
            self.finished.emit(file_list)

        except Exception as e:
            self.error.emit(str(e))