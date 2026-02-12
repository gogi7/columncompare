# Philips ANZ Equipment Tracking Database

A SQLite-based data analysis tool for tracking medical equipment across Australia and New Zealand, with TR (Time-to-Repair) analysis and workorder management.

## Overview

This project manages equipment data for Philips ANZ, combining multiple data sources into a unified SQLite database for analysis and reporting. Key features include:

- **Equipment Tracking**: Monitor equipment across 5 canonical regions (NSW, NZ, QLD, VSAT, WA)
- **TR Analysis**: Track Time-to-Repair metrics and trends
- **Workorder Management**: Link workorders to equipment with state normalization
- **Data Validation**: Scripts for cleaning and normalizing imported data

## Database Structure

The main database (`merged_data_validated.db`) contains the following key tables:

| Table | Records | Description |
|-------|---------|-------------|
| `combined_data` | 767,147 | Core equipment data with Zone/Regions assignments |
| `workorders` | 135,372 | Service workorders linked to equipment |
| `State_Location_Mapping` | 38 | Maps granular State codes → canonical Zone/Regions |
| `DimDate` | - | Date dimension table for time-based analysis |
| `fse` | - | Field Service Engineer assignments |
| `estherIB` | - | Installed base data from Esther system |
| `DimEquipment` | - | Equipment dimension table |
| `DimMaterial` | - | Material/parts dimension table |

### The 5 Canonical Regions

| Zone/Region | Coverage |
|-------------|----------|
| **NSW** | New South Wales + ACT |
| **NZ** | All New Zealand (20+ regional codes) |
| **QLD** | Queensland + Northern Territory |
| **VSAT** | Victoria + South Australia + Tasmania |
| **WA** | Western Australia |

## Quick Start

### Prerequisites
- Python 3.8+
- SQLite3
- Required packages: `pandas`, `tqdm`, `openpyxl`

```bash
pip install pandas tqdm openpyxl
```

### Querying the Database

```python
import sqlite3
import pandas as pd

conn = sqlite3.connect('merged_data_validated.db')

# Get equipment by region
df = pd.read_sql_query('''
    SELECT "Zone/Regions", COUNT(*) as equipment_count 
    FROM combined_data 
    GROUP BY "Zone/Regions"
''', conn)
print(df)
```

### Running Data Normalization

After importing new data, run the cleanup scripts:

```bash
# For Excel source files (pre-import)
python project/adjustments/tr0anddistrictsexcel.py

# For SQLite database (post-import)
python project/adjustments/tr0anddistrictDB.py
```

## Documentation

- [State Mapping Pipeline](docs/STATE_MAPPING_PIPELINE.md) — How workorder states are normalized to regions
- [Pipeline Overview](docs/PIPELINE_OVERVIEW.md) — Full data flow from source to database

## Project Structure

```
columncompare/
├── merged_data_validated.db    # Main SQLite database
├── project/
│   ├── README.md               # This file
│   ├── adjustments/            # Data normalization scripts
│   │   ├── tr0anddistrictDB.py       # Post-import SQLite cleanup
│   │   ├── tr0anddistrictsexcel.py   # Pre-import Excel cleanup
│   │   └── weeksnormalisaion.py      # Week number normalization
│   ├── docs/                   # Documentation
│   ├── comparator/             # Core comparison logic
│   ├── tables/                 # Table definitions
│   └── tests/                  # Test suite
└── *.py                        # Analysis scripts
```

## Key Scripts

| Script | Purpose |
|--------|---------|
| `tr0anddistrictDB.py` | Fill empty TR values with 0, normalize Zone/Regions in SQLite |
| `tr0anddistrictsexcel.py` | Same normalization applied to Excel source files |
| `dbdatesfix.py` | Date format corrections |
| `weeksnormalisaion.py` | Standardize week numbering across data sources |

## Maintenance

### Quarterly Tasks
1. Run unmapped states query to catch new regional codes
2. Update `State_Location_Mapping` table as needed
3. Re-run normalization scripts after bulk imports

See [State Mapping Pipeline](docs/STATE_MAPPING_PIPELINE.md) for detailed maintenance procedures.
