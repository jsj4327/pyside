# run_manager.py
import os
import subprocess
import sys
from typing import Optional, Tuple, List, Callable


class RunManager:
    """项目运行管理器，负责检测并执行入口文件，支持多开、非阻塞后台运行"""

    # 保存所有由启动器拉起的子进程引用，防止垃圾回收，支持多开管理
    active_processes: List[subprocess.Popen] = []

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

    @classmethod
    def run_python_file(cls, file_path: str, capture_output: bool = True) -> Tuple[bool, str, str]:
        """
        运行一个 Python 文件（非阻塞，支持后台多开，永不超时销毁）
        
        Args:
            file_path: Python 文件的完整路径
            capture_output: 是否捕获输出
            
        Returns:
            (是否成功, stdout/提示信息, stderr)
        """
        if not os.path.isfile(file_path):
            return False, "", f"文件不存在: {file_path}"

        try:
            # 获取脚本所在目录作为工作目录，确保程序能正确读取同级数据文件
            work_dir = os.path.dirname(file_path)
            python_exe = sys.executable

            # 使用 Popen 在后台独立拉起进程，不阻塞主线程、不设超时
            process = subprocess.Popen(
                [python_exe, file_path],
                cwd=work_dir,
                stdout=subprocess.PIPE if capture_output else subprocess.DEVNULL,
                stderr=subprocess.PIPE if capture_output else subprocess.DEVNULL,
                text=True
            )

            # 将进程加入活跃列表并自动清理已关闭的死进程
            cls.active_processes.append(process)
            cls.active_processes = [p for p in cls.active_processes if p.poll() is None]

            success_msg = f"成功启动进程 [PID: {process.pid}] -> {os.path.basename(file_path)}"
            return True, success_msg, ""

        except Exception as e:
            return False, "", f"运行异常: {str(e)}"

    @classmethod
    def run_project(cls, project_path: str, callback: Optional[Callable[[str], None]] = None) -> Tuple[bool, str, str]:
        """
        运行项目：检测 main.py 并执行，支持回调与独立多开
        
        Args:
            project_path: 项目目录路径
            callback: 实时输出回调函数（接收 stdout/stderr 行）
            
        Returns:
            (是否成功, stdout, stderr)
        """
        if not os.path.isdir(project_path):
            return False, "", f"目录无效: {project_path}"

        main_file = cls.find_main_py(project_path)
        if main_file is None:
            return False, "", "未找到 main.py（忽略大小写）"

        # 调用非阻塞运行
        success, stdout, stderr = cls.run_python_file(main_file, capture_output=True)
        
        # 如果有回调函数，触发回调
        if callback and stdout:
            callback(stdout)

        return success, stdout, stderr