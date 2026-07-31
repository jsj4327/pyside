from PySide2.QtWidgets import QFileDialog



class ExcelController:
    """控制器，衔接 View 的用户操作与 Model 的数据处理"""
    def __init__(self, model, view):
        self.model = model
        self.view = view

        # 绑定 View 发出的操作信号
        self.view.import_excel_requested.connect(self.handle_import_excel)

        # 绑定 Model 发出的数据变动信号
        self.model.data_loaded.connect(self.view.display_data)
        self.model.error_occurred.connect(self.view.show_error)

    def handle_import_excel(self):
        """打开文件选择框，加入对 .et (WPS表格) 的支持"""
        file_path, _ = QFileDialog.getOpenFileName(
            self.view,
            "选择 Excel / WPS 表格文件",
            "",
            "表格文件 (*.xlsx *.xls *.et);;Excel Files (*.xlsx *.xls);;WPS 表格 (*.et)"
        )
        if file_path:
            self.model.load_excel(file_path)