import os
import pandas as pd
from PySide2.QtCore import QObject, Signal


class ExcelModel(QObject):
    """Excel & WPS 数据模型，支持 .xlsx, .xls 和 .et 表格数据"""
    data_loaded = Signal(object)  # 成功加载数据后发射 DataFrame
    error_occurred = Signal(str) # 发生错误时发射错误信息

    def __init__(self):
        super().__init__()
        self._df = None
        self._file_path = ""

    @property
    def df(self):
        return self._df

    @property
    def file_path(self):
        return self._file_path

    def load_excel(self, file_path):
        try:
            self._file_path = file_path
            ext = os.path.splitext(file_path)[1].lower()

            if ext == '.et':
                # WPS .et 文件通常可以使用 openpyxl 引擎直接读取
                # 若部分传统 .et 文件报错，尝试使用 xlrd
                try:
                    self._df = pd.read_excel(file_path, engine='openpyxl')
                except Exception:
                    self._df = pd.read_excel(file_path, engine='xlrd')
            elif ext == '.xls':
                self._df = pd.read_excel(file_path, engine='xlrd')
            else:
                # 默认 .xlsx
                self._df = pd.read_excel(file_path)

            self.data_loaded.emit(self._df)
        except Exception as e:
            err_msg = str(e)
            if "xlrd" in err_msg or "openpyxl" in err_msg:
                err_msg += "\n提示：如果读取 WPS (.et) 或 Excel 文件报错，请确保已安装依赖：\npip install xlrd openpyxl"
            self.error_occurred.emit(err_msg)