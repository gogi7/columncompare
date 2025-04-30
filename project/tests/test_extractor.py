# Empty file 

import unittest
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from comparator.column_extractor import ExcelColumnExtractor

class TestExcelColumnExtractor(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.test_data_dir = os.path.join(os.path.dirname(__file__), 'test_data')
        
    def test_get_columns_file1(self):
        extractor = ExcelColumnExtractor(os.path.join(self.test_data_dir, 'file1.xlsx'))
        columns = extractor.get_columns()
        print(f"\nFile1 columns: {columns}")
        self.assertEqual(columns, ['Name', 'Age', 'Email'])

    def test_get_columns_file2(self):
        extractor = ExcelColumnExtractor(os.path.join(self.test_data_dir, 'file2.xlsx'))
        columns = extractor.get_columns()
        self.assertEqual(columns, ['Name', 'Age', 'Email', 'Phone'])

    def test_file_not_found(self):
        extractor = ExcelColumnExtractor('nonexistent.xlsx')
        with self.assertRaises(FileNotFoundError):
            extractor.get_columns()

if __name__ == '__main__':
    unittest.main() 