import os

DEFAULT_GITIGNORE_CONTENT = """# Python
__pycache__/
*.py[cod]
*$py.class

# 虚拟环境
.venv/
venv/
env/
ENV/

# 环境变量
.env

# 操作系统
.DS_Store
Thumbs.db

# IDE / 编辑器
.vscode/
.idea/
*.swp
*.swo

# Qt / PySide / PyQt 构建文件
ui_*.py
*_rc.py
*.qmlc
*.jsc
"""


def generate_gitignore(repo_path: str) -> tuple:
    """
    Generate .gitignore in the given repo path.
    Returns: (success: bool, message: str)
    """
    gitignore_path = os.path.join(repo_path, ".gitignore")
    try:
        with open(gitignore_path, 'w', encoding='utf-8') as f:
            f.write(DEFAULT_GITIGNORE_CONTENT)
        return True, "已成功生成适用于 Python/Qt 的 .gitignore 文件！"
    except Exception as e:
        return False, f"生成 .gitignore 文件失败：\n{str(e)}"


def check_gitignore_exists(repo_path: str) -> bool:
    gitignore_path = os.path.join(repo_path, ".gitignore")
    return os.path.exists(gitignore_path)


def get_gitignore_path(repo_path: str) -> str:
    return os.path.join(repo_path, ".gitignore")
