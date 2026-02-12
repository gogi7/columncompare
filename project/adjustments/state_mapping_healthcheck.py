"""
State Mapping Health Check

Validates the State_Location_Mapping table against workorders:
1. Calculates mapping success rate
2. Detects new/unmapped State values
3. Shows breakdown by Zone/Regions
4. Identifies data quality issues

Location: C:/Tools PHPC/columncompare/project/adjustments/state_mapping_healthcheck.py
Database: C:/Tools PHPC/columncompare/merged_data_validated.db

Usage:
    python state_mapping_healthcheck.py [--fix]
    
    --fix    Interactively add missing mappings to the database
"""

import sqlite3
import os
import sys
from datetime import datetime

# --- Configuration ---
# Auto-detect Windows vs WSL path
import platform
if platform.system() == 'Linux' and os.path.exists('/mnt/c'):
    # Running in WSL
    DB_FILE = '/mnt/c/Tools PHPC/columncompare/merged_data_validated.db'
else:
    # Running in Windows
    DB_FILE = r'C:\Tools PHPC\columncompare\merged_data_validated.db'

WORKORDERS_TABLE = 'workorders'
MAPPING_TABLE = 'State_Location_Mapping'
# --- End Configuration ---


def get_db_connection(db_path):
    """Establishes a connection to the SQLite database."""
    if not os.path.exists(db_path):
        print(f"Error: Database file not found at {db_path}")
        return None
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        return conn
    except sqlite3.Error as e:
        print(f"Error connecting to database: {e}")
        return None


def run_health_check(conn, fix_mode=False):
    """Run comprehensive state mapping health check."""
    cursor = conn.cursor()
    
    print("=" * 70)
    print("STATE MAPPING HEALTH CHECK")
    print(f"Database: {DB_FILE}")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    
    # --- 1. Basic Counts ---
    print("\n📊 BASIC STATISTICS")
    print("-" * 40)
    
    cursor.execute(f"SELECT COUNT(*) FROM {WORKORDERS_TABLE}")
    total_workorders = cursor.fetchone()[0]
    
    cursor.execute(f"SELECT COUNT(*) FROM {MAPPING_TABLE}")
    mapping_entries = cursor.fetchone()[0]
    
    cursor.execute(f"SELECT COUNT(DISTINCT State) FROM {WORKORDERS_TABLE} WHERE State IS NOT NULL AND State != ''")
    unique_states = cursor.fetchone()[0]
    
    print(f"  Total workorders:        {total_workorders:,}")
    print(f"  Mapping table entries:   {mapping_entries}")
    print(f"  Unique States in WOs:    {unique_states}")
    
    # --- 2. Mapping Success Rate ---
    print("\n✅ MAPPING SUCCESS RATE")
    print("-" * 40)
    
    cursor.execute(f"""
        SELECT COUNT(*) FROM {WORKORDERS_TABLE} w
        WHERE w.State IN (SELECT State FROM {MAPPING_TABLE})
    """)
    mapped_count = cursor.fetchone()[0]
    
    cursor.execute(f"""
        SELECT COUNT(*) FROM {WORKORDERS_TABLE}
        WHERE State IS NULL OR State = ''
    """)
    empty_state_count = cursor.fetchone()[0]
    
    unmapped_count = total_workorders - mapped_count - empty_state_count
    
    if total_workorders > 0:
        success_rate = (mapped_count / total_workorders) * 100
        empty_rate = (empty_state_count / total_workorders) * 100
        unmapped_rate = (unmapped_count / total_workorders) * 100
    else:
        success_rate = empty_rate = unmapped_rate = 0
    
    print(f"  Mapped successfully:     {mapped_count:,} ({success_rate:.2f}%)")
    print(f"  Empty/NULL State:        {empty_state_count:,} ({empty_rate:.2f}%)")
    print(f"  Unmapped (has State):    {unmapped_count:,} ({unmapped_rate:.2f}%)")
    
    # Success indicator
    if success_rate >= 99:
        print(f"\n  🟢 HEALTHY - {success_rate:.2f}% mapping rate")
    elif success_rate >= 95:
        print(f"\n  🟡 WARNING - {success_rate:.2f}% mapping rate (< 99%)")
    else:
        print(f"\n  🔴 CRITICAL - {success_rate:.2f}% mapping rate (< 95%)")
    
    # --- 3. Breakdown by Zone/Regions ---
    print("\n📍 BREAKDOWN BY ZONE/REGIONS")
    print("-" * 40)
    
    cursor.execute(f"""
        SELECT slm."Zone/Regions" as Zone, COUNT(*) as Count
        FROM {WORKORDERS_TABLE} w
        INNER JOIN {MAPPING_TABLE} slm ON w.State = slm.State
        GROUP BY slm."Zone/Regions"
        ORDER BY Count DESC
    """)
    
    print(f"  {'Zone':<12} {'Count':>12} {'Percentage':>12}")
    print(f"  {'-'*12} {'-'*12} {'-'*12}")
    
    for row in cursor.fetchall():
        pct = (row['Count'] / total_workorders) * 100
        print(f"  {row['Zone']:<12} {row['Count']:>12,} {pct:>11.2f}%")
    
    print(f"  {'-'*12} {'-'*12} {'-'*12}")
    print(f"  {'UNMAPPED':<12} {unmapped_count + empty_state_count:>12,} {(unmapped_rate + empty_rate):>11.2f}%")
    
    # --- 4. Unmapped States Detection ---
    print("\n⚠️  UNMAPPED STATES DETECTED")
    print("-" * 40)
    
    cursor.execute(f"""
        SELECT w.State, COUNT(*) as Count
        FROM {WORKORDERS_TABLE} w
        WHERE w.State NOT IN (SELECT State FROM {MAPPING_TABLE})
          AND w.State IS NOT NULL AND w.State != ''
        GROUP BY w.State
        ORDER BY Count DESC
    """)
    
    unmapped_states = cursor.fetchall()
    
    if not unmapped_states:
        print("  ✅ No unmapped states found! All State values are mapped.")
    else:
        print(f"  Found {len(unmapped_states)} unmapped State value(s):\n")
        print(f"  {'State':<15} {'Count':>10} {'Suggested Zone':>15}")
        print(f"  {'-'*15} {'-'*10} {'-'*15}")
        
        for row in unmapped_states:
            state = row['State']
            count = row['Count']
            # Suggest zone based on common patterns
            suggested = suggest_zone(state)
            print(f"  {state:<15} {count:>10,} {suggested:>15}")
        
        if fix_mode:
            print("\n" + "=" * 70)
            print("FIX MODE: Add missing mappings")
            print("=" * 70)
            add_missing_mappings(conn, unmapped_states)
    
    # --- 5. Case Sensitivity Check ---
    print("\n🔤 CASE SENSITIVITY CHECK")
    print("-" * 40)
    
    cursor.execute(f"""
        SELECT State, COUNT(*) as Count
        FROM {WORKORDERS_TABLE}
        WHERE State IS NOT NULL AND State != ''
        GROUP BY State
        HAVING LOWER(State) IN (
            SELECT LOWER(State) FROM {WORKORDERS_TABLE}
            WHERE State IS NOT NULL AND State != ''
            GROUP BY LOWER(State)
            HAVING COUNT(DISTINCT State) > 1
        )
        ORDER BY LOWER(State), State
    """)
    
    case_variants = cursor.fetchall()
    
    if not case_variants:
        print("  ✅ No case sensitivity issues detected.")
    else:
        print("  ⚠️  Found State values with case variants:")
        current_lower = None
        for row in case_variants:
            if current_lower != row['State'].lower():
                if current_lower is not None:
                    print()
                current_lower = row['State'].lower()
            print(f"    '{row['State']}' ({row['Count']:,} records)")
    
    # --- 6. Mapping Table Integrity ---
    print("\n🔍 MAPPING TABLE INTEGRITY")
    print("-" * 40)
    
    # Check for duplicate State entries
    cursor.execute(f"""
        SELECT State, COUNT(*) as Count
        FROM {MAPPING_TABLE}
        GROUP BY State
        HAVING COUNT(*) > 1
    """)
    duplicates = cursor.fetchall()
    
    if duplicates:
        print("  ⚠️  Duplicate State entries found:")
        for row in duplicates:
            print(f"    '{row['State']}' appears {row['Count']} times")
    else:
        print("  ✅ No duplicate State entries.")
    
    # Check for NULL or empty Zone/Regions
    cursor.execute(f"""
        SELECT State, "Zone/Regions"
        FROM {MAPPING_TABLE}
        WHERE "Zone/Regions" IS NULL OR "Zone/Regions" = ''
    """)
    empty_zones = cursor.fetchall()
    
    if empty_zones:
        print("  ⚠️  States with empty Zone/Regions:")
        for row in empty_zones:
            print(f"    '{row['State']}' has no Zone/Regions assigned")
    else:
        print("  ✅ All States have Zone/Regions assigned.")
    
    # --- Summary ---
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"  Mapping Success Rate:  {success_rate:.2f}%")
    print(f"  Unmapped States:       {len(unmapped_states)}")
    print(f"  Empty State Records:   {empty_state_count:,}")
    
    if len(unmapped_states) > 0:
        print(f"\n  💡 Run with --fix to interactively add missing mappings:")
        print(f"     python state_mapping_healthcheck.py --fix")
    
    print("\n" + "=" * 70)
    
    return {
        'total_workorders': total_workorders,
        'mapped_count': mapped_count,
        'unmapped_count': unmapped_count,
        'empty_state_count': empty_state_count,
        'success_rate': success_rate,
        'unmapped_states': [dict(row) for row in unmapped_states],
        'mapping_entries': mapping_entries
    }


def suggest_zone(state):
    """Suggest a Zone/Regions based on common patterns."""
    state_upper = state.upper() if state else ''
    
    # Australian states
    if state_upper in ['NSW', 'NEW', 'ACT', 'AUS']:
        return 'NSW'
    elif state_upper in ['VIC', 'SA', 'TAS']:
        return 'VSAT'
    elif state_upper in ['QLD', 'QUE', 'NT']:
        return 'QLD'
    elif state_upper in ['WA', 'WES']:
        return 'WA'
    # NZ - 3-letter codes typically
    elif len(state_upper) == 3:
        return 'NZ (likely)'
    else:
        return '??? (unknown)'


def add_missing_mappings(conn, unmapped_states):
    """Interactively add missing mappings."""
    cursor = conn.cursor()
    
    valid_zones = ['NSW', 'NZ', 'QLD', 'VSAT', 'WA']
    
    for row in unmapped_states:
        state = row['State']
        count = row['Count']
        suggested = suggest_zone(state)
        
        print(f"\n  State: '{state}' ({count:,} workorders)")
        print(f"  Suggested Zone: {suggested}")
        print(f"  Valid zones: {', '.join(valid_zones)}")
        
        zone = input(f"  Enter Zone/Regions (or 's' to skip, 'q' to quit): ").strip()
        
        if zone.lower() == 'q':
            print("  Quitting fix mode.")
            break
        elif zone.lower() == 's':
            print(f"  Skipping '{state}'")
            continue
        elif zone.upper() in valid_zones:
            zone = zone.upper()
            state_fse = state.upper() if len(state) <= 3 else 'Unknown'
            
            try:
                cursor.execute(f"""
                    INSERT INTO {MAPPING_TABLE} (State, State_FSE, "Zone/Regions")
                    VALUES (?, ?, ?)
                """, (state, state_fse, zone))
                conn.commit()
                print(f"  ✅ Added: '{state}' → '{zone}'")
            except sqlite3.Error as e:
                print(f"  ❌ Error adding mapping: {e}")
        else:
            print(f"  ⚠️  Invalid zone '{zone}'. Skipping.")


def main():
    fix_mode = '--fix' in sys.argv
    
    conn = get_db_connection(DB_FILE)
    if not conn:
        sys.exit(1)
    
    try:
        results = run_health_check(conn, fix_mode=fix_mode)
        
        # Exit code based on health
        if results['success_rate'] >= 99 and len(results['unmapped_states']) == 0:
            sys.exit(0)  # Healthy
        elif results['success_rate'] >= 95:
            sys.exit(1)  # Warning
        else:
            sys.exit(2)  # Critical
            
    finally:
        conn.close()


if __name__ == "__main__":
    main()
