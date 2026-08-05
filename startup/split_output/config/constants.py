import os

# 获取程序所在目录作为基准路径
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 定义本地数据存储文件
DATA_FILE = "launcher_apps.json"

# 默认分类列表
DEFAULT_CATEGORIES = ["我的脚本", "系统工具", "数据处理", "自动化", "开发测试", "其他"]

# 视图模式常量
VIEW_ALL = "all"
VIEW_CATEGORY = "category"
VIEW_ALPHA = "alpha"

# 网格列数
GRID_COLS = 5
WINDOW_SCALE = 0.85
