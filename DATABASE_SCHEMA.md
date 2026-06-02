# DATABASE_SCHEMA

## Overview

This document describes the PostgreSQL database schema used in the Automated Data Pipeline project.

The database stores cleaned and structured data from:

* FRED macroeconomic indicators
* Yahoo Finance market prices
* Sina Finance China stock quotes
* Automated data quality checks

Core tables:

```sql
macro_indicators
market_prices
stock_quotes
data_quality_results
```

---

# 1. macro_indicators

## Purpose

Stores macroeconomic time series extracted from FRED.

Examples:

* Unemployment rate
* Consumer price index
* Federal funds rate

## Suggested Schema

```sql
CREATE TABLE IF NOT EXISTS macro_indicators (
    id SERIAL PRIMARY KEY,
    indicator_code VARCHAR(50) NOT NULL,
    indicator_name VARCHAR(255),
    date DATE NOT NULL,
    value NUMERIC(20, 6),
    source VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT unique_macro_indicator_date
        UNIQUE (indicator_code, date)
);
```

## Key Fields

| Column         | Description                   |
| -------------- | ----------------------------- |
| id             | Internal primary key          |
| indicator_code | FRED series code              |
| indicator_name | Human-readable indicator name |
| date           | Observation date              |
| value          | Indicator value               |
| source         | Data source                   |
| created_at     | Record creation timestamp     |

## Duplicate Handling

The loader uses UPSERT logic based on:

```sql
UNIQUE (indicator_code, date)
```

This prevents duplicate observations for the same macroeconomic indicator and date.

---

# 2. market_prices

## Purpose

Stores financial market price data extracted from Yahoo Finance.

Examples:

* SPY
* QQQ
* GLD
* Crude oil futures
* Treasury yields
* Dollar index
* Index futures

## Suggested Schema

```sql
CREATE TABLE IF NOT EXISTS market_prices (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(50) NOT NULL,
    asset_name VARCHAR(255),
    asset_type VARCHAR(100),
    date DATE NOT NULL,

    open NUMERIC(20, 6),
    high NUMERIC(20, 6),
    low NUMERIC(20, 6),
    close NUMERIC(20, 6),
    adjusted_close NUMERIC(20, 6),
    volume BIGINT,

    source VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT unique_market_symbol_date
        UNIQUE (symbol, date)
);
```

## Key Fields

| Column         | Description                      |
| -------------- | -------------------------------- |
| id             | Internal primary key             |
| symbol         | Market ticker symbol             |
| asset_name     | Human-readable asset name        |
| asset_type     | ETF, futures, index, yield, etc. |
| date           | Trading date                     |
| open           | Opening price                    |
| high           | Highest price                    |
| low            | Lowest price                     |
| close          | Closing price                    |
| adjusted_close | Adjusted closing price           |
| volume         | Trading volume                   |
| source         | Data source                      |
| created_at     | Record creation timestamp        |

## Duplicate Handling

The loader uses UPSERT logic based on:

```sql
UNIQUE (symbol, date)
```

This prevents duplicate market records for the same asset and date.

---

# 3. stock_quotes

## Purpose

Stores real-time China stock quote data extracted from Sina Finance.

This table contains A-share and Hong Kong share quote data, including price, volume, bid/ask information, and calculated order imbalance indicators.

## Suggested Schema

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

## Key Fields

| Column                   | Description                                          |
| ------------------------ | ---------------------------------------------------- |
| id                       | Internal primary key                                 |
| symbol                   | Stock code, stored as text to preserve leading zeros |
| sina_symbol              | Sina Finance symbol                                  |
| name_en                  | English stock name                                   |
| name_cn                  | Chinese stock name                                   |
| market                   | A-share or HK-share                                  |
| open                     | Opening price                                        |
| previous_close           | Previous closing price                               |
| current_price            | Latest price                                         |
| high                     | Intraday high                                        |
| low                      | Intraday low                                         |
| price_change             | Price change                                         |
| pct_change               | Percentage change                                    |
| volume                   | Trading volume                                       |
| amount                   | Trading amount                                       |
| bid1_price to bid5_price | Top five bid prices                                  |
| ask1_price to ask5_price | Top five ask prices                                  |
| bid_volume_total         | Total bid volume from available levels               |
| ask_volume_total         | Total ask volume from available levels               |
| bid_ask_volume_diff      | Bid volume minus ask volume                          |
| bid_ask_spread           | Best ask price minus best bid price                  |
| order_imbalance          | Bid-ask imbalance indicator                          |
| trade_datetime           | Quote timestamp                                      |
| extracted_at             | Data extraction timestamp                            |

## Duplicate Handling

The loader uses UPSERT logic based on:

```sql
UNIQUE (symbol, market, trade_datetime)
```

This prevents duplicate quote records for the same stock, market, and quote timestamp.

## Important Design Notes

Stock symbols are stored as `VARCHAR`, not numeric types.

This is necessary because many stock codes contain leading zeros:

```text
000001
002594
00700
09988
03690
```

If stock symbols are stored as integers, the leading zeros will be lost.

The `amount` column uses:

```sql
NUMERIC(20, 2)
```

This is necessary because Hong Kong share trading amounts can exceed the range of smaller integer types.

---

# 4. data_quality_results

## Purpose

Stores the results of automated data quality checks.

Unlike the core data tables, this table is designed to keep historical quality check results. Therefore, its row count increases every time the pipeline runs.

## Suggested Schema

```sql
CREATE TABLE IF NOT EXISTS data_quality_results (
    id SERIAL PRIMARY KEY,
    check_name VARCHAR(255) NOT NULL,
    table_name VARCHAR(255),
    check_status VARCHAR(50),
    check_result TEXT,
    checked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## Key Fields

| Column       | Description               |
| ------------ | ------------------------- |
| id           | Internal primary key      |
| check_name   | Name of the quality check |
| table_name   | Table being checked       |
| check_status | PASS, WARNING, or FAIL    |
| check_result | Detailed check result     |
| checked_at   | Check execution timestamp |

## Design Choice

This table is append-only.

Each pipeline run inserts a new batch of quality check results. This allows the project to track historical data quality performance over time.

---

# Recommended Indexes

## macro_indicators

```sql
CREATE INDEX IF NOT EXISTS idx_macro_indicator_code
ON macro_indicators (indicator_code);

CREATE INDEX IF NOT EXISTS idx_macro_date
ON macro_indicators (date);
```

## market_prices

```sql
CREATE INDEX IF NOT EXISTS idx_market_symbol
ON market_prices (symbol);

CREATE INDEX IF NOT EXISTS idx_market_date
ON market_prices (date);
```

## stock_quotes

```sql
CREATE INDEX IF NOT EXISTS idx_stock_symbol
ON stock_quotes (symbol);

CREATE INDEX IF NOT EXISTS idx_stock_market
ON stock_quotes (market);

CREATE INDEX IF NOT EXISTS idx_stock_trade_datetime
ON stock_quotes (trade_datetime);
```

## data_quality_results

```sql
CREATE INDEX IF NOT EXISTS idx_quality_checked_at
ON data_quality_results (checked_at);

CREATE INDEX IF NOT EXISTS idx_quality_table_name
ON data_quality_results (table_name);
```

---

# Database Design Principles

This database schema follows several practical data engineering principles:

1. Use `VARCHAR` for identifiers such as stock symbols.
2. Use `NUMERIC` for financial values to avoid floating-point precision issues.
3. Use `BIGINT` for large volume fields.
4. Use unique constraints to support UPSERT operations.
5. Preserve historical data quality records.
6. Separate macroeconomic data, market prices, stock quotes, and quality checks into different tables.
7. Use timestamps to support auditability and monitoring.

---

# Current Data Loading Strategy

The pipeline uses two loading patterns:

## Core Data Tables

The following tables use UPSERT logic:

```text
macro_indicators
market_prices
stock_quotes
```

Existing records are updated, and new records are inserted.

## Quality Results Table

The following table uses append-only logic:

```text
data_quality_results
```

Each pipeline run adds a new set of quality check records.
