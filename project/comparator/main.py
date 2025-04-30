import sys
import os
# Change the import to use the local module directly
from comparator import ColumnComparator
import json
import pandas as pd
from datetime import datetime
import pathlib

def get_test_data_dir():
    """Get the path to the test data directory"""
    current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(current_dir, 'tests', 'test_data')

def create_results_dir(source_dir):
    """Create a results directory based on the source directory name"""
    # Get the name of the source directory
    source_name = os.path.basename(os.path.normpath(source_dir))
    
    # Create a base results directory if it doesn't exist
    base_results_dir = "comparison_results"
    if not os.path.exists(base_results_dir):
        os.makedirs(base_results_dir)
    
    # Create a subdirectory for this source
    source_results_dir = os.path.join(base_results_dir, source_name)
    if not os.path.exists(source_results_dir):
        os.makedirs(source_results_dir)
    
    # Create a timestamp-based directory for this run
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = os.path.join(source_results_dir, timestamp)
    os.makedirs(run_dir)
    
    # Create a metadata file with information about the source
    metadata = {
        "source_directory": str(pathlib.Path(source_dir).resolve()),
        "analysis_timestamp": timestamp,
        "files_analyzed": len([f for f in os.listdir(source_dir) if f.lower().endswith('.xlsx')])
    }
    
    with open(os.path.join(run_dir, "metadata.json"), 'w') as f:
        json.dump(metadata, f, indent=4)
    
    return run_dir

def main():
    print("\nExcel Column Comparison Tool")
    print("----------------------------")
    print("1. Use test data directory")
    print("2. Specify your own directory")
    
    while True:
        choice = input("\nEnter your choice (1 or 2): ").strip()
        if choice in ['1', '2']:
            break
        print("Invalid choice. Please enter 1 or 2.")

    if choice == '1':
        directory = get_test_data_dir()
        print(f"\nUsing test data directory: {directory}")
    else:
        directory = input("\nEnter the path to your directory containing Excel files: ").strip()
        if not os.path.exists(directory):
            print(f"Error: Directory '{directory}' does not exist.")
            sys.exit(1)

    try:
        # Create results directory for this run
        results_dir = create_results_dir(directory)
        
        comparator = ColumnComparator(directory)
        result = comparator.compare()
        
        if not result['files']:
            print(f"\nNo Excel files found in directory: {directory}")
            sys.exit(1)

        # Create and save the comparison tables
        comparison_table = comparator.create_comparison_table()
        transposed_table = comparator.create_transposed_comparison_table()
        
        # Save all results to the run directory
        output_json = os.path.join(results_dir, 'comparison_results.json')
        output_excel = os.path.join(results_dir, 'comparison_results.xlsx')
        output_excel_v2 = os.path.join(results_dir, 'comparison_results_v2.xlsx')
        
        with open(output_json, 'w') as f:
            json.dump(result, f, indent=4)

        with pd.ExcelWriter(output_excel) as writer:
            comparison_table.to_excel(writer, sheet_name='Columns as Rows')
            transposed_table.to_excel(writer, sheet_name='Files as Rows', index=False)
            
        transposed_table.to_excel(output_excel_v2, index=False)
        
        # Display both tables in console
        print("\nColumn Comparison Table (Columns as Rows):")
        print("------------------------------------------")
        print(comparison_table.to_string())
        
        print("\nColumn Comparison Table (Files as Rows):")
        print("----------------------------------------")
        print(transposed_table.to_string())
        
        print(f"\nResults saved in: {results_dir}")
        print(f"Files generated:")
        print(f"- Excel format v1: comparison_results.xlsx (includes both table views)")
        print(f"- Excel format v2: comparison_results_v2.xlsx (files as rows view)")
        print(f"- JSON format: comparison_results.json")
        print(f"- Metadata: metadata.json")

        if result['comparisons']:
            print("\nColumn Changes Between Files:")
            print("-----------------------------")
            for comp in result['comparisons']:
                print(f"\nComparing {comp['previous_file']} → {comp['current_file']}")
                if comp['added']:
                    print(f"Added columns: {', '.join(comp['added'])}")
                if comp['removed']:
                    print(f"Removed columns: {', '.join(comp['removed'])}")
                if not comp['added'] and not comp['removed']:
                    print("No changes in columns")

    except Exception as e:
        print(f"\nError: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
