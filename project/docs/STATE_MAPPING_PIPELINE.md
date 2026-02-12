# State Mapping Pipeline

## Overview

The state mapping pipeline normalizes granular State values from workorders to 5 canonical Zone/Regions used across the database. This enables consistent JOINs between workorders and combined_data tables.

## The Problem

- `workorders.State` has **38 different values** (NSW, VIC, AUK, OTA, MWT, etc.)
- `combined_data.Zone/Regions` uses **5 canonical values**: NSW, NZ, QLD, VSAT, WA
- Need to map between them for JOINs and reporting

### Example: Why This Matters

A workorder might have `State = 'AUK'` (Auckland), but the equipment in `combined_data` has `Zone/Regions = 'NZ'`. Without the mapping, the JOIN fails.

## Solution: State_Location_Mapping Table

The `State_Location_Mapping` table provides the translation layer.

### Table Structure

| Column | Description | Example |
|--------|-------------|---------|
| `State` | Source value from workorders | AUK |
| `State_FSE` | Normalized state for FSE assignment | NZ |
| `Zone/Regions` | Canonical 5-region value | NZ |

### Full Mapping Reference

#### NSW Region
| State Code | State_FSE | Maps To |
|------------|-----------|---------|
| NSW | NSW | NSW |
| New | NSW | NSW |
| ACT | ACT | NSW |
| Aus | ACT | NSW |
| 09 | Unknown | NSW |

#### NZ Region (New Zealand)
| State Code | State_FSE | Maps To |
|------------|-----------|---------|
| NZ | NZ | NZ |
| AUK | NZ | NZ |
| AKL | NZ | NZ |
| OTA | NZ | NZ |
| Ota | NZ | NZ |
| MWT | NZ | NZ |
| CAN | NZ | NZ |
| STL | NZ | NZ |
| NTL | NZ | NZ |
| WKO | NZ | NZ |
| WTC | NZ | NZ |
| WGN | NZ | NZ |
| WLG | NZ | NZ |
| SI | NZ | NZ |
| NI | NZ | NZ |
| NSN | NZ | NZ |
| GIS | NZ | NZ |
| BOP | NZ | NZ |
| MBH | NZ | NZ |
| TKI | NZ | NZ |
| KGB | NZ | NZ |
| WAI | NZ | NZ |
| HKB | NZ | NZ |

#### QLD Region
| State Code | State_FSE | Maps To |
|------------|-----------|---------|
| QLD | QLD | QLD |
| Que | QLD | QLD |
| NT | NT | QLD |

#### VSAT Region (Victoria + SA + Tasmania)
| State Code | State_FSE | Maps To |
|------------|-----------|---------|
| VIC | VIC | VSAT |
| Vic | VIC | VSAT |
| vic | VIC | VSAT |
| SA | SA | VSAT |
| TAS | TAS | VSAT |

#### WA Region
| State Code | State_FSE | Maps To |
|------------|-----------|---------|
| WA | WA | WA |
| Wes | WA | WA |

## Pipeline Scripts

### 1. tr0anddistrictDB.py

**Location:** `project/adjustments/tr0anddistrictDB.py`

**Purpose:** Post-import SQLite cleanup

**Actions:**
- Fills empty/NULL TR values with 0
- Replaces `VIC` → `VSAT` in Zone/Regions
- Replaces `AUK` → `NZ` in Zone/Regions

**Usage:**
```bash
python project/adjustments/tr0anddistrictDB.py
```

Then choose option 1 (Modify) or 2 (Check).

### 2. tr0anddistrictsexcel.py

**Location:** `project/adjustments/tr0anddistrictsexcel.py`

**Purpose:** Pre-import Excel cleanup

**Actions:** Same as above, applied to source Excel files before import.

**Target Directory:** `C:\Data Modelling\Ashish PowerBI TR\anztabrcwcombined`

## How to Use the Mapping

### JOIN workorders to combined_data

```sql
SELECT 
    w.WorkorderNumber,
    w.State,
    slm."Zone/Regions" as MappedRegion,
    cd.EquipmentNumber,
    cd.TR
FROM workorders w
INNER JOIN State_Location_Mapping slm 
    ON w.State = slm.State
INNER JOIN combined_data cd 
    ON slm."Zone/Regions" = cd."Zone/Regions"
    AND w.EquipmentNumber = cd.EquipmentNumber;
```

### Get workorder counts by canonical region

```sql
SELECT 
    slm."Zone/Regions",
    COUNT(*) as workorder_count
FROM workorders w
INNER JOIN State_Location_Mapping slm ON w.State = slm.State
GROUP BY slm."Zone/Regions"
ORDER BY workorder_count DESC;
```

### Check for unmapped states

```sql
SELECT DISTINCT State, COUNT(*) as count
FROM workorders 
WHERE State NOT IN (SELECT State FROM State_Location_Mapping)
  AND State IS NOT NULL 
  AND State != ''
GROUP BY State
ORDER BY count DESC;
```

### Find workorders with missing State values

```sql
SELECT COUNT(*) as missing_state_count
FROM workorders 
WHERE State IS NULL OR State = '';
```

## Success Rate

| Metric | Count | Percentage |
|--------|-------|------------|
| Total workorders | 135,372 | 100% |
| Mapped (valid State) | 134,217 | 99.15% |
| Unmapped (empty State) | 1,155 | 0.85% |

> **Note:** All non-empty State values are currently mapped. The 1,155 unmapped records have empty/NULL State fields.

## Maintenance

### Quarterly Checklist

1. **Check for new unmapped states:**
   ```sql
   SELECT DISTINCT State, COUNT(*) as count
   FROM workorders 
   WHERE State NOT IN (SELECT State FROM State_Location_Mapping)
     AND State IS NOT NULL AND State != ''
   GROUP BY State;
   ```

2. **Add new mappings** if any appear:
   ```sql
   INSERT INTO State_Location_Mapping (State, State_FSE, "Zone/Regions")
   VALUES ('NEW_CODE', 'CANONICAL_STATE', 'REGION');
   ```

3. **Handle case variants** - The mapping includes common variants (VIC, Vic, vic) but new ones may appear.

### Adding a New Mapping

Example: Adding a new NZ region code 'TAR' (Taranaki):

```sql
INSERT INTO State_Location_Mapping (State, State_FSE, "Zone/Regions")
VALUES ('TAR', 'NZ', 'NZ');
```

### Verifying Mapping Coverage

```sql
-- Total coverage percentage
SELECT 
    ROUND(
        (SELECT COUNT(*) FROM workorders WHERE State IN (SELECT State FROM State_Location_Mapping))
        * 100.0 / 
        (SELECT COUNT(*) FROM workorders WHERE State IS NOT NULL AND State != ''),
        2
    ) as coverage_percent;
```

## Troubleshooting

### "No records found when JOINing"

1. Check if the State value exists in mapping:
   ```sql
   SELECT * FROM State_Location_Mapping WHERE State = 'YOUR_STATE';
   ```

2. Check for case sensitivity issues:
   ```sql
   SELECT DISTINCT State FROM workorders 
   WHERE LOWER(State) = LOWER('your_state');
   ```

### "Wrong region assigned"

Review the mapping and update if incorrect:
```sql
UPDATE State_Location_Mapping 
SET "Zone/Regions" = 'CORRECT_REGION'
WHERE State = 'STATE_CODE';
```
