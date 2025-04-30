from openpyxl import Workbook
import os

def create_test_excel(filename, columns):
    wb = Workbook()
    ws = wb.active
    for col_num, header in enumerate(columns, 1):
        ws.cell(row=1, column=col_num, value=header)
    wb.save(filename)

def create_test_files():
    # Create test_data directory if it doesn't exist
    test_data_dir = os.path.join(os.path.dirname(__file__), 'test_data')
    os.makedirs(test_data_dir, exist_ok=True)

    # Create test files with different column combinations
    files_data = {
        'file1.xlsx': ['Name', 'Age', 'Email'],
        'file2.xlsx': ['Name', 'Age', 'Email', 'Phone'],
        'file3.xlsx': ['Name', 'Email', 'Phone', 'Address']
    }

    for filename, columns in files_data.items():
        filepath = os.path.join(test_data_dir, filename)
        create_test_excel(filepath, columns)

if __name__ == "__main__":
    create_test_files() 