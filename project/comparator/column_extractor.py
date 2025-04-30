from openpyxl import load_workbook
import os

class ExcelColumnExtractor:
    def __init__(self, filepath):
        self.filepath = filepath

    def get_columns(self):
        if not os.path.isfile(self.filepath):
            raise FileNotFoundError(f"No such file: {self.filepath}")

        wb = load_workbook(self.filepath, read_only=True)
        ws = wb.active  # Assume first sheet
        header = ws[1]  # First row is header
        columns = [cell.value for cell in header if cell.value is not None]
        return columns

