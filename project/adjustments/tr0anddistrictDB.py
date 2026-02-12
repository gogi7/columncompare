import sqlite3
import os
from tqdm import tqdm
import pandas as pd # For easily checking column existence and reading for checks

# --- Configuration ---
db_file = r'C:\Tools PHPC\columncompare\merged_data_validated.db' # Use raw string for path
combined_data_table_name = 'combined_data'
# --- End Configuration ---

def get_db_connection(db_path):
    """Establishes a connection to the SQLite database."""
    if not os.path.exists(db_path):
        print(f"Error: Database file not found at {db_path}")
        return None
    try:
        conn = sqlite3.connect(db_path)
        # Optional: Set row_factory for dictionary-like access (not strictly needed here)
        # conn.row_factory = sqlite3.Row
        return conn
    except sqlite3.Error as e:
        print(f"Error connecting to database: {e}")
        return None

def get_table_columns(conn, table_name):
    """Gets a list of column names for a given table."""
    try:
        # PRAGMA table_info is a reliable way to get column names
        cursor = conn.cursor()
        cursor.execute(f"PRAGMA table_info([{table_name}]);") # Use [] for table names with spaces/special chars
        columns = [row[1] for row in cursor.fetchall()]
        return columns
    except sqlite3.Error as e:
        print(f"Error fetching column info for table {table_name}: {e}")
        return []

def modify_database(db_path, table_name):
    """
    Modifies the SQLite database:
    1. Fills empty/NULL values in "TR" column with 0.
    2. Replaces "VIC" with "VSAT" and "AUK" with "NZ" in "Zone/Regions".
    """
    conn = get_db_connection(db_path)
    if not conn:
        return

    cursor = conn.cursor()

    # Check if table exists by trying to get columns
    table_columns = get_table_columns(conn, table_name)
    if not table_columns:
        print(f"Table '{table_name}' not found or no columns retrieved. Aborting modification.")
        conn.close()
        return

    total_operations = 0
    if "TR" in table_columns: total_operations +=1
    if "Zone/Regions" in table_columns: total_operations +=2 # Two updates for Zone/Regions

    if total_operations == 0:
        print(f"Neither 'TR' nor 'Zone/Regions' columns found in table '{table_name}'. No modifications possible.")
        conn.close()
        return

    with tqdm(total=total_operations, desc="Modifying database", unit="op") as pbar:
        try:
            # 1. Process "TR" column
            if "TR" in table_columns:
                # Update rows where TR is NULL or an empty string (common for unpopulated cells)
                # Ensure TR is an integer column or handle type conversion if necessary.
                # Assuming TR is already numeric or text that can hold '0'.
                sql_update_tr = f"""
                    UPDATE [{table_name}]
                    SET TR = 0
                    WHERE TR IS NULL OR TR = '';
                """
                cursor.execute(sql_update_tr)
                tr_rows_affected = cursor.rowcount
                if tr_rows_affected > 0:
                    tqdm.write(f"  Updated {tr_rows_affected} rows in 'TR' column to 0.")
                else:
                    tqdm.write(f"  No empty/NULL values found to update in 'TR' column.")
                pbar.update(1)
            else:
                tqdm.write(f"  Warning: Column 'TR' not found in table '{table_name}'.")
                if "Zone/Regions" not in table_columns: pbar.update(1) # If TR is missing but Zone is also missing, update pbar


            # 2. Process "Zone/Regions" column
            # Quoting "Zone/Regions" because of the slash
            if "Zone/Regions" in table_columns:
                # Replace VIC with VSAT
                sql_update_vic = f"""
                    UPDATE [{table_name}]
                    SET "Zone/Regions" = 'VSAT'
                    WHERE "Zone/Regions" = 'VIC';
                """
                cursor.execute(sql_update_vic)
                vic_rows_affected = cursor.rowcount
                if vic_rows_affected > 0:
                    tqdm.write(f"  Replaced {vic_rows_affected} 'VIC' with 'VSAT' in 'Zone/Regions'.")
                else:
                    tqdm.write(f"  No 'VIC' values found to update in 'Zone/Regions'.")
                pbar.update(1)

                # Replace AUK with NZ
                sql_update_auk = f"""
                    UPDATE [{table_name}]
                    SET "Zone/Regions" = 'NZ'
                    WHERE "Zone/Regions" = 'AUK';
                """
                cursor.execute(sql_update_auk)
                auk_rows_affected = cursor.rowcount
                if auk_rows_affected > 0:
                    tqdm.write(f"  Replaced {auk_rows_affected} 'AUK' with 'NZ' in 'Zone/Regions'.")
                else:
                    tqdm.write(f"  No 'AUK' values found to update in 'Zone/Regions'.")
                pbar.update(1)
            else:
                tqdm.write(f"  Warning: Column 'Zone/Regions' not found in table '{table_name}'.")
                if "TR" not in table_columns: pbar.update(1) # If Zone is missing but TR is also missing

            conn.commit()
            tqdm.write("  Database modifications committed.")

        except sqlite3.Error as e:
            conn.rollback() # Rollback changes on error
            tqdm.write(f"\n  An error occurred during database modification: {e}")
            tqdm.write("  Changes have been rolled back.")
        finally:
            conn.close()

def check_database_status(db_path, table_name):
    """
    Checks the SQLite database for values that would be modified:
    1. Counts empty/NULL values in "TR" column.
    2. Counts "VIC" and "AUK" in "Zone/Regions".
    """
    conn = get_db_connection(db_path)
    if not conn:
        return

    cursor = conn.cursor()
    issues_found = False

    # Check if table exists
    table_columns = get_table_columns(conn, table_name)
    if not table_columns:
        print(f"Table '{table_name}' not found or no columns retrieved. Aborting check.")
        conn.close()
        return

    total_checks = 0
    if "TR" in table_columns: total_checks +=1
    if "Zone/Regions" in table_columns: total_checks +=2


    if total_checks == 0:
        print(f"Neither 'TR' nor 'Zone/Regions' columns found in table '{table_name}'. No checks possible.")
        conn.close()
        return

    print("\n--- Database Check Results ---")
    with tqdm(total=total_checks, desc="Checking database", unit="check") as pbar:
        try:
            # 1. Check "TR" column
            if "TR" in table_columns:
                sql_check_tr = f"""
                    SELECT COUNT(*) FROM [{table_name}]
                    WHERE TR IS NULL OR TR = '';
                """
                cursor.execute(sql_check_tr)
                empty_tr_count = cursor.fetchone()[0]
                if empty_tr_count > 0:
                    tqdm.write(f"  Issue: 'TR' column has {empty_tr_count} empty/NULL value(s) that would be set to 0.")
                    issues_found = True
                else:
                    tqdm.write(f"  OK: 'TR' column has no empty/NULL values.")
                pbar.update(1)
            else:
                tqdm.write(f"  Info: Column 'TR' not found in table '{table_name}'.")
                if "Zone/Regions" not in table_columns: pbar.update(1)


            # 2. Check "Zone/Regions" column
            if "Zone/Regions" in table_columns:
                # Check for VIC
                sql_check_vic = f"""
                    SELECT COUNT(*) FROM [{table_name}]
                    WHERE "Zone/Regions" = 'VIC';
                """
                cursor.execute(sql_check_vic)
                vic_count = cursor.fetchone()[0]
                if vic_count > 0:
                    tqdm.write(f"  Issue: 'Zone/Regions' has {vic_count} 'VIC' value(s) that would be changed to 'VSAT'.")
                    issues_found = True
                else:
                    tqdm.write(f"  OK: 'Zone/Regions' has no 'VIC' values.")
                pbar.update(1)

                # Check for AUK
                sql_check_auk = f"""
                    SELECT COUNT(*) FROM [{table_name}]
                    WHERE "Zone/Regions" = 'AUK';
                """
                cursor.execute(sql_check_auk)
                auk_count = cursor.fetchone()[0]
                if auk_count > 0:
                    tqdm.write(f"  Issue: 'Zone/Regions' has {auk_count} 'AUK' value(s) that would be changed to 'NZ'.")
                    issues_found = True
                else:
                    tqdm.write(f"  OK: 'Zone/Regions' has no 'AUK' values.")
                pbar.update(1)
            else:
                tqdm.write(f"  Info: Column 'Zone/Regions' not found in table '{table_name}'.")
                if "TR" not in table_columns: pbar.update(1)


            if not issues_found and total_checks > 0:
                tqdm.write("\n  All checks passed. Database appears to be up-to-date regarding these rules.")
            elif issues_found:
                tqdm.write("\n  One or more issues found. Database may need updates.")

        except sqlite3.Error as e:
            tqdm.write(f"\n  An error occurred during database check: {e}")
        finally:
            conn.close()

if __name__ == "__main__":
    if not os.path.exists(db_file):
        print(f"CRITICAL ERROR: Database file specified does not exist: {db_file}")
        print("Please check the 'db_file' configuration at the top of the script.")
    else:
        while True:
            print("\nChoose an operation for the SQLite database:")
            print(f"  DB: {db_file}")
            print(f"  Table: {combined_data_table_name}")
            print("1. Modify database (fill TR with 0, update Zone/Regions)")
            print("2. Check database (report if updates are needed)")
            print("Q. Quit")
            choice = input("Enter your choice (1, 2, or Q): ").strip().lower()

            if choice == '1':
                print("\n--- Starting Database Modification ---")
                confirm = input(f"WARNING: This will PERMANENTLY modify data in '{combined_data_table_name}' within '{db_file}'.\n"
                                "It is STRONGLY recommended to have a backup. Are you sure? (yes/no): ").strip().lower()
                if confirm == 'yes':
                    modify_database(db_file, combined_data_table_name)
                    print("\n--- Database modification process complete. ---")
                else:
                    print("Modification cancelled by user.")
                break
            elif choice == '2':
                print("\n--- Starting Database Check ---")
                check_database_status(db_file, combined_data_table_name)
                print("\n--- Database check process complete. ---")
                break
            elif choice == 'q':
                print("Exiting script.")
                break
            else:
                print("Invalid choice. Please enter 1, 2, or Q.")