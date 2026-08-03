# -*- coding: utf-8 -*-
import os
from shared.infrastructure.event_bus import event_bus

class WorkspaceEngineService:
    def __init__(self):
        self.scanned_files_cache = {}
        event_bus.subscribe("workspace:scan_requested", self.handle_scan_request)

    def handle_scan_request(self, data: dict):
        dir_path = data.get("dir_path", "")
        exclude_exts_raw = data.get("exclude_exts", "")
        exclude_empty = data.get("exclude_empty", True)  # 读取过滤空文件配置
        
        if not dir_path or not os.path.exists(dir_path):
            event_bus.publish("workspace:scan_finished", {
                "success": False,
                "message": f"目录路径无效或不存在: {dir_path}",
                "file_list": []
            })
            return

        exclude_exts = []
        if exclude_exts_raw:
            exclude_exts = [
                ext.strip().lower() if ext.strip().startswith('.') else f".{ext.strip().lower()}"
                for ext in exclude_exts_raw.split(",") if ext.strip()
            ]

        self.scanned_files_cache.clear()
        valid_files = []

        try:
            for root, dirs, files in os.walk(dir_path):
                dirs[:] = [d for d in dirs if d not in ['.git', '__pycache__', '.idea', '.vscode', 'venv']]
                
                for file in files:
                    file_ext = os.path.splitext(file)[1].lower()
                    if file_ext in exclude_exts:
                        continue
                    
                    abs_path = os.path.join(root, file)
                    
                    # 获取文件大小
                    try:
                        file_size = os.path.getsize(abs_path)
                    except Exception:
                        file_size = 0

                    # 核心新增：如果勾选了过滤空文件，且文件大小为 0，则跳过
                    if exclude_empty and file_size == 0:
                        continue

                    rel_path = os.path.relpath(abs_path, dir_path)

                    # 尝试读取文件内容
                    file_content = ""
                    try:
                        with open(abs_path, 'r', encoding='utf-8', errors='ignore') as f:
                            file_content = f.read()
                    except Exception as e:
                        file_content = f"[无法读取文件内容: {str(e)}]"

                    self.scanned_files_cache[rel_path] = {
                        "abs_path": abs_path,
                        "size": file_size,
                        "content": file_content
                    }

                    valid_files.append({
                        "rel_path": rel_path,
                        "size": file_size,
                        "content": file_content
                    })

            print(f"[WorkspaceEngine] 扫描完成，共找到 {len(valid_files)} 个有效文件 (过滤空文件开关: {exclude_empty})")
            event_bus.publish("workspace:scan_finished", {
                "success": True,
                "message": f"扫描成功，共加载 {len(valid_files)} 个文件",
                "file_list": valid_files
            })

        except Exception as e:
            event_bus.publish("workspace:scan_finished", {
                "success": False,
                "message": f"扫描过程发生异常: {str(e)}",
                "file_list": []
            })

# 创建单例实例
workspace_engine_service = WorkspaceEngineService()