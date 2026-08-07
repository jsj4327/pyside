# -*- coding:utf-8 -*-
import os
import json
from typing import List, Dict, Optional
from PySide2.QtCore import QObject, Signal


class TemplateManager(QObject):
    """模板管理器 - 管理所有模板文件"""
    
    sig_templates_updated = Signal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._template_dir = self._get_template_dir()
        self._templates: Dict[str, str] = {}
        self._custom_templates: Dict[str, str] = {}
        self._load_all_templates()
    
    def _get_template_dir(self) -> str:
        """获取模板目录路径"""
        # 当前文件所在目录
        current_dir = os.path.dirname(os.path.abspath(__file__))
        template_dir = os.path.join(current_dir, "templates")
        
        # 如果不存在，创建目录
        if not os.path.exists(template_dir):
            os.makedirs(template_dir)
        
        # 创建自定义模板子目录
        custom_dir = os.path.join(template_dir, "custom")
        if not os.path.exists(custom_dir):
            os.makedirs(custom_dir)
        
        return template_dir
    
    def _load_all_templates(self):
        """加载所有模板"""
        print(f"[TEMPLATE] 加载模板，目录: {self._template_dir}")
        
        # 清空现有模板
        self._templates = {}
        self._custom_templates = {}
        
        # 加载系统模板
        system_templates = [
            ("architecture_web", "Web应用架构"),
            ("architecture_mobile", "移动应用架构"),
            ("architecture_desktop", "桌面应用架构"),
            ("architecture_default", "通用架构"),
            ("improve_project", "项目改进"),
        ]
        
        for name, label in system_templates:
            file_path = os.path.join(self._template_dir, f"{name}.txt")
            content = self._load_template_file(file_path)
            if content:
                self._templates[name] = content
                print(f"[TEMPLATE] 加载系统模板: {name}")
            else:
                # 如果文件不存在，创建默认模板
                self._create_default_template(name, label)
                self._templates[name] = self._load_template_file(file_path) or ""
        
        # 加载自定义模板
        custom_dir = os.path.join(self._template_dir, "custom")
        if os.path.exists(custom_dir):
            for file_name in os.listdir(custom_dir):
                if file_name.endswith(".txt"):
                    name = file_name[:-4]  # 去掉 .txt
                    file_path = os.path.join(custom_dir, file_name)
                    content = self._load_template_file(file_path)
                    if content:
                        self._custom_templates[name] = content
                        print(f"[TEMPLATE] 加载自定义模板: {name}")
        
        print(f"[TEMPLATE] 模板加载完成，系统: {len(self._templates)} 个，自定义: {len(self._custom_templates)} 个")
        self.sig_templates_updated.emit()
    
    def _load_template_file(self, file_path: str) -> Optional[str]:
        """加载模板文件"""
        try:
            if os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8') as f:
                    return f.read()
            return None
        except Exception as e:
            print(f"[TEMPLATE-ERROR] 加载模板失败 {file_path}: {e}")
            return None
    
    def _create_default_template(self, name: str, label: str):
        """创建默认模板"""
        file_path = os.path.join(self._template_dir, f"{name}.txt")
        
        if os.path.exists(file_path):
            return
        
        default_content = f"""【任务】{label}

【项目背景】
{{context}}

【核心需求】
请根据当前项目情况，设计合理的方案：

1. 请在此添加具体需求
2. 请在此添加具体要求
3. 请在此添加具体内容

【要求】
- 结合实际项目需求
- 给出具体可执行的方案
- 按上述结构清晰输出
"""
        
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(default_content)
            print(f"[TEMPLATE] 创建默认模板: {name}")
        except Exception as e:
            print(f"[TEMPLATE-ERROR] 创建默认模板失败 {name}: {e}")
    
    def get_template(self, name: str) -> Optional[str]:
        """获取模板内容"""
        # 先查系统模板
        if name in self._templates:
            return self._templates[name]
        # 再查自定义模板
        if name in self._custom_templates:
            return self._custom_templates[name]
        return None
    
    def get_all_templates(self) -> Dict[str, str]:
        """获取所有模板"""
        all_templates = {}
        all_templates.update(self._templates)
        all_templates.update(self._custom_templates)
        return all_templates
    
    def get_system_templates(self) -> Dict[str, str]:
        """获取系统模板"""
        return self._templates.copy()
    
    def get_custom_templates(self) -> Dict[str, str]:
        """获取自定义模板"""
        return self._custom_templates.copy()
    
    def save_template(self, name: str, content: str, is_custom: bool = True) -> bool:
        """保存模板"""
        try:
            if is_custom:
                dir_path = os.path.join(self._template_dir, "custom")
            else:
                dir_path = self._template_dir
            
            if not os.path.exists(dir_path):
                os.makedirs(dir_path)
            
            file_path = os.path.join(dir_path, f"{name}.txt")
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            # 重新加载
            self._load_all_templates()
            return True
        except Exception as e:
            print(f"[TEMPLATE-ERROR] 保存模板失败: {e}")
            return False
    
    def delete_custom_template(self, name: str) -> bool:
        """删除自定义模板"""
        try:
            file_path = os.path.join(self._template_dir, "custom", f"{name}.txt")
            if os.path.exists(file_path):
                os.remove(file_path)
                self._load_all_templates()
                return True
            return False
        except Exception as e:
            print(f"[TEMPLATE-ERROR] 删除模板失败: {e}")
            return False
    
    def get_template_names(self) -> List[str]:
        """获取所有模板名称"""
        return list(self.get_all_templates().keys())
    
    def get_template_display_name(self, name: str) -> str:
        """获取模板显示名称"""
        display_names = {
            "architecture_web": "Web应用架构",
            "architecture_mobile": "移动应用架构",
            "architecture_desktop": "桌面应用架构",
            "architecture_default": "通用架构",
            "improve_project": "项目改进",
        }
        
        if name in display_names:
            return display_names[name]
        
        # 自定义模板：直接使用文件名
        return name.replace("_", " ").title()