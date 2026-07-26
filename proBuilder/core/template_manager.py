#!/usr/bin/env python3
# -*- coding: utf-8 -*-

class TemplateManager:
    """项目结构蓝图解析器"""

    @staticmethod
    def parse_blueprint(text: str):
        """
        解析文本格式的架构蓝图
        返回: (formatted_preview_str, folders_count, files_count, structured_list)
        """
        lines = text.splitlines()
        dir_stack = []
        result_lines = []
        folders_count = 0
        files_count = 0
        parsed_structure = []

        for line in lines:
            if not line.strip() or line.strip() == "│":
                continue

            clean_line = line.replace("│", " ").replace("├──", "").replace("└──", "").rstrip()
            indent = len(line) - len(line.lstrip(' │'))
            item_name = clean_line.strip()
            
            if not item_name:
                continue

            if "#" in item_name:
                item_name = item_name.split("#")[0].strip()

            if not item_name:
                continue

            level = indent // 4
            while len(dir_stack) > level:
                dir_stack.pop()

            if item_name.endswith("/"):
                dir_name = item_name.rstrip("/")
                dir_stack.append(dir_name)
                folders_count += 1
                result_lines.append("  " * level + f"📁 {dir_name}/")
                parsed_structure.append({"type": "dir", "path": list(dir_stack)})
            else:
                files_count += 1
                result_lines.append("  " * level + f"📄 {item_name}")
                current_parents = list(dir_stack)
                parsed_structure.append({"type": "file", "name": item_name, "parents": current_parents})

        preview_summary = "\n".join(result_lines)
        return preview_summary, folders_count, files_count, parsed_structure