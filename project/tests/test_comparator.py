import unittest
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from comparator.comparator import ColumnComparator

class TestColumnComparator(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.test_data_dir = os.path.join(os.path.dirname(__file__), 'test_data')

    def test_empty_directory(self):
        # Create a temporary empty directory
        empty_dir = os.path.join(self.test_data_dir, 'empty')
        os.makedirs(empty_dir, exist_ok=True)
        
        comparator = ColumnComparator(empty_dir)
        result = comparator.compare()
        
        self.assertEqual(result, {"files": [], "comparisons": []})
        
        # Cleanup
        os.rmdir(empty_dir)

    def test_compare_files(self):
        comparator = ColumnComparator(self.test_data_dir)
        result = comparator.compare()

        print("\nTest Compare Files Result:")
        print(f"Files found: {len(result['files'])}")
        for file_info in result["files"]:
            print(f"File: {file_info['file']}")
            print(f"Columns: {file_info['columns']}")

        print("\nComparisons:")
        for comp in result["comparisons"]:
            print(f"\nComparing {comp['previous_file']} -> {comp['current_file']}")
            print(f"Added columns: {comp['added']}")
            print(f"Removed columns: {comp['removed']}")

        # Test files list
        self.assertEqual(len(result["files"]), 3)
        self.assertEqual(result["files"][0]["columns"], ['Age', 'Email', 'Name'])
        self.assertEqual(result["files"][1]["columns"], ['Age', 'Email', 'Name', 'Phone'])
        self.assertEqual(result["files"][2]["columns"], ['Address', 'Email', 'Name', 'Phone'])

        # Test comparisons
        self.assertEqual(len(result["comparisons"]), 2)
        
        # Test first comparison (file1 -> file2)
        self.assertEqual(result["comparisons"][0]["added"], ['Phone'])
        self.assertEqual(result["comparisons"][0]["removed"], [])
        
        # Test second comparison (file2 -> file3)
        self.assertEqual(result["comparisons"][1]["added"], ['Address'])
        self.assertEqual(result["comparisons"][1]["removed"], ['Age'])

if __name__ == '__main__':
    unittest.main() 