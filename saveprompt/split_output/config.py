"""
全局配置常量模块
集中管理数据文件路径、默认分类、分页选项及UI样式常量。
"""
import os

# 数据存储文件路径（与脚本同目录）
DATA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "prompts_data.json")

# 默认分类列表
DEFAULT_CATEGORIES = ["编程协同", "翻译润色", "文本写作", "角色扮演", "通用工具"]

# 未分类兜底名称
UNCATEGORIZED = "未分类"

# 全部分类标识符
ALL_CATEGORY_KEY = "ALL"

# 分页大小可选项
PAGE_SIZE_OPTIONS = [50, 100, 200, 500]

# 默认每页条数
DEFAULT_PAGE_SIZE = 50

# UI 样式常量
STYLE_BTN_PRIMARY = "background-color: #007ACC; color: white; font-weight: bold;"
STYLE_BTN_SUCCESS = "background-color: #28A745; color: white; font-weight: bold;"
STYLE_BTN_DANGER = "color: red;"
STYLE_CODE_FONT = "Consolas"
STYLE_CODE_SIZE = 10

# 默认预设初始数据
DEFAULT_DATA = {
    "categories": DEFAULT_CATEGORIES.copy(),
    "prompts": [
        {
            "id": "1",
            "title": "Python 代码重构与架构分析",
            "category": "编程协同",
            "tags": "Python, 重构, 架构",
            "prompt": "你是一个资深的 Python 架构师。请分析以下代码的逻辑缺陷、性能瓶颈以及架构不合理之处，并给出遵循 PEP 8 和模块化单体原则的重构建议：\n\n[在此粘贴代码]",
            "notes": "适用于排查复杂业务逻辑或臃肿函数",
            "updated_at": "2026-07-29 10:00:00"
        },
        {
            "id": "2",
            "title": "专业技术文档翻译 (英译中)",
            "category": "翻译润色",
            "tags": "翻译, 技术文档",
            "prompt": "请将以下英文技术文档翻译为地道的中文。要求：\n1. 保持专业术语准确（如 Repository, Decorator, Dependency Injection 等）；\n2. 语句通顺，符合中文阅读习惯；\n3. 保留原有的 Markdown 格式。\n\n[粘贴英文内容]",
            "notes": "适合翻译 GitHub Readme 或 API 文档",
            "updated_at": "2026-07-29 11:30:00"
        }
    ]
}
