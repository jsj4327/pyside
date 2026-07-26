#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
from core.template_manager import TemplateManager
from utils.file_utils import FileUtils

class ProjectGenerator:
    """项目脚手架批量构建器"""

    @staticmethod
    def generate_project(base_path: str, blueprint_text: str):
        """根据蓝图文本创建真实的物理目录与文件"""
        if not os.path.exists(base_path):
            os.makedirs(base_path, exist_ok=True)

        _, _, _, structure = TemplateManager.parse_blueprint(blueprint_text)

        for item in structure:
            if item["type"] == "dir":
                dir_path = os.path.join(base_path, *item["path"])
                os.makedirs(dir_path, exist_ok=True)
            elif item["type"] == "file":
                parents = item["parents"]
                file_name = item["name"]
                target_dir = os.path.join(base_path, *parents)
                os.makedirs(target_dir, exist_ok=True)
                
                file_path = os.path.join(target_dir, file_name)
                
                # 初始化默认模板内容
                content = f"# -*- coding: utf-8 -*-\n# 文件: {file_name}\n\n"
                if file_name == "main.py":
                    content = (
                        "import sys\n"
                        "from PySide2.QtWidgets import QApplication, QMessageBox\n\n"
                        "def main():\n"
                        "    app = QApplication(sys.argv)\n"
                        "    QMessageBox.information(None, '提示', '项目构建成功！')\n"
                        "    sys.exit(0)\n\n"
                        "if __name__ == '__main__':\n"
                        "    main()\n"
                    )
                
                if not os.path.exists(file_path):
                    FileUtils.write_file_safely(file_path, content)