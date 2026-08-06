from PySide2.QtWidgets import (QMainWindow, QSplitter, QWidget, QHBoxLayout,
                               QMenuBar, QMenu, QAction, QFileDialog, QMessageBox,
                               QToolBar, QLineEdit, QPushButton, QLabel)
from PySide2.QtCore import Qt
from ui.thumbnail\u005f\u005fsidebar import ThumbnailSidebar
from ui.pdf\u005f\u005freader\u005f\u005fview import PdfReaderView
from core.pdf\u005f\u005fdocument import PdfDocument
import fitz

class MainWindow(QMainWindow):
    def \u005f\u005finit\u005f\u005f(self):
        super().\u005f\u005finit\u005f\u005f()
        self.setWindowTitle("Modern PDF Reader")
        self.resize(1200, 800)
        self.pdf\u005fdocument = PdfDocument()
        self.\u005f\u005fsetup\u005f\u005fui()
        self.\u005f\u005fsetup\u005f\u005fmenu()
        self.\u005f\u005fsetup\u005f\u005ftoolbar()

    def \u005f\u005fsetup\u005f\u005fui(self):
        splitter = QSplitter(Qt.Horizontal)
        self.sidebar = ThumbnailSidebar()
        self.reader\u005fview = PdfReaderView()
        
        splitter.addWidget(self.sidebar)
        splitter.addWidget(self.reader\u005fview)
        
        # 设置初始宽度比例：左侧固定 200px，右侧自适应
        splitter.setStretchFactor(0, 0) 
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([200, 1000]) 

        central\u005fwidget = QWidget()
        layout = QHBoxLayout(central\u005fwidget)
        layout.addWidget(splitter)
        self.setCentralWidget(central\u005fwidget)
        
        self.sidebar.page\u005fselected.connect(self.reader\u005fview.show\u005fpage)

    def \u005f\u005fsetup\u005f\u005fmenu(self):
        menu\u005fbar = self.menuBar()
        file\u005fmenu = menu\u005fbar.addMenu("File")
        open\u005faction = QAction("Open PDF", self)
        open\u005faction.triggered.connect(self.\u005f\u005fopen\u005f\u005fpdf)
        exit\u005faction = QAction("Exit", self)
        exit\u005faction.triggered.connect(self.close)
        file\u005fmenu.addAction(open\u005faction)
        file\u005fmenu.addAction(exit\u005faction)

    def \u005f\u005fsetup\u005f\u005ftoolbar(self):
        """设置顶部工具栏"""
        toolbar = QToolBar("处理工具栏", self)
        toolbar.setMovable(False)
        toolbar.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.addToolBar(toolbar)

        # 开始页文本框
        start\u005flabel = QLabel("开始页:", self)
        self.start\u005fpage\u005finput = QLineEdit(self)
        self.start\u005fpage\u005finput.setPlaceholderText("例如: 1")
        self.start\u005fpage\u005finput.setFixedWidth(80)

        # 结束页文本框
        end\u005flabel = QLabel("结束页:", self)
        self.end\u005fpage\u005finput = QLineEdit(self)
        self.end\u005fpage\u005finput.setPlaceholderText("例如: 10")
        self.end\u005fpage\u005finput.setFixedWidth(80)

        # 开始处理按钮
        self.process\u005fbutton = QPushButton("开始处理", self)
        self.process\u005fbutton.clicked.connect(self.\u005f\u005fon\u005f\u005fprocess\u005f\u005fclicked)

        # 将控件添加到工具栏
        toolbar.addWidget(start\u005flabel)
        toolbar.addWidget(self.start\u005fpage\u005finput)
        toolbar.addSeparator()
        toolbar.addWidget(end\u005flabel)
        toolbar.addWidget(self.end\u005fpage\u005finput)
        toolbar.addSeparator()
        toolbar.addWidget(self.process\u005fbutton)

    def \u005f\u005fon\u005f\u005fprocess\u005f\u005fclicked(self):
        """处理按钮的点击事件：将指定范围的页面横向扩宽一倍，原内容在左，右侧留空，并原地替换"""
        start\u005ftext = self.start\u005fpage\u005finput.text().strip()
        end\u005ftext = self.end\u005fpage\u005finput.text().strip()

        if not start\u005ftext or not end\u005ftext:
            QMessageBox.warning(self, "输入错误", "请输入有效的开始页和结束页！")
            return

        try:
            start\u005fpage = int(start\u005ftext)
            end\u005fpage = int(end\u005ftext)
            total\u005fpages = self.pdf\u005fdocument.page\u005fcount

            if total\u005fpages == 0:
                QMessageBox.warning(self, "无文档", "请先打开一个PDF文件！")
                return

            # 校验页码范围
            if start\u005fpage < 1 or end\u005fpage > total\u005fpages or start\u005fpage > end\u005fpage:
                QMessageBox.warning(
                    self, 
                    "范围错误", 
                    f"页码范围无效！当前文档共 {total\u005fpages} 页。"
                )
                return

            # 获取当前文档对象
            doc = self.pdf\u005fdocument.doc
            
            # 核心修复：
            # 1. 在循环外记录要处理的页码索引列表，避免在循环中修改文档结构导致索引错乱
            # 2. 使用新页面替换旧页面时，先插入新页面，再删除旧页面，并正确计算新页面的索引
            pages\u005fto\u005fprocess = list(range(start\u005fpage - 1, end\u005fpage))
            
            for i in pages\u005fto\u005fprocess:
                page = doc[i]
                # 获取原始页面的尺寸
                rect = page.rect
                
                # 创建新页面，宽度为原来的两倍，高度保持不变
                new\u005frect = fitz.Rect(0, 0, rect.width * 2, rect.height)
                
                # 在当前页后面插入新页面
                new\u005fpage\u005findex = doc.new\u005fpage(pno=i+1, width=new\u005frect.width, height=new\u005frect.height)
                new\u005fpage = doc[new\u005fpage\u005findex]
                
                # 将原页面内容渲染到新页面的左半部分
                # 注意：此时原页面的索引仍然是 i
                new\u005fpage.show\u005fpdf\u005fpage(rect, doc, i)
                
                # 删除原来的页面（索引为 i 的页面）
                doc.delete\u005fpage(i)
                
                # 删除后，新页面的索引变为 i（因为后面的页面都往前移了一位）

            # 更新模型状态
            self.pdf\u005fdocument.page\u005fcount = len(doc)
            
            # 刷新左侧缩略图和右侧阅读区
            self.sidebar.load\u005fthumbnails(self.pdf\u005fdocument)
            if self.pdf\u005fdocument.page\u005fcount > 0:
                self.reader\u005fview.show\u005fpage(start\u005fpage - 1)

            QMessageBox.information(
                self, 
                "处理完成", 
                f"成功处理第 {start\u005fpage} 页到第 {end\u005fpage} 页！\n页面已原地替换。"
            )

        except ValueError:
            QMessageBox.warning(self, "输入错误", "页码必须是整数！")
        except Exception as e:
            QMessageBox.critical(self, "处理失败", f"发生未知错误:\n{str(e)}")

    def \u005f\u005fopen\u005f\u005fpdf(self):
        file\u005fpath, _ = QFileDialog.getOpenFileName(self, "Select PDF File", "", "PDF Files (*.pdf)")
        if not file\u005fpath:
            return
        success = self.pdf\u005fdocument.load\u005fdocument(file\u005fpath)
        if not success:
            QMessageBox.warning(self, "Error", "Failed to load PDF file")
            return
        self.reader\u005fview.set\u005fdocument(self.pdf\u005fdocument)
        self.sidebar.load\u005fthumbnails(self.pdf\u005fdocument)
        if self.pdf\u005fdocument.page\u005fcount > 0:
            self.reader\u005fview.show\u005fpage(0)

    def closeEvent(self, event):
        self.pdf\u005fdocument.close\u005fdocument()
        event.accept()