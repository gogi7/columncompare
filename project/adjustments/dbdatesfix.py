import sqlite3
import os
import shutil # For backing up the database

# --- Configuration ---
OUTPUT_DIRECTORY = r"C:\Tools PHPC\columncompare"
DB_FILE = os.path.join(OUTPUT_DIRECTORY, "merged_data_validated.db")
DB_TABLE_NAME = "combined_data"
DIM_DATE_TABLE_NAME = "DimDate"
SOURCE_FILE_COL = "Source_Filename" # Confirmed column name
FK_DATE_KEY_COL = "DateKey_fk"      # FK in combined_data to DimDate.DateKey
DIM_DATE_ACTUAL_DATE_COL = "FullDate" # Date column in DimDate (used to find new DateKey)

# --- Backup ---
def backup_db(db_path):
    backup_path = db_path + ".backup"
    try:
        shutil.copy2(db_path, backup_path)
        print(f"SUCCESS: Database backed up to {backup_path}")
        return True
    except Exception as e:
        print(f"ERROR: Failed to backup database: {e}")
        return False

if not os.path.exists(DB_FILE):
    print(f"ERROR: SQLite Database file not found: {DB_FILE}")
    exit()

if not backup_db(DB_FILE):
    print("Aborting script due to backup failure.")
    exit()

conn = None
try:
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    print(f"\nSuccessfully connected to {DB_FILE} for modifications.")

    # --- Case 1: Delete records from '2022 Week 52 25 12 2022.xlsx' ---
    file_to_delete_case1 = '2022 Week 52 25 12 2022.xlsx'
    print(f"\n--- Case 1: Deleting records from source file: '{file_to_delete_case1}' ---")
    
    # First, check how many records will be deleted (optional, but good for safety)
    cursor.execute(f"""
        SELECT COUNT(*) FROM "{DB_TABLE_NAME}"
        WHERE "{SOURCE_FILE_COL}" = ?
    """, (file_to_delete_case1,))
    count_before_delete = cursor.fetchone()[0]
    print(f"  Found {count_before_delete} records from '{file_to_delete_case1}' to be deleted.")

    if count_before_delete > 0:
        cursor.execute(f"""
            DELETE FROM "{DB_TABLE_NAME}"
            WHERE "{SOURCE_FILE_COL}" = ?
        """, (file_to_delete_case1,))
        conn.commit()
        print(f"  DELETED {cursor.rowcount} records from '{file_to_delete_case1}'.")
    else:
        print(f"  No records found from '{file_to_delete_case1}', no deletion performed.")


    # --- Case 2: Update DateKey_fk for records from '2023 Week 52 29 12 2023.xlsx' ---
    file_to_update_case2 = '2023 Week 52 29 12 2023.xlsx'
    correct_date_case2_iso = '2023-12-29' # ISO format YYYY-MM-DD
    print(f"\n--- Case 2: Updating records from '{file_to_update_case2}' to reflect date '{correct_date_case2_iso}' ---")

    # Find the DateKey in DimDate for the correct date.
    # The format of FullDate in your DimDate table sample was "d/MM/yyyy" (e.g., "29/12/2023")
    # If your DimDate.FullDate is actually stored in ISO format 'YYYY-MM-DD', adjust the query.
    # Let's assume we need to find the DimDate.FullDate format for '2023-12-29'
    # A robust way is to query DimDate based on year, month, day if those columns exist and are reliable.
    # If DimDate.FullDate stores '29/12/2023', then:
    # correct_date_dimdate_format_case2 = '29/12/2023' 
    # If DimDate.FullDate stores '2023-12-29', then:
    correct_date_dimdate_format_case2 = correct_date_case2_iso

    cursor.execute(f"""
        SELECT DateKey FROM "{DIM_DATE_TABLE_NAME}"
        WHERE "{DIM_DATE_ACTUAL_DATE_COL}" = ? 
    """, (correct_date_dimdate_format_case2,)) # Or use Year, Month, Day columns if DimDate.FullDate format is tricky
    
    new_datekey_row = cursor.fetchone()
    if new_datekey_row:
        new_datekey_case2 = new_datekey_row[0]
        print(f"  Found new DateKey '{new_datekey_case2}' for date '{correct_date_dimdate_format_case2}'.")

        # Check how many records will be updated
        cursor.execute(f"""
            SELECT COUNT(*) FROM "{DB_TABLE_NAME}"
            WHERE "{SOURCE_FILE_COL}" = ?
        """, (file_to_update_case2,))
        count_before_update = cursor.fetchone()[0]
        print(f"  Found {count_before_update} records from '{file_to_update_case2}' to be updated.")

        if count_before_update > 0:
            # It's safer to update based on primary key or unique row ID if available.
            # If combined_data has a primary key (e.g., 'rowid' or a dedicated PK column),
            # it's better to SELECT those PKs first, then UPDATE using WHERE PK IN (...).
            # For simplicity, directly updating based on Source_Filename:
            cursor.execute(f"""
                UPDATE "{DB_TABLE_NAME}"
                SET "{FK_DATE_KEY_COL}" = ?
                WHERE "{SOURCE_FILE_COL}" = ?
            """, (new_datekey_case2, file_to_update_case2))
            conn.commit()
            print(f"  UPDATED {cursor.rowcount} records from '{file_to_update_case2}' with new DateKey_fk '{new_datekey_case2}'.")
        else:
            print(f"  No records found from '{file_to_update_case2}', no update performed.")
    else:
        print(f"  ERROR: Could not find a DateKey in DimDate for date '{correct_date_dimdate_format_case2}'. Update for Case 2 SKIPPED.")
        print(f"  Please ensure date '{correct_date_dimdate_format_case2}' exists in DimDate with the column '{DIM_DATE_ACTUAL_DATE_COL}' and the expected format.")

    # --- Case 3: Delete records from one of the duplicate files for 2024 Week 25 ---
    # YOU DECIDE WHICH ONE TO DELETE. I'm picking one based on your description.
    file_to_delete_case3 = '2024 Week 25 27 05 2024.xlsx' # Example, confirm this is the one to delete
    print(f"\n--- Case 3: Deleting records from source file: '{file_to_delete_case3}' (2024 Week 25 duplicate) ---")
    
    cursor.execute(f"""SELECT COUNT(*) FROM "{DB_TABLE_NAME}" WHERE "{SOURCE_FILE_COL}" = ?""", (file_to_delete_case3,))
    count_before_delete_c3 = cursor.fetchone()[0]
    print(f"  Found {count_before_delete_c3} records from '{file_to_delete_case3}' to be deleted.")

    if count_before_delete_c3 > 0:
        cursor.execute(f"""DELETE FROM "{DB_TABLE_NAME}" WHERE "{SOURCE_FILE_COL}" = ?""", (file_to_delete_case3,))
        conn.commit()
        print(f"  DELETED {cursor.rowcount} records from '{file_to_delete_case3}'.")
    else:
        print(f"  No records found from '{file_to_delete_case3}', no deletion performed.")

    # --- Case 4: Delete records from one of the duplicate files for 2024 Week 26 ---
    # YOU DECIDE WHICH ONE TO DELETE.
    file_to_delete_case4 = '2024 Week 26 01 06 2024.xlsx' # Example, confirm this is the one to delete
    print(f"\n--- Case 4: Deleting records from source file: '{file_to_delete_case4}' (2024 Week 26 duplicate) ---")

    cursor.execute(f"""SELECT COUNT(*) FROM "{DB_TABLE_NAME}" WHERE "{SOURCE_FILE_COL}" = ?""", (file_to_delete_case4,))
    count_before_delete_c4 = cursor.fetchone()[0]
    print(f"  Found {count_before_delete_c4} records from '{file_to_delete_case4}' to be deleted.")
    
    if count_before_delete_c4 > 0:
        cursor.execute(f"""DELETE FROM "{DB_TABLE_NAME}" WHERE "{SOURCE_FILE_COL}" = ?""", (file_to_delete_case4,))
        conn.commit()
        print(f"  DELETED {cursor.rowcount} records from '{file_to_delete_case4}'.")
    else:
        print(f"  No records found from '{file_to_delete_case4}', no deletion performed.")

    print("\n--- All specified database modifications attempted. ---")

except sqlite3.Error as e:
    print(f"An SQLite error occurred during database modification: {e}")
    if conn:
        conn.rollback() # Rollback changes if any error occurs
        print("  Rolled back any uncommitted changes.")
except Exception as e:
    print(f"An unexpected error occurred: {e}")
    if conn:
        conn.rollback()
        print("  Rolled back any uncommitted changes.")
finally:
    if conn:
        conn.close()
        print("  Database connection closed.")

print("\n--- Database modification script finished. ---")
print("RECOMMENDATION: Re-run your analysis script to verify the changes.")