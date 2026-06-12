# DATABASE_SCHEMA

## Overview

This document describes the PostgreSQL schema used by the Automated Data Pipeline.

The database stores:

- FRED macroeconomic indicators
- OpenBB financial market data
- Sina Finance China stock quotes
- Historical data-quality results

Current core tables:

```sql
macro_indicators
openbb_market_data
stock_quotes
data_quality_results
```

---

# 1. `macro_indicators`

## Purpose

Stores cleaned macroeconomic time series extracted from FRED.

Current indicators include unemployment, CPI, and the federal funds rate.

## Logical Schema

```sql
CREATE TABLE IF NOT EXISTS macro_indicators (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL,
    country VARCHAR(100),
    indicator_code VARCHAR(50) NOT NULL,
    indicator_name VARCHAR(255),
    value NUMERIC(20, 6),
    source VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT unique_macro_indicator_date
        UNIQUE (indicator_code, date)
);
```

## Key Fields

| Column | Description |
|---|---|
| `id` | Internal primary key |
| `date` | Observation date |
| `country` | Country associated with the series |
| `indicator_code` | FRED series identifier |
| `indicator_name` | Human-readable indicator name |
| `value` | Observation value |
| `source` | Original data source |
| `created_at` | Database insertion timestamp |

## Duplicate Handling

```sql
UNIQUE (indicator_code, date)
```

Existing records are updated and new observations are inserted.

---

# 2. `openbb_market_data`

## Purpose

Stores transformed financial market data extracted through OpenBB. The current implementation uses the Yahoo Finance provider for indices, Treasury-yield indices, the US Dollar Index, and equity-index futures.

## Current Schema

```sql
CREATE TABLE IF NOT EXISTS openbb_market_data (
    market_id BIGSERIAL PRIMARY KEY,
    date DATE NOT NULL,
    symbol VARCHAR(30) NOT NULL,
    asset_name VARCHAR(150) NOT NULL,
    asset_type VARCHAR(50) NOT NULL,

    open NUMERIC(20, 8),
    high NUMERIC(20, 8),
    low NUMERIC(20, 8),
    close NUMERIC(20, 8) NOT NULL,
    volume NUMERIC(24, 4),

    provider VARCHAR(50) NOT NULL,
    extracted_at TIMESTAMP,
    transformed_at TIMESTAMP,

    ohlc_valid BOOLEAN,
    daily_return DOUBLE PRECISION,
    log_return DOUBLE PRECISION,
    intraday_return DOUBLE PRECISION,
    daily_range_pct DOUBLE PRECISION,

    loaded_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT uq_openbb_market_symbol_date
        UNIQUE (symbol, date)
);
```

## Key Fields

| Column | Description |
|---|---|
| `market_id` | Internal primary key |
| `date` | Trading or observation date |
| `symbol` | Provider ticker or market symbol |
| `asset_name` | Human-readable asset name |
| `asset_type` | Current values include `index` and `futures` |
| `open` | Opening value |
| `high` | Highest reported value |
| `low` | Lowest reported value |
| `close` | Closing or settlement value |
| `volume` | Reported trading volume |
| `provider` | OpenBB provider used for extraction |
| `extracted_at` | Extraction timestamp |
| `transformed_at` | Transformation timestamp |
| `ohlc_valid` | Transformation-stage OHLC validation flag |
| `daily_return` | Percentage change from the previous close |
| `log_return` | Logarithmic return |
| `intraday_return` | `(close - open) / open` |
| `daily_range_pct` | `(high - low) / open` |
| `loaded_at` | Latest database load timestamp |

## Natural Key and UPSERT

```sql
UNIQUE (symbol, date)
```

The loader uses:

```sql
ON CONFLICT (symbol, date)
DO UPDATE
```

Repeated pipeline runs therefore do not create duplicate symbol/date records.

## Data-Quality Note

Continuous futures and incomplete current-day provider records can occasionally contain OHLC inconsistencies. These rows are retained for traceability and recorded as warnings.

Investigation output:

```text
data/processed/ohlc_inconsistency_investigation.csv
```

---

# 3. `stock_quotes`

## Purpose

Stores current A-share and Hong Kong share quote data extracted from Sina Finance.

The table supports current prices, price changes, volume, amount, available top-five bid and ask levels, bid/ask spread, aggregate bid/ask volume, and order imbalance.

## Logical Schema

```sql
CREATE TABLE IF NOT EXISTS stock_quotes (
    id SERIAL PRIMARY KEY,

    symbol VARCHAR(20) NOT NULL,
    sina_symbol VARCHAR(20) NOT NULL,
    name_en VARCHAR(255),
    name_cn VARCHAR(255),
    market VARCHAR(50) NOT NULL,

    open NUMERIC(20, 6),
    previous_close NUMERIC(20, 6),
    current_price NUMERIC(20, 6),
    high NUMERIC(20, 6),
    low NUMERIC(20, 6),

    price_change NUMERIC(20, 6),
    pct_change NUMERIC(20, 6),

    volume BIGINT,
    amount NUMERIC(20, 2),

    bid1_volume NUMERIC(20, 2),
    bid1_price NUMERIC(20, 6),
    bid2_volume NUMERIC(20, 2),
    bid2_price NUMERIC(20, 6),
    bid3_volume NUMERIC(20, 2),
    bid3_price NUMERIC(20, 6),
    bid4_volume NUMERIC(20, 2),
    bid4_price NUMERIC(20, 6),
    bid5_volume NUMERIC(20, 2),
    bid5_price NUMERIC(20, 6),

    ask1_volume NUMERIC(20, 2),
    ask1_price NUMERIC(20, 6),
    ask2_volume NUMERIC(20, 2),
    ask2_price NUMERIC(20, 6),
    ask3_volume NUMERIC(20, 2),
    ask3_price NUMERIC(20, 6),
    ask4_volume NUMERIC(20, 2),
    ask4_price NUMERIC(20, 6),
    ask5_volume NUMERIC(20, 2),
    ask5_price NUMERIC(20, 6),

    bid_volume_total NUMERIC(20, 2),
    ask_volume_total NUMERIC(20, 2),
    bid_ask_volume_diff NUMERIC(20, 2),
    bid_ask_spread NUMERIC(20, 6),
    order_imbalance NUMERIC(20, 6),

    trade_datetime TIMESTAMP NOT NULL,
    source VARCHAR(100),
    extracted_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT unique_stock_quote
        UNIQUE (symbol, market, trade_datetime)
);
```

## Important Design Notes

Stock symbols are stored as `VARCHAR` to preserve leading zeros:

```text
000001
002594
00700
09988
03690
```

The `amount` field uses `NUMERIC(20, 2)` because trading amounts can exceed the range of smaller integer types.

## Duplicate Handling

```sql
UNIQUE (symbol, market, trade_datetime)
```

---

# 4. `data_quality_results`

## Purpose

Stores historical results from automated quality checks.

Current checks cover:

- Required-field missing values
- Duplicate natural keys
- Date freshness
- Negative values
- OHLC consistency
- Return sanity
- Expected OpenBB symbol coverage

## Current Output Fields

| Column | Description |
|---|---|
| `table_name` | Dataset being checked |
| `check_name` | Name of the quality rule |
| `check_result` | `PASS`, `WARNING`, or `FAIL` |
| `failed_rows` | Number of affected values or rows |
| `details` | Human-readable result details |
| `check_time` | Check execution timestamp |

Representative schema:

```sql
CREATE TABLE IF NOT EXISTS data_quality_results (
    id BIGSERIAL PRIMARY KEY,
    table_name VARCHAR(255),
    check_name VARCHAR(255) NOT NULL,
    check_result VARCHAR(50) NOT NULL,
    failed_rows INTEGER NOT NULL DEFAULT 0,
    details TEXT,
    check_time TIMESTAMP NOT NULL
);
```

This table is append-only so each pipeline run preserves a historical quality snapshot.

---

# Recommended Indexes

## `macro_indicators`

```sql
CREATE INDEX IF NOT EXISTS idx_macro_indicator_code
ON macro_indicators (indicator_code);

CREATE INDEX IF NOT EXISTS idx_macro_date
ON macro_indicators (date);
```

## `openbb_market_data`

```sql
CREATE INDEX IF NOT EXISTS idx_openbb_market_date
ON openbb_market_data (date);

CREATE INDEX IF NOT EXISTS idx_openbb_market_symbol
ON openbb_market_data (symbol);

CREATE INDEX IF NOT EXISTS idx_openbb_market_asset_type
ON openbb_market_data (asset_type);

CREATE INDEX IF NOT EXISTS idx_openbb_market_provider
ON openbb_market_data (provider);
```

## `stock_quotes`

```sql
CREATE INDEX IF NOT EXISTS idx_stock_symbol
ON stock_quotes (symbol);

CREATE INDEX IF NOT EXISTS idx_stock_market
ON stock_quotes (market);

CREATE INDEX IF NOT EXISTS idx_stock_trade_datetime
ON stock_quotes (trade_datetime);
```

## `data_quality_results`

```sql
CREATE INDEX IF NOT EXISTS idx_quality_check_time
ON data_quality_results (check_time);

CREATE INDEX IF NOT EXISTS idx_quality_table_name
ON data_quality_results (table_name);

CREATE INDEX IF NOT EXISTS idx_quality_result
ON data_quality_results (check_result);
```

---

# Data Loading Strategy

## UPSERT Tables

```text
macro_indicators
openbb_market_data
stock_quotes
```

## Append-Only Table

```text
data_quality_results
```

---

# Database Design Principles

1. Use text types for identifiers and symbols.
2. Use `NUMERIC` for stored financial values requiring controlled precision.
3. Use unique natural keys to support idempotent UPSERT operations.
4. Preserve provider and ETL timestamps for lineage and auditability.
5. Separate macroeconomic series, market history, quote snapshots, and quality results.
6. Retain upstream anomalies and record them through explicit quality warnings.
7. Add indexes for common date, symbol, provider, market, and quality queries.
