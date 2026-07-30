# -*- coding: utf-8 -*-
"""Workspace 模块对外 API。"""
import os
from typing import Dict, List, Optional, Tuple

from modules.workspace.application import file_io as file_io_app
from modules.workspace.infrastructure import local_fs


class WorkspaceApi:
    def __init__(self, default_save_dir: Optional[str] = None):
        self.save_dir = default_save_dir or os.path.join(os.getcwd(), "output_codes")
        local_fs.ensure_dir(self.save_dir)
        self.files_cache: Dict[str, str] = {}

    def set_save_dir(self, path: str) -> None:
        self.save_dir = path
        local_fs.ensure_dir(self.save_dir)

    def save_received_files(self, files: List[Dict[str, str]]) -> List[Tuple[str, bool, str]]:
        results = file_io_app.save_files_batch(self.save_dir, files)
        for rel, ok, payload in results:
            if ok:
                self.files_cache[rel] = payload
        return results

    def save_file(self, relative_path: str, content: str) -> Tuple[bool, str]:
        ok, msg = file_io_app.save_single_file(self.save_dir, relative_path, content)
        if ok:
            self.files_cache[relative_path] = content
        return ok, msg

    def get_cached(self, relative_path: str) -> Optional[str]:
        return self.files_cache.get(relative_path)