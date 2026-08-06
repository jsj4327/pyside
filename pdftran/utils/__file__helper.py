import os
from pathlib import Path

class FileHelper:
    @staticmethod
    def check_pdf_file(file_path: str) -> bool:
        if not os.path.exists(file_path):
            return False
        suffix = Path(file_path).suffix.lower()
        return suffix == ".pdf"

    @staticmethod
    def get_file_name(file_path: str) -> str:
        return Path(file_path).name