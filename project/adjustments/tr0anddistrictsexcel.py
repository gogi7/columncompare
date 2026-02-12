import os
import pandas as pd
from tqdm import tqdm

def process_excel_files(directory_path, mode="modify"):
    """
    Processes or checks all Excel files in the given directory.

    Args:
        directory_path (str): The path to the directory containing Excel files.
        mode (str): "modify" to change files, "check" to report status.
    """
    if not os.path.isdir(directory_path):
        print(f"Error: Directory not found: {directory_path}")
        return

    excel_files = [
        f for f in os.listdir(directory_path)
        if f.lower().endswith((".xlsx", ".xls"))
    ]

    if not excel_files:
        print(f"No Excel files found in {directory_path}")
        return

    print(f"Found {len(excel_files)} Excel files to process in '{mode}' mode.")

    files_needing_attention = []

    for filename in tqdm(excel_files, desc=f"Processing Excel files ({mode})", unit="file"):
        file_path = os.path.join(directory_path, filename)
        issues_found_in_file = []

        try:
            # Try reading with openpyxl first, then xlrd if it's an old .xls file
            try:
                df = pd.read_excel(file_path, engine='openpyxl')
            except Exception:
                try:
                    df = pd.read_excel(file_path, engine='xlrd')
                except Exception as e_xlrd:
                    tqdm.write(f"  Error: Could not read {filename} with any engine: {e_xlrd}")
                    files_needing_attention.append(f"{filename} (Could not read)")
                    continue

            # --- Common Column Checks ---
            tr_col_exists = "TR" in df.columns
            zone_col_exists = "Zone/Regions" in df.columns

            # --- MODE: MODIFY ---
            if mode == "modify":
                modified_in_script = False

                # 1. Process "TR" column
                if tr_col_exists:
                    empty_tr_count = df["TR"].isnull().sum()
                    if empty_tr_count > 0:
                        df["TR"].fillna(0, inplace=True)
                        tqdm.write(f"  {filename}: Filled {empty_tr_count} empty cells in 'TR' with 0.")
                        modified_in_script = True
                    # Ensure integer type if only 0s and 1s
                    if all(val in [0, 1] for val in df["TR"].dropna().unique()):
                         df["TR"] = df["TR"].astype(int)
                else:
                    tqdm.write(f"  {filename}: Warning - Column 'TR' not found.")

                # 2. Process "Zone/Regions" column
                if zone_col_exists:
                    replacements_made_count = 0
                    original_vic_count = (df["Zone/Regions"] == "VIC").sum()
                    original_auk_count = (df["Zone/Regions"] == "AUK").sum()

                    df["Zone/Regions"] = df["Zone/Regions"].replace({"VIC": "VSAT", "AUK": "NZ"})

                    if original_vic_count > 0:
                        tqdm.write(f"  {filename}: Replaced {original_vic_count} 'VIC' with 'VSAT' in 'Zone/Regions'.")
                        replacements_made_count += original_vic_count
                    if original_auk_count > 0:
                        tqdm.write(f"  {filename}: Replaced {original_auk_count} 'AUK' with 'NZ' in 'Zone/Regions'.")
                        replacements_made_count += original_auk_count

                    if replacements_made_count > 0:
                        modified_in_script = True
                else:
                    tqdm.write(f"  {filename}: Warning - Column 'Zone/Regions' not found.")

                if modified_in_script:
                    try:
                        df.to_excel(file_path, index=False, engine='openpyxl' if filename.lower().endswith(".xlsx") else None)
                        # tqdm.write(f"  {filename}: Saved changes.") # Can be a bit too verbose
                    except Exception as save_err:
                        tqdm.write(f"  {filename}: ERROR SAVING FILE - {save_err}. File might be open or permissions issue.")
                        files_needing_attention.append(f"{filename} (Error saving)")


            # --- MODE: CHECK ---
            elif mode == "check":
                if tr_col_exists:
                    empty_tr_values = df["TR"].isnull().sum()
                    if empty_tr_values > 0:
                        issues_found_in_file.append(f"'TR' column has {empty_tr_values} empty value(s)")
                else:
                    issues_found_in_file.append("'TR' column not found")

                if zone_col_exists:
                    vic_values = (df["Zone/Regions"] == "VIC").sum()
                    auk_values = (df["Zone/Regions"] == "AUK").sum()
                    if vic_values > 0:
                        issues_found_in_file.append(f"'Zone/Regions' has {vic_values} 'VIC' value(s)")
                    if auk_values > 0:
                        issues_found_in_file.append(f"'Zone/Regions' has {auk_values} 'AUK' value(s)")
                else:
                    issues_found_in_file.append("'Zone/Regions' column not found")

                if issues_found_in_file:
                    files_needing_attention.append(f"{filename}: {'; '.join(issues_found_in_file)}")
                # else: # Optional: print if a file is okay
                #     tqdm.write(f"  {filename}: OK - All checks passed.")


        except Exception as e:
            tqdm.write(f"\n  Error processing file {filename}: {e}")
            import traceback
            traceback.print_exc()
            if mode == "check":
                 files_needing_attention.append(f"{filename} (Error during processing: {e})")


    # --- Summary for CHECK mode ---
    if mode == "check":
        if files_needing_attention:
            print("\n--- Files Requiring Attention ---")
            for item in files_needing_attention:
                print(f"- {item}")
        else:
            print("\n--- All files appear to be updated according to the checks. ---")

if __name__ == "__main__":
    # IMPORTANT: Use a raw string (r"...") for Windows paths
    target_directory = r"C:\Data Modelling\Ashish PowerBI TR\anztabrcwcombined"

    while True:
        print("\nChoose an operation:")
        print("1. Modify files (fill TR with 0, update Zone/Regions)")
        print("2. Check files (report if updates are needed)")
        print("Q. Quit")
        choice = input("Enter your choice (1, 2, or Q): ").strip().lower()

        if choice == '1':
            print("\n--- Starting File Modification ---")
            confirm = input(f"WARNING: This will modify files in '{target_directory}'. Are you sure? (yes/no): ").strip().lower()
            if confirm == 'yes':
                process_excel_files(target_directory, mode="modify")
                print("\n--- Modification process complete. ---")
            else:
                print("Modification cancelled by user.")
            break
        elif choice == '2':
            print("\n--- Starting File Check ---")
            process_excel_files(target_directory, mode="check")
            print("\n--- Check process complete. ---")
            break
        elif choice == 'q':
            print("Exiting script.")
            break
        else:
            print("Invalid choice. Please enter 1, 2, or Q.")