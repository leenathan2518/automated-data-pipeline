# PROJECT_ARCHITECTURE

## System Overview

The Automated Data Pipeline follows a modular layered ETL architecture.

```text
External Sources
│
├── FRED
├── OpenBB
│   └── yfinance provider
└── Sina Finance
        │
        ▼
┌──────────────────────────┐
│      Extract Layer       │
└────────────┬─────────────┘
             ▼
┌──────────────────────────┐
│     Transform Layer      │
└────────────┬─────────────┘
             ▼
┌──────────────────────────┐
│    Data Quality Layer    │
└────────────┬─────────────┘
             ▼
┌──────────────────────────┐
│        Load Layer        │
└────────────┬─────────────┘
             ▼
┌──────────────────────────┐
│       PostgreSQL         │
└────────────┬─────────────┘
             ▼
┌──────────────────────────┐
│ Logging and Monitoring   │
└──────────────────────────┘
```

---

# 1. Extract Layer

The extract layer retrieves raw data from external providers and stores it in CSV format.

## FRED Extract

File:

```text
src/extract/fred_extract.py
```

Current series:

- `UNRATE`
- `CPIAUCSL`
- `FEDFUNDS`

Outputs:

```text
data/raw/fred_UNRATE.csv
data/raw/fred_CPIAUCSL.csv
data/raw/fred_FEDFUNDS.csv
```

## OpenBB Market Extract

File:

```text
src/extract/openbb_market_extract.py
```

OpenBB is used as a unified market-data interface. The current provider is `yfinance`.

Index route instruments:

- `^GSPC`
- `^DJI`
- `^IXIC`
- `^TNX`
- `^TYX`
- `DX-Y.NYB`

Futures route instruments:

- `ES=F`
- `YM=F`

Output:

```text
data/raw/openbb_market_data.csv
```

The extractor:

- Uses separate OpenBB index and futures endpoints
- Preserves provider metadata
- Standardises output columns
- Continues processing when one symbol fails
- Applies a delay between requests
- Reports successful and failed symbols

## Sina China Stock Extract

File:

```text
src/extract/sina_stock_extract.py
```

Output:

```text
data/raw/sina_stock_quotes_raw.csv
```

---

# 2. Transform Layer

The transform layer standardises raw data and calculates derived variables.

## Macro Transform

File:

```text
src/transform/macro_transform.py
```

Responsibilities:

- Combine FRED series
- Convert dates
- Standardise metadata
- Prepare values for database loading

Output:

```text
data/processed/macro_indicators_processed.csv
```

## OpenBB Market Transform

File:

```text
src/transform/transform_openbb_market.py
```

Responsibilities:

- Validate the expected raw schema
- Convert dates and numeric fields
- Standardise text fields
- Remove unusable rows
- Remove duplicate symbol/date observations
- Preserve provider and extraction metadata
- Calculate financial features
- Add transformation timestamps

Derived fields:

```text
daily_return
log_return
intraday_return
daily_range_pct
ohlc_valid
transformed_at
```

Output:

```text
data/processed/openbb_market_data_clean.csv
```

## China Stock Transform

File:

```text
src/transform/china_stock_transform.py
```

Responsibilities:

- Preserve leading-zero symbols
- Parse A-share and Hong Kong timestamps
- Standardise numeric fields
- Handle missing values
- Calculate bid/ask metrics
- Prepare quote snapshots for PostgreSQL

Output:

```text
data/processed/china_stock_quotes_clean.csv
```

---

# 3. Data Quality Layer

File:

```text
src/quality/data_checks.py
```

## Macro Checks

- Required-field missing values
- Duplicate natural keys
- Date freshness

## OpenBB Market Checks

- Required-field missing values
- Duplicate `date + symbol` keys
- Date freshness
- Negative OHLCV values
- Full OHLC consistency
- Extreme return detection
- Expected symbol coverage

## Warning Investigation

Rows with inconsistent OHLC relationships are retained and exported for manual review:

```text
data/processed/ohlc_inconsistency_investigation.csv
```

Quality output:

```text
data/processed/data_quality_results.csv
```

---

# 4. Load Layer

## Macro Loader

File:

```text
src/load/load_macro_to_postgres.py
```

Target:

```sql
macro_indicators
```

## OpenBB Market Loader

File:

```text
src/load/load_openbb_market_to_postgres.py
```

Target:

```sql
openbb_market_data
```

Natural key:

```sql
UNIQUE (symbol, date)
```

Features:

- Automatic table creation
- Index creation
- Batch UPSERT
- Provider metadata retention
- Post-load verification
- Duplicate-group validation
- Date-range validation
- Symbol-level row summaries

## China Stock Loader

File:

```text
src/load/load_china_stock_to_postgres.py
```

Target:

```sql
stock_quotes
```

## Data Quality Loader

File:

```text
src/load/load_quality_to_postgres.py
```

Target:

```sql
data_quality_results
```

The quality-results table uses append-only loading.

---

# 5. Orchestration Layer

File:

```text
main.py
```

Current execution order:

```text
1. Extract FRED macroeconomic data
2. Extract financial market data through OpenBB
3. Extract Sina China stock quote data

4. Transform macroeconomic data
5. Transform OpenBB financial market data
6. Transform China stock quote data

7. Run data quality checks

8. Load macroeconomic data into PostgreSQL
9. Load OpenBB financial market data into PostgreSQL
10. Load China stock quote data into PostgreSQL
11. Load quality results into PostgreSQL
```

The orchestrator stops on an unhandled step failure and logs the full traceback.

---

# 6. Logging and Observability

Logger:

```text
src/utils/logger.py
```

Current features:

- Pipeline start and completion
- Step-level start and completion
- Per-step runtime
- Total runtime
- Failure location
- Exception details
- Full traceback

A successful run on 12 June 2026 completed all 11 steps in:

```text
61.66 seconds
```

---

# 7. Database Layer

PostgreSQL version:

```text
PostgreSQL 17
```

Core tables:

```sql
macro_indicators
openbb_market_data
stock_quotes
data_quality_results
```

| Table | Strategy |
|---|---|
| `macro_indicators` | UPSERT |
| `openbb_market_data` | UPSERT |
| `stock_quotes` | UPSERT |
| `data_quality_results` | Append-only |

---

# 8. OpenBB Data Lineage

```text
OpenBB
  │
  └── yfinance provider
        │
        ▼
openbb_market_data.csv
        │
        ▼
transform_openbb_market.py
        │
        ▼
openbb_market_data_clean.csv
        │
        ├── data_checks.py
        │     └── data_quality_results.csv
        │
        ▼
load_openbb_market_to_postgres.py
        │
        ▼
PostgreSQL: openbb_market_data
```

Provider, extraction, transformation, and load timestamps support traceability.

---

# 9. Error-Handling Strategy

- Missing input files raise explicit errors.
- Missing required columns stop transformation or loading.
- Individual OpenBB symbol failures are collected without immediately stopping the full extraction batch.
- The pipeline stops when a critical orchestration step raises an exception.
- Quality warnings do not stop valid data from loading.
- PostgreSQL transactions are handled through SQLAlchemy context managers.

---

# 10. Planned Improvements

- Lightweight Streamlit pipeline-monitoring dashboard
- Incremental extraction based on the latest stored date
- Pipeline-run metadata table
- Docker containerisation
- Scheduled execution
- Cloud deployment
- CI/CD checks
- Automated database health monitoring
- Optional Apache Airflow orchestration
