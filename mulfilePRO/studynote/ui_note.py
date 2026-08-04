# -*- coding: utf-8 -*-

from PySide2 import QtCore, QtGui, QtWidgets

class Ui_NoteApp(object):
    def setupUi(self, MainWindow):
        MainWindow.setObjectName("MainWindow")
        MainWindow.resize(1300, 800)
        
        self.centralwidget = QtWidgets.QWidget(MainWindow)
        self.centralwidget.setObjectName("centralwidget")
        
        self.mainLayout = QtWidgets.QHBoxLayout(self.centralwidget)
        self.mainLayout.setContentsMargins(0, 0, 0, 0)
        self.mainLayout.setSpacing(0)
        
        # 1. 左侧边栏（笔记本分类树 + 标签过滤面板）
        self.sidebarWidget = QtWidgets.QWidget(self.centralwidget)
        self.sidebarWidget.setMaximumWidth(260)
        self.sidebarWidget.setMinimumWidth(210)
        self.sidebarLayout = QtWidgets.QVBoxLayout(self.sidebarWidget)
        self.sidebarLayout.setContentsMargins(10, 10, 10, 10)
        self.sidebarLayout.setSpacing(8)
        
        self.searchLineEdit = QtWidgets.QLineEdit(self.sidebarWidget)
        self.searchLineEdit.setPlaceholderText("全局搜索笔记... (Ctrl+F)")
        self.sidebarLayout.addWidget(self.searchLineEdit)
        
        self.notebookBtnLayout = QtWidgets.QHBoxLayout()
        self.newNotebookBtn = QtWidgets.QPushButton("📁 新建笔记本", self.sidebarWidget)
        self.delNotebookBtn = QtWidgets.QPushButton("🗑️", self.sidebarWidget)
        self.delNotebookBtn.setMaximumWidth(40)
        self.notebookBtnLayout.addWidget(self.newNotebookBtn)
        self.notebookBtnLayout.addWidget(self.delNotebookBtn)
        self.sidebarLayout.addLayout(self.notebookBtnLayout)
        
        self.treeWidget = QtWidgets.QTreeWidget(self.sidebarWidget)
        self.treeWidget.setHeaderHidden(True)
        self.treeWidget.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.sidebarLayout.addWidget(self.treeWidget)
        
        self.tagLabelTitle = QtWidgets.QLabel("🏷️ 标签快捷过滤", self.sidebarWidget)
        self.tagLabelTitle.setStyleSheet("font-weight: bold; color: #666; margin-top: 5px;")
        self.sidebarLayout.addWidget(self.tagLabelTitle)
        
        self.tagListWidget = QtWidgets.QListWidget(self.sidebarWidget)
        self.tagListWidget.setMaximumHeight(130)
        self.sidebarLayout.addWidget(self.tagListWidget)
        
        self.mainLayout.addWidget(self.sidebarWidget)
        
        # 2. 中间笔记列表
        self.noteListWidget = QtWidgets.QWidget(self.centralwidget)
        self.noteListWidget.setMaximumWidth(280)
        self.noteListWidget.setMinimumWidth(220)
        self.noteListLayout = QtWidgets.QVBoxLayout(self.noteListWidget)
        self.noteListLayout.setContentsMargins(10, 10, 10, 10)
        
        self.btnLayout = QtWidgets.QHBoxLayout()
        self.newNoteBtn = QtWidgets.QPushButton("新建笔记 (Ctrl+N)", self.noteListWidget)
        self.delNoteBtn = QtWidgets.QPushButton("删除", self.noteListWidget)
        self.btnLayout.addWidget(self.newNoteBtn)
        self.btnLayout.addWidget(self.delNoteBtn)
        self.noteListLayout.addLayout(self.btnLayout)
        
        self.listWidget = QtWidgets.QListWidget(self.noteListWidget)
        self.noteListLayout.addWidget(self.listWidget)
        
        self.mainLayout.addWidget(self.noteListWidget)
        
        # 3. 右侧多标签页编辑器区
        self.editorWidget = QtWidgets.QWidget(self.centralwidget)
        self.editorLayout = QtWidgets.QVBoxLayout(self.editorWidget)
        self.editorLayout.setContentsMargins(15, 15, 15, 15)
        self.editorLayout.setSpacing(10)
        
        # 【新增】顶部公共系统控制栏（暗黑模式、导出等全局功能）
        self.topControlLayout = QtWidgets.QHBoxLayout()
        self.topControlLayout.addSpacerItem(QtWidgets.QSpacerItem(10, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum))
        self.themeBtn = QtWidgets.QPushButton("🌙 暗黑模式", self.editorWidget)
        self.exportBtn = QtWidgets.QPushButton("📤 导出当前", self.editorWidget)
        self.topControlLayout.addWidget(self.exportBtn)
        self.topControlLayout.addWidget(self.themeBtn)
        self.editorLayout.addLayout(self.topControlLayout)
        
        # 【新增】多标签页管理器 (Tab Widget)，支持关闭标签页
        self.tabWidget = QtWidgets.QTabWidget(self.editorWidget)
        self.tabWidget.setTabsClosable(True)
        self.tabWidget.setMovable(True)
        self.editorLayout.addWidget(self.tabWidget)
        
        self.mainLayout.addWidget(self.editorWidget)
        
        MainWindow.setCentralWidget(self.centralwidget)
        
        self.statusbar = QtWidgets.QStatusBar(MainWindow)
        MainWindow.setStatusBar(self.statusbar)
        
        self.retranslateUi(MainWindow)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle("PySide2 现代化高级笔记软件（多标签页多开版）")