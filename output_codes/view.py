import pandas as pd
from PySide2.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QPushButton, QTableWidget, QTableWidgetItem, QLabel, QMessageBox
)
from PySide2.QtCore import Signal


class MainWindow(QMainWindow):
    """主视图界面"""
    import_excel_requested = Signal()

    def __init__(self):
        super().__init__()
        self.setWindowTitle("PySide2 Excel 导入分析软件 (MVC)")
        self.resize(800, 600)

        # 控件初始化
        self.btn_import = QPushButton("导入 Excel 文件")
        self.status_label = QLabel("当前未加载任何文件")
        self.table_widget = QTableWidget()

        # 布局组织
        top_layout = QHBoxLayout()
        top_layout.addWidget(self.btn_import)
        top_layout.addWidget(self.status_label)
        top_layout.addStretch()

        main_layout = QVBoxLayout()
        main_layout.addLayout(top_layout)
        main_layout.addWidget(self.table_widget)

        container = QWidget()
        container.setLayout(main_layout)
        self.setCentralWidget(container)

        # 信号绑定
        self.btn_import.clicked.connect(self.import_excel_requested.emit)

    def display_data(self, df):
        """将 DataFrame 数据填充至 QTableWidget"""
        self.table_widget.clear()
        self.table_widget.setRowCount(df.shape[0])
        self.table_widget.setColumnCount(df.shape[1])
        self.table_widget.setHorizontalHeaderLabels([str(col) for col in df.columns])

        for row_idx, row in df.iterrows():
            for col_idx, value in enumerate(row):
                cell_value = "" if pd.isna(value) else str(value)
                self.table_widget.setItem(row_idx, col_idx, QTableWidgetItem(cell_value))

        self.status_label.setText(f"成功加载: {df.shape[0]} 行 x {df.shape[1]} 列")

    def show_error(self, message):
        """弹出错误提示框（使用字符串拼接彻底防范 EOL 异常）"""
        err_msg = "加载 Excel 失败:\n" + str(message)
        QMessageBox.critical(self, "错误", err_msg)
        self.status_label.setText("文件加载失败")