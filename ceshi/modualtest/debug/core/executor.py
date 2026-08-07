# -*- coding:utf-8 -*-
from PySide2.QtCore import QObject, Signal, QThread
from dataclasses import dataclass, field
from datetime import datetime
import subprocess
import os
import sys
import threading


@dataclass
class ExecutionRecord:
    """执行记录"""
    file_path: str
    exit_code: int
    stdout: str
    stderr: str
    duration: float
    timestamp: datetime = field(default_factory=datetime.now)


class ExecutorWorker(QObject):
    """执行工作线程"""
    
    sig_output_received = Signal(str, str)
    sig_finished = Signal(int, float)
    sig_error = Signal(str)
    
    def __init__(self, file_path: str, work_dir: str):
        super().__init__()
        self.file_path = file_path
        self.work_dir = work_dir
        self._is_running = False
        self._start_time = None
        self._process = None
    
    def run(self):
        """在独立线程中执行"""
        self._is_running = True
        self._start_time = datetime.now()
        
        try:
            python_cmd = sys.executable
            print(f"[EXECUTOR] Python: {python_cmd}")
            print(f"[EXECUTOR] 文件: {self.file_path}")
            print(f"[EXECUTOR] 工作目录: {self.work_dir}")
            
            # 使用 Popen 实时捕获输出
            self._process = subprocess.Popen(
                [python_cmd, self.file_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=self.work_dir,
                text=True,
                encoding='utf-8',
                errors='replace'
            )
            
            # 实时读取输出
            def read_stdout():
                for line in iter(self._process.stdout.readline, ''):
                    if line:
                        self.sig_output_received.emit(line.rstrip('\n'), "out")
            
            def read_stderr():
                for line in iter(self._process.stderr.readline, ''):
                    if line:
                        self.sig_output_received.emit(line.rstrip('\n'), "err")
            
            stdout_thread = threading.Thread(target=read_stdout)
            stderr_thread = threading.Thread(target=read_stderr)
            stdout_thread.daemon = True
            stderr_thread.daemon = True
            
            stdout_thread.start()
            stderr_thread.start()
            
            # 等待进程结束
            exit_code = self._process.wait()
            
            stdout_thread.join(timeout=1)
            stderr_thread.join(timeout=1)
            
            if self._process.stdout:
                self._process.stdout.close()
            if self._process.stderr:
                self._process.stderr.close()
            
            # 计算耗时
            duration = (datetime.now() - self._start_time).total_seconds()
            
            self.sig_finished.emit(exit_code, duration)
            
        except FileNotFoundError as e:
            self.sig_error.emit(f"Python 解释器未找到: {e}")
        except Exception as e:
            self.sig_error.emit(f"执行错误: {str(e)}")
        finally:
            self._is_running = False
            self._process = None
    
    def stop(self):
        """停止执行"""
        if self._process:
            try:
                self._process.terminate()
                self._process.wait(timeout=2)
            except:
                try:
                    self._process.kill()
                except:
                    pass
            self._process = None
        self._is_running = False


class PythonExecutor(QObject):
    """Python 文件执行器 - 使用 subprocess + QThread"""
    
    sig_started = Signal(str)
    sig_output_received = Signal(str, str)
    sig_finished = Signal(int, float)
    sig_error = Signal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._last_record = None
        self._worker = None
        self._thread = None
    
    def run(self, file_path: str):
        """执行 Python 文件"""
        print(f"[EXECUTOR] 执行文件: {file_path}")
        
        if not os.path.exists(file_path):
            error_msg = f"文件不存在: {file_path}"
            self.sig_error.emit(error_msg)
            return
        
        if not file_path.endswith('.py'):
            error_msg = f"不是 Python 文件: {file_path}"
            self.sig_error.emit(error_msg)
            return
        
        if not os.access(file_path, os.R_OK):
            error_msg = f"文件不可读: {file_path}"
            self.sig_error.emit(error_msg)
            return
        
        work_dir = os.path.dirname(file_path)
        
        self.sig_started.emit(file_path)
        
        # 创建 QThread
        self._thread = QThread()
        
        # 创建工作线程
        self._worker = ExecutorWorker(file_path, work_dir)
        self._worker.moveToThread(self._thread)
        
        # 连接信号
        self._worker.sig_output_received.connect(self.sig_output_received.emit)
        self._worker.sig_finished.connect(self._on_worker_finished)
        self._worker.sig_error.connect(self.sig_error.emit)
        
        # 线程启动时执行 run
        self._thread.started.connect(self._worker.run)
        
        # 线程结束时清理
        self._thread.finished.connect(self._thread.deleteLater)
        self._thread.finished.connect(self._on_thread_finished)
        
        # 启动线程
        self._thread.start()
    
    def _on_worker_finished(self, exit_code: int, duration: float):
        """工作线程完成"""
        self.sig_finished.emit(exit_code, duration)
        # 退出线程
        if self._thread and self._thread.isRunning():
            self._thread.quit()
            self._thread.wait()
    
    def _on_thread_finished(self):
        """线程完成清理"""
        if self._worker:
            self._worker.deleteLater()
            self._worker = None
        self._thread = None
    
    def stop(self):
        """停止执行"""
        if self._worker:
            self._worker.stop()
        if self._thread and self._thread.isRunning():
            self._thread.quit()
            self._thread.wait()
    
    def get_last_record(self) -> ExecutionRecord:
        """获取最后一次执行记录"""
        return self._last_record
    
    def is_running(self) -> bool:
        """是否正在运行"""
        return self._thread is not None and self._thread.isRunning()