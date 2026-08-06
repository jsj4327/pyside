from PySide2.QtWidgets import (QMainWindow, QSplitter, QWidget, QHBoxLayout,
                               QMenuBar, QMenu, QAction, QFileDialog, QMessageBox,
                               QToolBar, QLineEdit, QPushButton, QLabel)
from PySide2.QtCore import Qt
from ui.thumbnail__sidebar import ThumbnailSidebar
from ui.pdf__reader__view import PdfReaderView
from core.pdf__document import PdfDocument
import fitz

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Modern PDF Reader")
        self.resize(1200, 800)
        self.pdf_document = PdfDocument()
        self.__setup__ui()
        self.__setup__menu()
        self.__setup__toolbar()

    def __setup__ui(self):
        splitter = QSplitter(Qt.Horizontal)
        self.sidebar = ThumbnailSidebar()
        self.reader_view = PdfReaderView()
        
        splitter.addWidget(self.sidebar)
        splitter.addWidget(self.reader_view)
        
        splitter.setStretchFactor(0, 0) 
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([200, 1000]) 

        central_widget = QWidget()
        layout = QHBoxLayout(central_widget)
        layout.addWidget(splitter)
        self.setCentralWidget(central_widget)
        
        self.sidebar.page_selected.connect(self.reader_view.show_page)

    def __setup__menu(self):
        menu_bar = self.menuBar()
        file_menu = menu_bar.addMenu("File")
        
        open_action = QAction("Open PDF", self)
        open_action.triggered.connect(self.__open__pdf)
        
        save_action = QAction("Save PDF", self)
        save_action.triggered.connect(self.__save__pdf)
        
        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self.close)
        
        file_menu.addAction(open_action)
        file_menu.addAction(save_action)
        file_menu.addSeparator()
        file_menu.addAction(exit_action)

    def __setup__toolbar(self):
        toolbar = QToolBar("处理工具栏", self)
        toolbar.setMovable(False)
        toolbar.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.addToolBar(toolbar)

        start_label = QLabel("开始页:", self)
        self.start_page_input = QLineEdit(self)
        self.start_page_input.setPlaceholderText("例如: 1")
        self.start_page_input.setFixedWidth(80)

        end_label = QLabel("结束页:", self)
        self.end_page_input = QLineEdit(self)
        self.end_page_input.setPlaceholderText("例如: 10")
        self.end_page_input.setFixedWidth(80)

        self.process_button = QPushButton("开始处理", self)
        self.process_button.clicked.connect(self.__on__process__clicked)

        toolbar.addWidget(start_label)
        toolbar.addWidget(self.start_page_input)
        toolbar.addSeparator()
        toolbar.addWidget(end_label)
        toolbar.addWidget(self.end_page_input)
        toolbar.addSeparator()
        toolbar.addWidget(self.process_button)

    def __save__pdf(self):
        if self.pdf_document.doc is None:
            QMessageBox.warning(self, "提示", "当前没有打开的PDF文档！")
            return
        file_path, _ = QFileDialog.getSaveFileName(self, "Save PDF", "", "PDF Files (*.pdf)")
        if file_path:
            try:
                self.pdf_document.doc.save(file_path)
                QMessageBox.information(self, "保存成功", f"文件已成功保存至:\n{file_path}")
            except Exception as e:
                QMessageBox.critical(self, "保存失败", f"保存文件时发生错误:\n{str(e)}")

    def __on__process__clicked(self):
        start_text = self.start_page_input.text().strip()
        end_text = self.end_page_input.text().strip()

        if not start_text or not end_text:
            QMessageBox.warning(self, "输入错误", "请输入有效的开始页和结束页！")
            return

        try:
            start_page = int(start_text)
            end_page = int(end_text)
            total_pages = self.pdf_document.page_count

            if total_pages == 0:
                QMessageBox.warning(self, "无文档", "请先打开一个PDF文件！")
                return

            if start_page < 1 or end_page > total_pages or start_page > end_page:
                QMessageBox.warning(
                    self, 
                    "范围错误", 
                    f"页码范围无效！当前文档共 {total_pages} 页。"
                )
                return

            doc = self.pdf_document.doc
            for i in range(start_page - 1, end_page):
                page = doc[i]
                rect = page.rect
                new_rect = fitz.Rect(rect.x0, rect.y0, rect.x0 + rect.width * 2, rect.y1)
                page.set_mediabox(new_rect)
                page.set_cropbox(new_rect)

            self.sidebar.load_thumbnails(self.pdf_document)
            self.reader_view.set_document(self.pdf_document)
            if self.pdf_document.page_count > 0:
                self.reader_view.show_page(start_page - 1)

            QMessageBox.information(
                self, 
                "处理完成", 
                f"成功处理第 {start_page} 页到第 {end_page} 页！\n页面宽度已成功加倍。"
            )

        except ValueError:
            QMessageBox.warning(self, "输入错误", "页码必须是整数！")
        except Exception as e:
            QMessageBox.critical(self, "处理失败", f"发生未知错误:\n{str(e)}")

    def __open__pdf(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select PDF File", "", "PDF Files (*.pdf)")
        if not file_path:
            return
        success = self.pdf_document.load_document(file_path)
        if not success:
            QMessageBox.warning(self, "Error", "Failed to load PDF file")
            return
        self.reader_view.set_document(self.pdf_document)
        self.sidebar.load_thumbnails(self.pdf_document)
        if self.pdf_document.page_count > 0:
            self.reader_view.show_page(0)

    def closeEvent(self, event):
        self.pdf_document.close_document()
        event.accept()