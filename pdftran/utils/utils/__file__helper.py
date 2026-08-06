import os
from pathlib import Path

class FileHelper:
    @staticmethod
    def check\u005fpdf\u005ffile(file\u005fpath: str) -> bool:
        if not os.path.exists(file\u005fpath):
            return False
        suffix = Path(file\u005fpath).suffix.lower()
        return suffix == ".pdf"

    @staticmethod
    def get\u005ffile\u005fname(file\u005fpath: str) -> str:
        return Path(file\u005fpath).name