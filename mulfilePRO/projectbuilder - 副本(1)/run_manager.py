# run_manager.py
import os
import subprocess
import sys
from typing import Optional, Tuple, List


class RunManager:
    """项目运行管理器，负责检测并执行入口文件，捕获输出"""

    @staticmethod
    def find_main_py(project_path: str) -> Optional[str]:
        """
        在指定目录下查找 main.py（忽略大小写）
        
        Args:
            project_path: 项目目录路径
            
        Returns:
            找到的 main.py 完整路径，若未找到则返回 None
        """
        if not os.path.isdir(project_path):
            return None

        for filename in os.listdir(project_path):
            if filename.lower() == "main.py":
                full_path = os.path.join(project_path, filename)
                if os.path.isfile(full_path):
                    return full_path
        return None

    @staticmethod
    def run_python_file(file_path: str, capture_output: bool = True) -> Tuple[bool, str, str]:
        """
        运行一个 Python 文件，并返回输出
        
        Args:
            file_path: Python 文件的完整路径
            capture_output: 是否捕获输出（True时返回stdout/stderr）
            
        Returns:
            (是否成功, stdout, stderr)
        """
        if not os.path.isfile(file_path):
            return False, "", f"文件不存在: {file_path}"

        try:
            # 获取脚本所在目录作为工作目录
            work_dir = os.path.dirname(file_path)
            python_exe = sys.executable

            # 运行并捕获输出
            result = subprocess.run(
                [python_exe, file_path],
                cwd=work_dir,
                capture_output=capture_output,
                text=True,
                timeout=60  # 可配置超时
            )
            stdout = result.stdout if result.stdout else ""
            stderr = result.stderr if result.stderr else ""
            
            if result.returncode == 0:
                return True, stdout, stderr
            else:
                return False, stdout, stderr
        except subprocess.TimeoutExpired:
            return False, "", "运行超时（60秒）"
        except Exception as e:
            return False, "", f"运行异常: {str(e)}"

    @staticmethod
    def run_project(project_path: str, callback=None) -> Tuple[bool, str, str]:
        """
        运行项目：检测 main.py 并执行，可回调实时输出
        
        Args:
            project_path: 项目目录路径
            callback: 实时输出回调函数（接收 stdout/stderr 行）
            
        Returns:
            (是否成功, stdout, stderr)
        """
        if not os.path.isdir(project_path):
            return False, "", f"目录无效: {project_path}"

        main_file = RunManager.find_main_py(project_path)
        if main_file is None:
            return False, "", f"未找到 main.py（忽略大小写）"

        # 简化：直接调用 run_python_file 并返回完整输出
        # 若需要实时输出，可修改为使用 Popen 并逐行回调，但此处先满足基础需求
        return RunManager.run_python_file(main_file, capture_output=True)