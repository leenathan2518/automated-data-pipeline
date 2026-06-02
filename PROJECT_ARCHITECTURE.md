# PROJECT_ARCHITECTURE

## System Overview

The Automated Data Pipeline follows a layered ETL architecture.

```text
External Data Sources
        │
        ▼
┌─────────────────────┐
│   Extract Layer     │
└─────────────────────┘
        │
        ▼
┌─────────────────────┐
│  Transform Layer    │
└─────────────────────┘
        │
        ▼
┌─────────────────────┐
│ Data Quality Layer  │
└─────────────────────┘
        │
        ▼
┌─────────────────────┐
│    Load Layer       │
└─────────────────────┘
        │
        ▼
┌─────────────────────┐
│    PostgreSQL       │
└─────────────────────┘
```

---

# Extract Layer

The extract layer retrieves raw data from external providers.

## FRED Extract

File:

```text
src/extract/fred_extract.py
```

Data:

* UNRATE
* CPIAUCSL
* FEDFUNDS

Output:

```text
data/raw/fred_UNRATE.csv
data/raw/fred_CPIAUCSL.csv
data/raw/fred_FEDFUNDS.csv
```

---

## Market Extract

File:

```text
src/extract/market_extract.py
```

Data:

* SPY
* QQQ
* GLD
* CL=F
* DX-Y.NYB
* ^TNX
* ^TYX
* YM=F
* ES=F

Output:

```text
data/raw/market_*.csv
```

---

## China Stock Extract

File:

```text
src/extract/sina_stock_extract.py
```

Data:

A-share:

* Ping An Bank
* China Merchants Bank
* Kweichow Moutai
* CATL
* BYD
* SMIC

Hong Kong Share:

* Tencent
* Alibaba
* Meituan

Output:

```text
data/raw/sina_stock_quotes_raw.csv
```

---

# Transform Layer

The transform layer standardizes raw data before loading.

## Macro Transform

File:

```text
src/transform/macro_transform.py
```

Functions:

* Datetime conversion
* Column standardisation
* Missing value handling

Output:

```text
data/processed/
```

---

## Market Transform

File:

```text
src/transform/market_transform.py
```

Functions:

* Date conversion
* Numeric conversion
* Data cleaning

Output:

```text
data/processed/
```

---

## China Stock Transform

File:

```text
src/transform/china_stock_transform.py
```

Functions:

* Preserve leading-zero stock symbols
* Parse A-share timestamps
* Parse Hong Kong timestamps
* Handle missing values
* Calculate bid/ask metrics
* Standardize data types

Output:

```text
data/processed/china_stock_quotes_clean.csv
```

---

# Data Quality Layer

File:

```text
src/quality/data_checks.py
```

Checks:

* Row count validation
* Missing value checks
* Duplicate checks
* Data freshness validation

Output:

```text
data_quality_results
```

---

# Load Layer

The load layer inserts cleaned data into PostgreSQL.

## Macro Loader

File:

```text
src/load/load_macro_to_postgres.py
```

Target Table:

```sql
macro_indicators
```

---

## Market Loader

File:

```text
src/load/load_market_to_postgres.py
```

Target Table:

```sql
market_prices
```

---

## China Stock Loader

File:

```text
src/load/load_china_stock_to_postgres.py
```

Target Table:

```sql
stock_quotes
```

Features:

* UPSERT support
* Duplicate prevention
* NULL handling

---

## Data Quality Loader

File:

```text
src/load/load_quality_to_postgres.py
```

Target Table:

```sql
data_quality_results
```

---

# Orchestration Layer

File:

```text
main.py
```

Pipeline Execution Order:

```text
1. Extract FRED data
2. Extract market data
3. Extract China stock data

4. Transform macro data
5. Transform market data
6. Transform stock data

7. Run quality checks

8. Load macro data
9. Load market data
10. Load stock data
11. Load quality results
```

---

# Logging

File:

```text
src/utils/logger.py
```

Features:

* Step-level logging
* Runtime tracking
* Exception tracking
* Pipeline monitoring

---

# Database

PostgreSQL Version:

```text
PostgreSQL 17
```

Core Tables:

```sql
macro_indicators
market_prices
stock_quotes
data_quality_results
```

---

# Future Improvements

* Apache Airflow orchestration
* Docker containerisation
* Incremental extraction
* Cloud deployment
* Automated monitoring dashboard
* Data warehouse modelling
* CI/CD integration
