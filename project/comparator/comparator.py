import os
from column_extractor import ExcelColumnExtractor
import pandas as pd

class ColumnComparator:
    def __init__(self, directory):
        self.directory = directory

    def _get_excel_files(self):
        files = os.listdir(self.directory)
        excel_files = [f for f in files if f.lower().endswith(".xlsx")]
        excel_files.sort()  # Sort alphabetically; assume chronological order
        return excel_files

    def create_comparison_table(self):
        """Creates a DataFrame showing columns across all files with their status"""
        files = self._get_excel_files()
        if not files:
            return pd.DataFrame()

        # Get columns for each file
        file_columns = []
        all_columns = set()
        for f in files:
            filepath = os.path.join(self.directory, f)
            extractor = ExcelColumnExtractor(filepath)
            cols = set(extractor.get_columns())
            file_columns.append((f, cols))
            all_columns.update(cols)

        # Create a DataFrame with all unique columns as index
        df = pd.DataFrame(index=sorted(list(all_columns)))
        
        # Fill the DataFrame with column presence/absence
        for file_name, columns in file_columns:
            df[file_name] = df.index.isin(columns)
            # Convert boolean to more readable format
            df[file_name] = df[file_name].map({True: "✓", False: ""})

        return df

    def create_transposed_comparison_table(self):
        """Creates a DataFrame with files as rows and columns as column headers"""
        files = self._get_excel_files()
        if not files:
            return pd.DataFrame()

        # Get columns for each file
        file_columns = []
        all_columns = set()
        for f in files:
            filepath = os.path.join(self.directory, f)
            extractor = ExcelColumnExtractor(filepath)
            cols = set(extractor.get_columns())
            file_columns.append((f, cols))
            all_columns.update(cols)

        # Create DataFrame with files as rows and columns as column headers
        data = []
        for file_name, columns in file_columns:
            row = {'File': file_name}
            for col in sorted(list(all_columns)):
                row[col] = "✓" if col in columns else ""
            data.append(row)
        
        df = pd.DataFrame(data)
        # Set File as the first column
        cols = ['File'] + [col for col in df.columns if col != 'File']
        df = df[cols]
        
        return df

    def compare(self):
        files = self._get_excel_files()
        if not files:
            return {"files": [], "comparisons": []}

        file_columns = []
        for f in files:
            filepath = os.path.join(self.directory, f)
            extractor = ExcelColumnExtractor(filepath)
            cols = set(extractor.get_columns())
            file_columns.append((f, cols))

        comparisons = []
        for i in range(1, len(file_columns)):
            prev_file, prev_cols = file_columns[i-1]
            curr_file, curr_cols = file_columns[i]
            added = curr_cols - prev_cols
            removed = prev_cols - curr_cols
            comparisons.append({
                "previous_file": prev_file,
                "current_file": curr_file,
                "added": sorted(list(added)),
                "removed": sorted(list(removed))
            })

        return {
            "files": [{"file": f, "columns": sorted(list(c))} for f, c in file_columns],
            "comparisons": comparisons
        }
