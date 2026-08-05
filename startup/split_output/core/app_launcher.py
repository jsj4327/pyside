import sys
import subprocess
import os
from utils.path_utils import get_absolute_path

class AppLauncher:
    @staticmethod
    def launch(exe_path: str) -> tuple:
        """
        启动应用程序
        Returns: (success: bool, message: str)
        """
        absolute_exe_path = get_absolute_path(exe_path)
        if not absolute_exe_path or not os.path.exists(absolute_exe_path):
            return False, f"路径无效或文件不存在。\n路径: {absolute_exe_path}"

        try:
            script_dir = os.path.dirname(absolute_exe_path)
            if sys.platform == "win32":
                subprocess.Popen(
                    ['python', absolute_exe_path],
                    cwd=script_dir,
                    creationflags=subprocess.CREATE_NEW_CONSOLE if sys.stdout else 0
                )
            else:
                subprocess.Popen(
                    ['python3', absolute_exe_path],
                    cwd=script_dir
                )
            return True, ""
        except Exception as e:
            return False, str(e)
