import fitz
from utils.__file__helper import FileHelper

class PdfDocument:
    def __init__(self):
        self.doc = None
        self.file_path = ""
        self.page_count = 0

    def load_document(self, file_path: str) -> bool:
        if not FileHelper.check_pdf_file(file_path):
            return False
        try:
            self.doc = fitz.open(file_path)
            self.file_path = file_path
            self.page_count = self.doc.page_count
            return True
        except Exception as e:
            print(f"Load pdf error: {e}")
            return False

    def get_page(self, page_index: int):
        if self.doc is None:
            return None
        if 0 <= page_index < self.page_count:
            return self.doc.load_page(page_index)
        return None

    def close_document(self):
        if self.doc is not None:
            self.doc.close()
            self.doc = None
            self.file_path = ""
            self.page_count = 0