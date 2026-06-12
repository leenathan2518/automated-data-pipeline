# Automated Data Pipeline

## Project Overview

Automated Data Pipeline is an end-to-end financial data engineering project built with Python and PostgreSQL. It collects macroeconomic indicators, global market data, and China stock quote data from multiple external sources, standardises and validates the data, and loads the processed datasets into PostgreSQL.

The project demonstrates:

- Multi-source data ingestion
- OpenBB provider integration
- API and web-data extraction
- Data transformation and financial feature engineering
- Automated data quality monitoring
- PostgreSQL UPSERT loading
- Structured logging and runtime tracking
- Modular ETL orchestration

---

## System Architecture

```text
FRED ───────────────┐
                    │
OpenBB              ├──> Extract ──> Transform ──> Data Quality ──> PostgreSQL
└─ yfinance provider│
                    │
Sina Finance ───────┘
                                      │
                                      └──> Logging and Monitoring
```

---

## Data Sources

### FRED Macroeconomic Indicators

Current series:

- `UNRATE` — Unemployment Rate
- `CPIAUCSL` — Consumer Price Index for All Urban Consumers
- `FEDFUNDS` — Federal Funds Effective Rate

The current extraction module uses `fredapi`.

### OpenBB Financial Market Data

OpenBB is used as the unified market-data interface, with Yahoo Finance as the current provider.

| Symbol | Asset |
|---|---|
| `^GSPC` | S&P 500 |
| `^DJI` | Dow Jones Industrial Average |
| `^IXIC` | Nasdaq Composite |
| `^TNX` | US 10-Year Treasury Yield |
| `^TYX` | US 30-Year Treasury Yield |
| `DX-Y.NYB` | US Dollar Index |
| `ES=F` | S&P 500 Futures |
| `YM=F` | Dow Jones Futures |

OpenBB provides a consistent interface for index and futures extraction while preserving provider metadata for traceability.

### Sina Finance China Stock Quotes

A-share examples:

- Ping An Bank
- China Merchants Bank
- Kweichow Moutai
- CATL
- BYD
- SMIC

Hong Kong share examples:

- Tencent
- Alibaba
- Meituan

---

## ETL Workflow

### 1. Extract

The pipeline extracts:

- FRED macroeconomic series
- OpenBB market data
- Sina China stock quotes

Raw outputs are saved to:

```text
data/raw/
```

Key files:

```text
data/raw/fred_UNRATE.csv
data/raw/fred_CPIAUCSL.csv
data/raw/fred_FEDFUNDS.csv
data/raw/openbb_market_data.csv
data/raw/sina_stock_quotes_raw.csv
```

### 2. Transform

Transformation tasks include:

- Date and timestamp standardisation
- Numeric type conversion
- Symbol normalisation
- Missing-value handling
- Duplicate removal
- Return calculations
- Intraday movement calculation
- Daily range calculation
- Bid/ask metric calculation
- ETL metadata generation

The OpenBB transformation creates:

```text
daily_return
log_return
intraday_return
daily_range_pct
ohlc_valid
extracted_at
transformed_at
```

Processed outputs are saved to:

```text
data/processed/
```

### 3. Data Quality Validation

Automated checks include:

- Required-field missing values
- Natural-key duplicates
- Date freshness
- Negative price and volume values
- OHLC consistency
- Extreme return detection
- Expected symbol coverage

Known upstream OHLC inconsistencies are recorded as warnings rather than silently removed.

Investigation output:

```text
data/processed/ohlc_inconsistency_investigation.csv
```

Quality results:

```text
data/processed/data_quality_results.csv
```

### 4. PostgreSQL Load

Current core tables:

- `macro_indicators`
- `openbb_market_data`
- `stock_quotes`
- `data_quality_results`

Core datasets use PostgreSQL UPSERT logic:

```sql
ON CONFLICT DO UPDATE
```

The quality-results table is append-only so historical quality performance can be monitored over time.

---

## Project Structure

```text
Automated_Data_Pipeline/
│
├── data/
│   ├── raw/
│   └── processed/
│
├── logs/
│
├── src/
│   ├── extract/
│   │   ├── fred_extract.py
│   │   ├── openbb_market_extract.py
│   │   └── sina_stock_extract.py
│   ├── transform/
│   │   ├── macro_transform.py
│   │   ├── transform_openbb_market.py
│   │   └── china_stock_transform.py
│   ├── quality/
│   │   └── data_checks.py
│   ├── load/
│   │   ├── load_macro_to_postgres.py
│   │   ├── load_openbb_market_to_postgres.py
│   │   ├── load_china_stock_to_postgres.py
│   │   └── load_quality_to_postgres.py
│   └── utils/
│       └── logger.py
│
├── DATABASE_SCHEMA.md
├── PROJECT_ARCHITECTURE.md
├── main.py
├── requirements.txt
└── README.md
```

---

## Pipeline Execution

Install dependencies:

```bash
pip install -r requirements.txt
```

Run the complete pipeline:

```bash
python main.py
```

Current execution sequence:

1. Extract FRED macroeconomic data
2. Extract financial market data through OpenBB
3. Extract Sina China stock quote data
4. Transform macroeconomic data
5. Transform OpenBB financial market data
6. Transform China stock quote data
7. Run data quality checks
8. Load macroeconomic data into PostgreSQL
9. Load OpenBB market data into PostgreSQL
10. Load China stock quote data into PostgreSQL
11. Load quality results into PostgreSQL

---

## Structured Logging

The orchestration layer records:

- Pipeline start and completion
- Step-level start and completion
- Step runtime
- Total runtime
- Failed-step identification
- Full exception traceback

Logger module:

```text
src/utils/logger.py
```

---

## Latest Sample Run

A complete run on 12 June 2026 produced:

| Dataset | Result |
|---|---:|
| FRED macro rows loaded | 591 |
| OpenBB market rows loaded | 2,897 |
| OpenBB symbols | 8 |
| Sina stock quote rows loaded | 9 |
| Quality checks stored | 10 |
| Duplicate OpenBB symbol/date groups | 0 |
| Total runtime | 61.66 seconds |

All 11 steps completed successfully.

The quality layer recorded:

- 2 macro missing values as `WARNING`
- 7 upstream OHLC inconsistencies as `WARNING`
- No OpenBB duplicate, negative-value, freshness, return-sanity, or symbol-coverage failures

---

## Technologies Used

### Programming and Processing

- Python 3.12
- pandas
- NumPy

### Data Collection

- OpenBB
- OpenBB yfinance provider
- fredapi
- requests

### Database

- PostgreSQL 17
- SQLAlchemy
- psycopg2

### Engineering Tools

- PyCharm
- Git
- GitHub

---

## Key Data Engineering Concepts Demonstrated

- Modular ETL architecture
- Multi-provider financial data ingestion
- OpenBB integration
- Data lineage and provider metadata
- Financial feature engineering
- Data quality monitoring
- Exception investigation workflows
- PostgreSQL schema design
- Incremental loading with UPSERT
- Structured logging
- Runtime observability
- Re-runnable workflows

---

## Planned Improvements

- Lightweight Streamlit pipeline-monitoring dashboard
- Incremental date-based extraction
- Historical pipeline-run metadata table
- Docker containerisation
- Scheduled orchestration
- CI/CD validation
- Cloud-hosted PostgreSQL deployment

---

## Author

Vinci Lee

Master of Applied Economics  
Bachelor of Statistics

Data Analytics | Data Engineering | Applied Economics
