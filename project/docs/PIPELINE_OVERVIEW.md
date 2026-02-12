# Pipeline Overview

This document describes the complete data flow from source files to the normalized SQLite database.

## Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           SOURCE DATA                                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  Excel Files (anztabrcwcombined/)                                           │
│  ├── Equipment data                                                          │
│  ├── Workorders                                                              │
│  └── FSE assignments                                                         │
│                                                                              │
└─────────────────────────────────┬───────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                    STAGE 1: PRE-IMPORT CLEANUP                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  tr0anddistrictsexcel.py                                                    │
│  ├── Fill empty TR values with 0                                            │
│  ├── Replace VIC → VSAT in Zone/Regions                                     │
│  └── Replace AUK → NZ in Zone/Regions                                       │
│                                                                              │
│  Output: Cleaned Excel files ready for import                               │
│                                                                              │
└─────────────────────────────────┬───────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                    STAGE 2: DATA IMPORT                                      │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  Import scripts / Manual import via DB Browser for SQLite                   │
│  ├── Load Excel → SQLite tables                                             │
│  ├── Create indexes                                                          │
│  └── Establish relationships                                                │
│                                                                              │
│  Target: merged_data_validated.db                                           │
│                                                                              │
└─────────────────────────────────┬───────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                    STAGE 3: POST-IMPORT NORMALIZATION                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  tr0anddistrictDB.py                                                        │
│  ├── Fill empty TR values with 0 in combined_data                           │
│  ├── Replace VIC → VSAT in Zone/Regions                                     │
│  └── Replace AUK → NZ in Zone/Regions                                       │
│                                                                              │
│  weeksnormalisaion.py                                                       │
│  └── Standardize week numbering format                                      │
│                                                                              │
│  dbdatesfix.py                                                              │
│  └── Correct date format inconsistencies                                    │
│                                                                              │
└─────────────────────────────────┬───────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                    STAGE 4: READY FOR ANALYSIS                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  merged_data_validated.db                                                   │
│  ├── combined_data (767,147 records)                                        │
│  ├── workorders (135,372 records)                                           │
│  ├── State_Location_Mapping (38 mappings)                                   │
│  ├── DimDate                                                                │
│  ├── DimEquipment                                                           │
│  ├── DimMaterial                                                            │
│  ├── fse                                                                    │
│  └── estherIB                                                               │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Stage Details

### Stage 1: Pre-Import Cleanup

**Script:** `project/adjustments/tr0anddistrictsexcel.py`

**Input:** Excel files from `C:\Data Modelling\Ashish PowerBI TR\anztabrcwcombined`

**Operations:**
1. Scan all `.xlsx` and `.xls` files in directory
2. For each file with a `TR` column: fill NULL/empty values with 0
3. For each file with a `Zone/Regions` column:
   - Replace "VIC" with "VSAT"
   - Replace "AUK" with "NZ"
4. Save modified files in place

**Why pre-import?**  
Catching issues in Excel is easier to audit and allows manual review before database import.

### Stage 2: Data Import

Data is imported into SQLite via:
- **DB Browser for SQLite** (manual import)
- **Custom Python scripts** using pandas `to_sql()`

**Tables created:**
| Table | Source |
|-------|--------|
| combined_data | Equipment master data |
| workorders | Service workorder records |
| fse | Field Service Engineer assignments |
| estherIB | Installed base from Esther system |
| DimDate | Generated date dimension |
| DimEquipment | Equipment dimension |
| DimMaterial | Material/parts dimension |
| State_Location_Mapping | Manual mapping table |

### Stage 3: Post-Import Normalization

**Script:** `project/adjustments/tr0anddistrictDB.py`

**Operations:**
1. Connect to `merged_data_validated.db`
2. Update `combined_data` table:
   - Set `TR = 0` where TR is NULL or empty
   - Replace `Zone/Regions = 'VIC'` with 'VSAT'
   - Replace `Zone/Regions = 'AUK'` with 'NZ'

**Why post-import too?**  
- Catches data imported from other sources
- Ensures consistency if pre-import step was skipped
- Handles incremental imports

**Additional Scripts:**

| Script | Purpose |
|--------|---------|
| `weeksnormalisaion.py` | Standardize week numbers (ISO vs custom) |
| `dbdatesfix.py` | Fix date format inconsistencies |

### Stage 4: Analysis-Ready Database

After all normalization:

- **Zone/Regions** contains only 5 canonical values
- **TR** column has no NULLs (defaults to 0)
- **State_Location_Mapping** enables workorder ↔ equipment JOINs

## Joining Workorders to Equipment

The key challenge is that `workorders.State` uses granular codes (VIC, AUK, OTA...) while `combined_data.Zone/Regions` uses canonical regions (VSAT, NZ...).

### The Solution

```sql
-- Use State_Location_Mapping as a bridge
SELECT w.*, cd.*
FROM workorders w
JOIN State_Location_Mapping slm ON w.State = slm.State
JOIN combined_data cd 
    ON slm."Zone/Regions" = cd."Zone/Regions"
    AND w.EquipmentNumber = cd.EquipmentNumber;
```

### Why This Works

```
workorders.State = 'AUK'
        ↓ (lookup in State_Location_Mapping)
slm."Zone/Regions" = 'NZ'
        ↓ (JOIN to combined_data)
combined_data."Zone/Regions" = 'NZ'
```

## Running the Pipeline

### Full Refresh (New Data Load)

```bash
# 1. Clean source Excel files
python project/adjustments/tr0anddistrictsexcel.py
# Select option 1 (Modify)

# 2. Import data to SQLite (manual or via script)

# 3. Normalize the database
python project/adjustments/tr0anddistrictDB.py
# Select option 1 (Modify)

# 4. Fix any date issues
python project/adjustments/dbdatesfix.py

# 5. Normalize week numbers
python project/adjustments/weeksnormalisaion.py
```

### Check-Only Mode (Audit)

```bash
# Check Excel files without modifying
python project/adjustments/tr0anddistrictsexcel.py
# Select option 2 (Check)

# Check database without modifying  
python project/adjustments/tr0anddistrictDB.py
# Select option 2 (Check)
```

## Validation Queries

### Verify Zone/Regions Normalization

```sql
-- Should return only: NSW, NZ, QLD, VSAT, WA
SELECT DISTINCT "Zone/Regions" 
FROM combined_data 
ORDER BY 1;
```

### Verify TR Has No NULLs

```sql
-- Should return 0
SELECT COUNT(*) 
FROM combined_data 
WHERE TR IS NULL;
```

### Verify Mapping Coverage

```sql
-- Should show 100% for non-empty states
SELECT 
    COUNT(CASE WHEN slm.State IS NOT NULL THEN 1 END) * 100.0 / 
    COUNT(CASE WHEN w.State != '' AND w.State IS NOT NULL THEN 1 END) as coverage_pct
FROM workorders w
LEFT JOIN State_Location_Mapping slm ON w.State = slm.State;
```
