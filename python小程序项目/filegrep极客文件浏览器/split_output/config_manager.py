"""
配置管理器模块
提供应用程序配置的持久化存储功能，支持JSON格式的配置读写。
"""
import os
import json
import logging
from typing import Any, Optional

# 配置文件路径：与当前脚本同目录下的 .config.json
CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".config.json")

logger = logging.getLogger(__name__)


class ConfigManager:
    """
    配置管理器类
    负责加载、保存和访问应用程序配置。
    配置以JSON格式存储在本地文件中。
    """

    def __init__(self):
        """初始化配置管理器并加载现有配置。"""
        self.config: dict = {}
        self.load()

    def load(self) -> dict:
        """
        从配置文件加载配置。
        如果文件不存在或读取失败，则使用空字典作为默认配置。
        
        Returns:
            dict: 加载的配置字典
        """
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    self.config = json.load(f)
            except (json.JSONDecodeError, IOError, OSError) as e:
                logger.warning("配置文件读取失败，将使用默认配置: %s", e)
                self.config = {}
        else:
            self.config = {}
        return self.config

    def save(self) -> bool:
        """
        将当前配置保存到文件。
        
        Returns:
            bool: 保存成功返回True，失败返回False
        """
        try:
            # 确保目录存在
            config_dir = os.path.dirname(CONFIG_FILE)
            if config_dir and not os.path.exists(config_dir):
                os.makedirs(config_dir, exist_ok=True)
                
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, ensure_ascii=False, indent=4)
            return True
        except (IOError, OSError) as e:
            logger.error("保存配置失败: %s", e)
            return False

    def get(self, key: str, default: Any = None) -> Any:
        """
        获取配置项的值。
        
        Args:
            key: 配置键名
            default: 键不存在时的默认值
            
        Returns:
            配置项的值或默认值
        """
        return self.config.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """
        设置配置项的值并自动保存。
        
        Args:
            key: 配置键名
            value: 配置值
        """
        self.config[key] = value
        self.save()

    def delete(self, key: str) -> None:
        """
        删除指定配置项并保存。
        
        Args:
            key: 要删除的配置键名
        """
        if key in self.config:
            del self.config[key]
            self.save()

    def clear(self) -> None:
        """清空所有配置并保存。"""
        self.config.clear()
        self.save()
