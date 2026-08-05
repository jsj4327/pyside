# -*- coding:utf-8 -*-
import os
import json
import re


class ProjectFileGenerator:
    """项目文件生成器 - 解析AI响应并生成文件"""

    @staticmethod
    def extract_files_from_response(text: str) -> list:
        """
        从AI响应中提取文件列表
        参考源码预览模块的extract_json_from_response方法
        """
        if not text:
            return []

        def strip_line_numbers(content):
            lines = content.splitlines()
            stripped_lines = []
            for line in lines:
                stripped = re.sub(r'^\s*\d+[\.\)]?\s*', '', line)
                stripped_lines.append(stripped)
            return '\n'.join(stripped_lines)

        candidates = []

        # 1. 从 ```json ... ``` 代码块提取
        match = re.search(r'```json\s*([\s\S]*?)\s*```', text)
        if match:
            candidates.append(match.group(1).strip())

        # 2. 从 ``` ... ``` 代码块提取
        match = re.search(r'```\s*([\s\S]*?)\s*```', text)
        if match:
            candidates.append(match.group(1).strip())

        # 3. 从代码块标记提取
        match = re.search(r'【代码块\s*(?:json|JSON)?】?\s*([\s\S]*?)\s*【代码块结束】?', text)
        if match:
            candidates.append(match.group(1).strip())

        # 4. 直接提取整个文本
        candidates.append(text.strip())

        for raw in candidates:
            cleaned = strip_line_numbers(raw)
            
            # 尝试解析JSON数组
            try:
                data = json.loads(cleaned)
                if isinstance(data, list):
                    return data
                if isinstance(data, dict) and 'files' in data:
                    return data['files']
            except:
                pass

            # 尝试提取数组
            match = re.search(r'(\[\s*\{[\s\S]*?\}\s*\])', cleaned)
            if match:
                try:
                    data = json.loads(match.group(1))
                    if isinstance(data, list):
                        return data
                except:
                    pass

            # 尝试提取对象
            match = re.search(r'(\{[\s\S]*\})', cleaned)
            if match:
                try:
                    data = json.loads(match.group(1))
                    if isinstance(data, dict) and 'files' in data:
                        return data['files']
                except:
                    pass

        return []

    @staticmethod
    def generate_files(files_data: list, base_dir: str) -> tuple:
        """生成文件到磁盘，返回(成功数, 错误列表)"""
        success_count = 0
        errors = []

        for file_info in files_data:
            path = file_info.get('path', '')
            content = file_info.get('content', '')
            
            if not path:
                errors.append("缺少path字段")
                continue

            # 还原下划线转义
            path = path.replace('\\u005f', '_')

            full_path = os.path.join(base_dir, path)
            
            try:
                dir_path = os.path.dirname(full_path)
                if dir_path and not os.path.exists(dir_path):
                    os.makedirs(dir_path)
                
                with open(full_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                success_count += 1
            except Exception as e:
                errors.append(f"{path}: {str(e)}")

        return success_count, errors