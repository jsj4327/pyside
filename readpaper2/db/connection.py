# db/connection.py
"""
数据库连接池与句柄线程安全管理模块。
"""
import sqlite3
import threading
import logging
from typing import Optional
from config import DB_FILE

logger = logging.getLogger(__name__)

class DatabaseConnection:
    """提供线程局部（Thread-local）Safe SQLite 连接句柄"""

    def __init__(self, db_path: str = DB_FILE):
        self.db_path = db_path
        self._local = threading.local()

    def get_connection(self) -> sqlite3.Connection:
        if not hasattr(self._local, "connection") or self._local.connection is None:
            try:
                conn = sqlite3.connect(self.db_path, timeout=30.0)
                conn.row_factory = sqlite3.Row
                # 开启 WAL 模式以支持更高并发读写性能
                conn.execute("PRAGMA journal_mode = WAL;")
                conn.execute("PRAGMA synchronous = NORMAL;")
                conn.execute("PRAGMA cache_size = -64000;")  # 约 64MB 缓存
                conn.execute("PRAGMA foreign_keys = ON;")
                self._local.connection = conn
                logger.debug(f"已为线程 [{threading.get_ident()}] 创建新的 SQLite 连接")
            except sqlite3.Error as e:
                logger.error(f"数据库连接失败: {str(e)}")
                raise e
        return self._local.connection

    def close(self):
        if hasattr(self._local, "connection") and self._local.connection is not None:
            try:
                self._local.connection.close()
                logger.debug(f"已关闭线程 [{threading.get_ident()}] 的 SQLite 连接")
            except sqlite3.Error as e:
                logger.error(f"关闭数据库连接报错: {str(e)}")
            finally:
                self._local.connection = None

    def execute_backup(self, backup_file_path: str):
        """数据库热备份逻辑"""
        conn = self.get_connection()
        backup_conn = sqlite3.connect(backup_file_path)
        with backup_conn:
            conn.backup(backup_conn)
        backup_conn.close()
        logger.info(f"数据库已被成功备份至: {backup_file_path}")