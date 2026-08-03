# file_browser_persistence.py
import os
import sys
import json
from PySide2.QtCore import QSettings, QByteArray, Qt, QTimer
from PySide2.QtWidgets import QTreeWidgetItem  # 修正：QiWidgets -> QtWidgets


class FileBrowserPersistence:
    """
    文件浏览器控件持久化管理器
    保存和恢复：窗口几何、列宽、排序状态、过滤器设置等
    配置文件保存在启动文件所在目录的 config.ini
    """
    
    def __init__(self, app_name="FileBrowser", org_name="YourCompany"):
        """
        初始化持久化管理器
        
        Args:
            app_name: 应用程序名称
            org_name: 组织名称
        """
        self.app_name = app_name
        self.org_name = org_name
        self._settings = self._create_settings()
    
    def _create_settings(self):
        """
        创建 QSettings 对象，使用启动文件所在目录的配置文件
        """
        # 获取启动文件所在目录
        if getattr(sys, 'frozen', False):
            # 打包后的可执行文件
            app_dir = os.path.dirname(sys.executable)
        else:
            # 开发环境：获取 main.py 所在目录
            # 从调用栈中找到启动文件的位置
            import inspect
            frame = inspect.stack()[-1]
            filename = frame.filename
            app_dir = os.path.dirname(os.path.abspath(filename))
        
        # 配置文件路径
        config_file = os.path.join(app_dir, "config.ini")
        
        # 使用 QSettings 的 INI 格式，指定文件路径
        settings = QSettings(config_file, QSettings.IniFormat)
        
        # 打印配置文件位置，方便调试
        print(f"📁 配置文件位置: {config_file}")
        
        return settings
    
    # ==========================================
    # 基础读写方法
    # ==========================================
    def save_value(self, key, value):
        """保存单个值"""
        self._settings.setValue(key, value)
    
    def load_value(self, key, default=None):
        """加载单个值"""
        return self._settings.value(key, default)
    
    def save_string(self, key, value):
        """保存字符串"""
        self._settings.setValue(key, value)
    
    def load_string(self, key, default=""):
        """加载字符串"""
        return self._settings.value(key, default)
    
    def save_int(self, key, value):
        """保存整数"""
        self._settings.setValue(key, int(value))
    
    def load_int(self, key, default=0):
        """加载整数"""
        return int(self._settings.value(key, default))
    
    def save_bool(self, key, value):
        """保存布尔值"""
        self._settings.setValue(key, bool(value))
    
    def load_bool(self, key, default=False):
        """加载布尔值"""
        value = self._settings.value(key, default)
        if isinstance(value, str):
            return value.lower() == 'true'
        return bool(value)
    
    def save_list(self, key, value_list):
        """保存列表（转为JSON字符串）"""
        try:
            json_str = json.dumps(value_list, ensure_ascii=False)
            self._settings.setValue(key, json_str)
        except Exception as e:
            print(f"保存列表失败: {e}")
    
    def load_list(self, key, default=None):
        """加载列表（从JSON字符串解析）"""
        if default is None:
            default = []
        try:
            json_str = self._settings.value(key, "")
            if json_str:
                return json.loads(json_str)
            return default
        except Exception:
            return default
    
    def get_config_path(self):
        """获取配置文件路径"""
        return self._settings.fileName()
    
    # ==========================================
    # 文件浏览器专用持久化方法
    # ==========================================
    def save_file_browser_state(self, file_browser):
        """
        保存文件浏览器的所有状态
        
        Args:
            file_browser: FileBrowser实例
        """
        # 保存当前路径
        current_path = file_browser.get_current_path()
        if current_path:
            self.save_string("current_path", current_path)
        
        # 保存排除模式列表
        if hasattr(file_browser, 'exclude_patterns'):
            self.save_list("exclude_patterns", file_browser.exclude_patterns)
        
        # 保存显示隐藏文件状态
        if hasattr(file_browser, 'show_hidden'):
            self.save_bool("show_hidden", file_browser.show_hidden)
        
        # 保存统计行数状态
        if hasattr(file_browser, 'count_lines'):
            self.save_bool("count_lines", file_browser.count_lines)
        
        # 保存树形控件的列宽
        tree = file_browser.tree
        if tree:
            header = tree.header()
            column_count = header.count()
            column_widths = {}
            for col in range(column_count):
                column_widths[str(col)] = header.sectionSize(col)
            self.save_value("column_widths", column_widths)
            
            # 保存排序状态
            sort_col = header.sortIndicatorSection()
            sort_order = header.sortIndicatorOrder()
            self.save_int("sort_column", sort_col)
            self.save_int("sort_order", sort_order)
        
        # 保存展开状态（展开的节点路径列表）
        expanded_paths = []
        self._collect_expanded_paths(tree.invisibleRootItem(), expanded_paths)
        self.save_list("expanded_paths", expanded_paths)
        
        # 同步保存到磁盘
        self._settings.sync()
        print(f"✅ 配置已保存到: {self.get_config_path()}")
    
    def load_file_browser_state(self, file_browser):
        """
        加载文件浏览器的所有状态
        
        Args:
            file_browser: FileBrowser实例
        """
        # 恢复排除模式列表
        patterns = self.load_list("exclude_patterns", [])
        if patterns and hasattr(file_browser, 'exclude_patterns'):
            file_browser.exclude_patterns = patterns
            # 更新过滤输入框
            if hasattr(file_browser, 'filter_edit'):
                file_browser.filter_edit.setText(", ".join(patterns))
        
        # 恢复显示隐藏文件状态
        show_hidden = self.load_bool("show_hidden", False)
        if hasattr(file_browser, 'show_hidden'):
            file_browser.show_hidden = show_hidden
            if hasattr(file_browser, 'btn_hidden'):
                file_browser.btn_hidden.setChecked(show_hidden)
        
        # 恢复统计行数状态
        count_lines = self.load_bool("count_lines", True)
        if hasattr(file_browser, 'count_lines'):
            file_browser.count_lines = count_lines
            if hasattr(file_browser, 'btn_count_lines'):
                file_browser.btn_count_lines.setChecked(count_lines)
        
        # 恢复树形控件的列宽
        tree = file_browser.tree
        if tree:
            column_widths = self.load_value("column_widths", {})
            if column_widths:
                header = tree.header()
                for col_str, width in column_widths.items():
                    try:
                        col = int(col_str)
                        if col < header.count():
                            header.resizeSection(col, width)
                    except (ValueError, TypeError):
                        pass
            
            # 恢复排序状态
            sort_col = self.load_int("sort_column", -1)
            sort_order = self.load_int("sort_order", 0)
            if sort_col >= 0:
                order = Qt.AscendingOrder if sort_order == 0 else Qt.DescendingOrder
                tree.sortItems(sort_col, order)
        
        # 恢复当前路径（在加载完成后调用）
        current_path = self.load_string("current_path", "")
        if current_path and os.path.exists(current_path) and os.path.isdir(current_path):
            file_browser.load_directory(current_path)
        
        # 恢复展开状态（在树加载完成后延迟执行）
        expanded_paths = self.load_list("expanded_paths", [])
        if expanded_paths:
            QTimer.singleShot(100, lambda: self._restore_expanded_paths(
                tree, expanded_paths
            ))
    
    def _collect_expanded_paths(self, parent_item, expanded_paths):
        """递归收集所有展开节点的路径"""
        if parent_item is None:
            return
        
        for i in range(parent_item.childCount()):
            child = parent_item.child(i)
            if child is None:
                continue
            
            # 获取节点的完整路径
            path = child.data(0, Qt.UserRole + 1)
            if path and child.isExpanded():
                expanded_paths.append(path)
            
            # 递归处理子节点
            self._collect_expanded_paths(child, expanded_paths)
    
    def _restore_expanded_paths(self, tree, expanded_paths):
        """递归恢复展开状态"""
        def expand_by_path(item, path_set):
            if item is None:
                return
            path = item.data(0, Qt.UserRole + 1)
            if path and path in path_set:
                item.setExpanded(True)
            for i in range(item.childCount()):
                expand_by_path(item.child(i), path_set)
        
        if not tree or not expanded_paths:
            return
        
        path_set = set(expanded_paths)
        for i in range(tree.topLevelItemCount()):
            expand_by_path(tree.topLevelItem(i), path_set)
    
    # ==========================================
    # 配置分组管理
    # ==========================================
    def begin_group(self, group_name):
        """进入配置分组"""
        self._settings.beginGroup(group_name)
    
    def end_group(self):
        """退出配置分组"""
        self._settings.endGroup()
    
    def clear_all(self):
        """清空所有配置"""
        self._settings.clear()
        self._settings.sync()
        print(f"✅ 配置已清除: {self.get_config_path()}")
    
    def remove_key(self, key):
        """删除指定键"""
        self._settings.remove(key)
    
    def contains(self, key):
        """检查配置是否存在"""
        return self._settings.contains(key)


# ==========================================
# 便捷函数
# ==========================================

def save_file_browser_settings(file_browser, app_name="FileBrowser"):
    """
    保存文件浏览器设置的便捷函数
    
    Args:
        file_browser: FileBrowser实例
        app_name: 应用程序名称
    """
    persistence = FileBrowserPersistence(app_name)
    persistence.save_file_browser_state(file_browser)


def load_file_browser_settings(file_browser, app_name="FileBrowser"):
    """
    加载文件浏览器设置的便捷函数
    
    Args:
        file_browser: FileBrowser实例
        app_name: 应用程序名称
    """
    persistence = FileBrowserPersistence(app_name)
    persistence.load_file_browser_state(file_browser)