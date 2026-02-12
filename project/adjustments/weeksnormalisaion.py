import pandas as pd
import sqlite3
import os
import shutil
from datetime import datetime, timedelta

# --- Configuration ---
OUTPUT_DIRECTORY = r"C:\Tools PHPC\columncompare"
DB_FILE = os.path.join(OUTPUT_DIRECTORY, "merged_data_validated.db")
DB_TABLE_NAME = "combined_data"
DIM_DATE_TABLE_NAME = "DimDate"
SOURCE_FILE_COL = "Source_Filename"
FK_DATE_KEY_COL = "DateKey_fk"
DIM_DATE_ACTUAL_DATE_COL = "FullDate" # Assumed to be 'YYYY-MM-DD' for range queries
# !!! LIKELY CHANGE THIS LINE based on your DimDate schema !!!
DIM_DATE_DAY_OF_WEEK_COL = "DayOfWeek" # Or your actual numerical day of week column

# ... (rest of the script remains the same) ...

# --- Backup ---
def backup_db(db_path):
    backup_path = db_path + f".backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
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
cursor = None

def get_datekeys_and_dayofweek_for_range(start_date_iso, end_date_iso):
    """Fetches DateKey and DayOfWeekISO for a given date range."""
    query = f"""
    SELECT DateKey, "{DIM_DATE_ACTUAL_DATE_COL}", "{DIM_DATE_DAY_OF_WEEK_COL}"
    FROM "{DIM_DATE_TABLE_NAME}"
    WHERE "{DIM_DATE_ACTUAL_DATE_COL}" >= ? AND "{DIM_DATE_ACTUAL_DATE_COL}" <= ?
    ORDER BY "{DIM_DATE_ACTUAL_DATE_COL}"; 
    """
    # Ensure DIM_DATE_DAY_OF_WEEK_COL provides a consistent numerical day of week
    df = pd.read_sql_query(query, conn, params=(start_date_iso, end_date_iso))
    if len(df) != 7: # Assuming weekly operations
        print(f"WARNING: Expected 7 days for range {start_date_iso}-{end_date_iso}, but found {len(df)}. Mapping might be incorrect if lengths differ.")
    return df

try:
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    print(f"\nSuccessfully connected to {DB_FILE} for modifications.")

    # --- Action 1: Remove one instance of '2024 Week 35 03 09 2024.xlsx' ---
    # This targets the entire file, not just records within a specific date range,
    # as the file itself is considered a duplicate contribution.
    print("\n--- Action 1: Removing data from duplicate source file ---")
    file_to_delete_action1 = '2024 Week 35 03 09 2024.xlsx'
    
    cursor.execute(f"""SELECT COUNT(*) FROM "{DB_TABLE_NAME}" WHERE "{SOURCE_FILE_COL}" = ?""", (file_to_delete_action1,))
    count_before_delete_a1 = cursor.fetchone()[0]
    print(f"  Found {count_before_delete_a1} records from '{file_to_delete_action1}' to be deleted.")

    if count_before_delete_a1 > 0:
        cursor.execute(f"""DELETE FROM "{DB_TABLE_NAME}" WHERE "{SOURCE_FILE_COL}" = ?""", (file_to_delete_action1,))
        conn.commit()
        print(f"  DELETED {cursor.rowcount} records from '{file_to_delete_action1}'.")
    else:
        print(f"  No records found from '{file_to_delete_action1}', no deletion performed.")

    # --- Helper function for replacing week data ---
    def replace_week_data(target_label, target_start_iso, target_end_iso, source_start_iso, source_end_iso):
        print(f"\n--- {target_label}: Replacing data for {target_start_iso} to {target_end_iso} ---")
        print(f"    Source data from: {source_start_iso} to {source_end_iso}")

        target_week_dimdata = get_datekeys_and_dayofweek_for_range(target_start_iso, target_end_iso)
        source_week_dimdata = get_datekeys_and_dayofweek_for_range(source_start_iso, source_end_iso)

        if target_week_dimdata.empty or source_week_dimdata.empty:
            print(f"    ERROR: Could not retrieve DimDate info for target or source week. Skipping {target_label}.")
            return
        
        if len(target_week_dimdata) != len(source_week_dimdata):
            print(f"    ERROR: Target week ({len(target_week_dimdata)} days) and source week ({len(source_week_dimdata)} days) have different lengths. Cannot map. Skipping {target_label}.")
            return

        target_datekeys = tuple(target_week_dimdata['DateKey'].tolist())
        source_datekeys = tuple(source_week_dimdata['DateKey'].tolist())

        # Create DateKey mapping based on DayOfWeekISO
        # Sort both by DayOfWeekISO to ensure correct alignment before creating map
        target_week_dimdata = target_week_dimdata.sort_values(by=DIM_DATE_DAY_OF_WEEK_COL)
        source_week_dimdata = source_week_dimdata.sort_values(by=DIM_DATE_DAY_OF_WEEK_COL)
        
        datekey_map = pd.Series(target_week_dimdata['DateKey'].values, index=source_week_dimdata['DateKey'].values).to_dict()
        
        if not datekey_map:
             print(f"    ERROR: Could not create DateKey map. Skipping {target_label}.")
             return
        print(f"    DateKey map created with {len(datekey_map)} entries.")
        # print(f"    Sample map: {list(datekey_map.items())[:3]}")


        # 1. Delete existing "bad" data for the target week
        print(f"    Deleting existing data for target range ({target_start_iso} to {target_end_iso})...")
        placeholders_target = ', '.join(['?'] * len(target_datekeys))
        cursor.execute(f"""SELECT COUNT(*) FROM "{DB_TABLE_NAME}" WHERE "{FK_DATE_KEY_COL}" IN ({placeholders_target})""", target_datekeys)
        count_to_delete = cursor.fetchone()[0]
        
        if count_to_delete > 0:
            cursor.execute(f"""DELETE FROM "{DB_TABLE_NAME}" WHERE "{FK_DATE_KEY_COL}" IN ({placeholders_target})""", target_datekeys)
            print(f"    DELETED {cursor.rowcount} records from target range.")
        else:
            print(f"    No records found in target range to delete.")

        # 2. Fetch "good" data from the source week
        print(f"    Fetching data from source range ({source_start_iso} to {source_end_iso})...")
        placeholders_source = ', '.join(['?'] * len(source_datekeys))
        # Get all columns except potentially an auto-incrementing PK if one exists and isn't DateKey_fk
        # For simplicity, selecting all columns assuming DateKey_fk is the one to change.
        # It's important that combined_data does not have an auto-incrementing PK that would clash on insert.
        # If it does, you must explicitly list columns for SELECT and INSERT, omitting the PK.
        
        # Dynamically get column names for combined_data table
        cursor.execute(f"PRAGMA table_info({DB_TABLE_NAME})")
        combined_data_cols_info = cursor.fetchall()
        combined_data_cols = [info[1] for info in combined_data_cols_info]
        cols_to_select_str = ", ".join([f'"{col}"' for col in combined_data_cols])

        source_data_df = pd.read_sql_query(f"""
            SELECT {cols_to_select_str} FROM "{DB_TABLE_NAME}" 
            WHERE "{FK_DATE_KEY_COL}" IN ({placeholders_source})
        """, conn, params=source_datekeys)
        
        if source_data_df.empty:
            print(f"    No data found in source range '{source_start_iso} to {source_end_iso}'. Skipping insert for {target_label}.")
            conn.commit() # Commit the deletion if that happened
            return
        print(f"    Fetched {len(source_data_df)} records from source range.")

        # 3. Map DateKey_fk and potentially update Source_Filename
        source_data_df[FK_DATE_KEY_COL] = source_data_df[FK_DATE_KEY_COL].map(datekey_map)
        
        # Update Source_Filename to reflect it's copied data (optional, but good for audit)
        if SOURCE_FILE_COL in source_data_df.columns:
            source_data_df[SOURCE_FILE_COL] = f"Copied_from_week_{source_start_iso}_to_{source_end_iso}_for_{target_label}"
        
        # Drop rows where mapping failed (DateKey_fk became NaN if a source DateKey wasn't in map)
        source_data_df.dropna(subset=[FK_DATE_KEY_COL], inplace=True)
        # Ensure FK_DATE_KEY_COL is integer if it was number before map
        source_data_df[FK_DATE_KEY_COL] = source_data_df[FK_DATE_KEY_COL].astype(int)


        if source_data_df.empty:
            print(f"    No data remaining after DateKey mapping. Skipping insert for {target_label}.")
            conn.commit()
            return
            
        # 4. Insert mapped data
        print(f"    Inserting {len(source_data_df)} mapped records into target range...")
        # Use df.to_sql for inserting. Need to ensure combined_data_cols matches source_data_df.columns
        # For to_sql, it's usually easier if the DataFrame columns match the table exactly.
        # Our dynamic cols_to_select_str should ensure this.
        
        # Convert DataFrame to list of tuples for executemany
        # Ensure order of columns in DataFrame matches table schema or explicit insert statement
        # For simplicity, relying on to_sql or ensuring combined_data_cols are in correct order
        
        # Check if all columns are present
        df_cols_set = set(source_data_df.columns)
        table_cols_set = set(combined_data_cols)
        if df_cols_set != table_cols_set:
            print(f"    WARNING: DataFrame columns {df_cols_set} do not perfectly match table columns {table_cols_set}.")
            print(f"    Missing in DF: {table_cols_set - df_cols_set}")
            print(f"    Extra in DF: {df_cols_set - table_cols_set}")
            # Attempting insert with DataFrame columns. This might fail if order is wrong or PK is an issue.
        
        try:
            source_data_df.to_sql(DB_TABLE_NAME, conn, if_exists='append', index=False)
            conn.commit()
            print(f"    SUCCESS: Inserted {len(source_data_df)} records for {target_label}.")
        except Exception as e_insert:
            print(f"    ERROR during to_sql insert: {e_insert}")
            print(f"    Data for {target_label} might be partially processed or rolled back.")
            conn.rollback()


    # --- Action 2: Replace data for Oct 07 - Oct 13, 2024 ---
    # Target: 2024-10-07 to 2024-10-13
    # Source: 2024-09-30 to 2024-10-06 (previous week)
    replace_week_data(
        target_label="Action 2 (Oct 07-13)",
        target_start_iso="2024-10-07", target_end_iso="2024-10-13",
        source_start_iso="2024-09-30", source_end_iso="2024-10-06"
    )

    # --- Action 3: Replace data for Aug 12 - Aug 18, 2024 ---
    # Target: 2024-08-12 to 2024-08-18
    # Source: 2024-08-05 to 2024-08-11 (previous week)
    replace_week_data(
        target_label="Action 3 (Aug 12-18)",
        target_start_iso="2024-08-12", target_end_iso="2024-08-18",
        source_start_iso="2024-08-05", source_end_iso="2024-08-11"
    )

    # --- Action 4: Replace data for Aug 19 - Aug 25, 2024 ---
    # Target: 2024-08-19 to 2024-08-25
    # Source: 2024-08-26 to 2024-09-01 (next week's original data before any modifications)
    # IMPORTANT: This assumes the data for 2024-08-26 to 2024-09-01 is "good" *before* Action 1 potentially modifies it.
    # If Action 1 deletes one of the source files for that range, the source data for Action 4 will be less.
    # It's generally safer to copy from periods not being actively modified in the same script run, or do it in stages.
    # For this script, we'll proceed assuming the remaining data for 2024-08-26 to 2024-09-01 is sufficient.
    replace_week_data(
        target_label="Action 4 (Aug 19-25)",
        target_start_iso="2024-08-19", target_end_iso="2024-08-25",
        source_start_iso="2024-08-26", source_end_iso="2024-09-01"
    )

    print("\n--- All specified database modifications attempted. ---")

except sqlite3.Error as e_sql:
    print(f"An SQLite error occurred: {e_sql}")
    if conn:
        conn.rollback()
        print("  Rolled back any uncommitted changes due to SQLite error.")
except Exception as e_main:
    print(f"An unexpected error occurred: {e_main}")
    import traceback
    traceback.print_exc()
    if conn:
        conn.rollback()
        print("  Rolled back any uncommitted changes due to unexpected error.")
finally:
    if conn:
        conn.close()
        print("\nDatabase connection closed.")

print("\n--- Database modification script finished. ---")
print("RECOMMENDATION: Re-run your analysis script to verify the changes.")
print(f"REMEMBER: A backup was made at the start. If issues arise, restore from the backup ending in .backup_YYYYMMDD_HHMMSS")