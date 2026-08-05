import json
import os
from config.constants import DATA_FILE

class DataManager:
    @staticmethod
    def load_data() -> list:
        """加载应用数据"""
        if os.path.exists(DATA_FILE):
            try:
                with open(DATA_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"读取数据失败: {e}")
        return []

    @staticmethod
    def save_data(apps: list) -> bool:
        """保存应用数据"""
        try:
            with open(DATA_FILE, 'w', encoding='utf-8') as f:
                json.dump(apps, f, ensure_ascii=False, indent=4)
            return True
        except Exception as e:
            print(f"保存数据失败: {e}")
            return False
