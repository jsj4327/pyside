import fitz
from utils.\u005f\u005ffile\u005f\u005fhelper import FileHelper

class PdfDocument:
    def \u005f\u005finit\u005f\u005f(self):
        self.doc = None
        self.file\u005fpath = ""
        self.page\u005fcount = 0

    def load\u005fdocument(self, file\u005fpath: str) -> bool:
        if not FileHelper.check\u005fpdf\u005ffile(file\u005fpath):
            return False
        try:
            self.doc = fitz.open(file\u005fpath)
            self.file\u005fpath = file\u005fpath
            self.page\u005fcount = self.doc.page\u005fcount
            return True
        except Exception as e:
            print(f"Load pdf error: {e}")
            return False

    def get\u005fpage(self, page\u005findex: int):
        if self.doc is None:
            return None
        if 0 <= page\u005findex < self.page\u005fcount:
            return self.doc.load\u005fpage(page\u005findex)
        return None

    def close\u005fdocument(self):
        if self.doc is not None:
            self.doc.close()
            self.doc = None
            self.file\u005fpath = ""
            self.page\u005fcount = 0