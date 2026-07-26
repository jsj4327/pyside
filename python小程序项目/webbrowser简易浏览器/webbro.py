import sys
import os
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton
from PyQt5.QtGui import QIcon
from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEnginePage
from PyQt5.QtCore import QUrl

class CustomBrowserPage(QWebEnginePage):
    """自定义页面：在页面加载时自动注入现代 API 垫片"""
    def __init__(self, profile, parent=None):
        super().__init__(profile, parent)
        # 监听网页加载进度，当页面开始加载或完成时注入 JS
        self.loadFinished.connect(self.inject_polyfills)

    def userAgentForUrl(self, url):
        # 伪装成较新版本的 Chrome 桌面浏览器
        return "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

    def inject_polyfills(self, ok):
        """当页面加载时，动态注入补丁代码"""
        if not ok:
            return
            
        polyfill_code = """
        (function() {
            if (typeof window.__intl_patched === 'undefined') {
                if (typeof Intl !== 'undefined' && !Intl.RelativeTimeFormat) {
                    Intl.RelativeTimeFormat = function(locale, options) {
                        this.locale = locale;
                        this.options = options;
                    };
                    Intl.RelativeTimeFormat.prototype.format = function(value, unit) {
                        return value + " " + unit;
                    };
                    Intl.RelativeTimeFormat.prototype.formatToParts = function(value, unit) {
                        return [{type: 'integer', value: value.toString()}, {type: 'literal', value: ' ' + unit}];
                    };
                    console.log("【Python 动态注入】已成功补全 Intl.RelativeTimeFormat 垫片！");
                }
                window.__intl_patched = true;
            }
        })();
        """
        # 直接在当前页面上下文中执行该 JS 脚本
        self.runJavaScript(polyfill_code)

class SimpleOnlineBrowser(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("智能兼容在线浏览器")
        self.resize(1200, 800)
        
        # 绝对路径加载图标
        current_dir = os.path.dirname(os.path.abspath(__file__))
        icon_path = os.path.join(current_dir, "firegrep.png")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
            
        central_widget = QWidget()
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(5, 5, 5, 5)
        
        # 导航栏
        nav_layout = QHBoxLayout()
        self.url_edit = QLineEdit()
        self.url_edit.setPlaceholderText("输入网址 (如: https://gemini.google.com) 并回车...")
        self.url_edit.returnPressed.connect(self.navigate_to_url)
        nav_layout.addWidget(self.url_edit)
        
        self.btn_go = QPushButton("访问 🚀")
        self.btn_go.clicked.connect(self.navigate_to_url)
        nav_layout.addWidget(self.btn_go)
        main_layout.addLayout(nav_layout)
        
        # 浏览器视图核心
        self.browser = QWebEngineView()
        profile = self.browser.page().profile()
        custom_page = CustomBrowserPage(profile, self.browser)
        self.browser.setPage(custom_page)
        
        self.browser.urlChanged.connect(lambda qurl: self.url_edit.setText(qurl.toString()))
        main_layout.addWidget(self.browser)
        
        self.setCentralWidget(central_widget)
        
        # 默认访问 Gemini
        self.browser.setUrl(QUrl("https://gemini.google.com"))

    def navigate_to_url(self):
        url_str = self.url_edit.text().strip()
        if not url_str.startswith("http://") and not url_str.startswith("https://"):
            url_str = "https://" + url_str
        self.browser.setUrl(QUrl(url_str))

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = SimpleOnlineBrowser()
    window.show()
    sys.exit(app.exec_())
