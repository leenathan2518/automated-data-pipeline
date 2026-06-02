# Automated Data Pipeline

## Project Overview

Automated Data Pipeline is an end-to-end ETL (Extract, Transform, Load) project built with Python and PostgreSQL. The pipeline automatically collects macroeconomic indicators, financial market data, and China stock market data from multiple external sources, performs data transformation and quality validation, and loads the cleaned data into a PostgreSQL data warehouse.

The project demonstrates practical data engineering skills including API integration, web data extraction, data cleaning, automated workflows, database design, logging, and data quality monitoring.

---

## Project Architecture

```text
                 ┌───────────────┐
                 │     FRED      │
                 └───────┬───────┘
                         │
                 ┌───────▼───────┐
                 │   Yahoo API   │
                 └───────┬───────┘
                         │
                 ┌───────▼───────┐
                 │ Sina Finance  │
                 └───────┬───────┘
                         │
                         ▼

                EXTRACT LAYER
                         │
                         ▼

               TRANSFORM LAYER
                         │
                         ▼

            DATA QUALITY CHECKS
                         │
                         ▼

                LOAD LAYER
                         │
                         ▼

                  PostgreSQL
```

---

## Data Sources

### Macroeconomic Indicators (FRED)

* UNRATE (Unemployment Rate)
* CPIAUCSL (Consumer Price Index)
* FEDFUNDS (Federal Funds Rate)

Source:
https://fred.stlouisfed.org/

---

### Financial Market Data (Yahoo Finance)

* SPY (S&P 500 ETF)
* QQQ (NASDAQ ETF)
* GLD (Gold ETF)
* CL=F (Crude Oil Futures)
* DX-Y.NYB (US Dollar Index)
* ^TNX (10-Year Treasury Yield)
* ^TYX (30-Year Treasury Yield)
* YM=F (Dow Futures)
* ES=F (S&P Futures)

Source:
https://finance.yahoo.com/

---

### China Stock Market Data (Sina Finance)

A-share Examples:

* Ping An Bank
* China Merchants Bank
* Kweichow Moutai
* CATL
* BYD
* SMIC

Hong Kong Share Examples:

* Tencent
* Alibaba
* Meituan

Source:
https://finance.sina.com.cn/

---

## ETL Workflow

### Step 1 – Extract

Extract data from:

* FRED API
* Yahoo Finance API
* Sina Finance

Output:

```text
data/raw/
```

---

### Step 2 – Transform

Perform:

* Data type conversion
* Datetime standardization
* Missing value handling
* Symbol normalization
* Feature calculation
* Data cleaning

Output:

```text
data/processed/
```

---

### Step 3 – Data Quality Validation

Automated checks:

* Row count validation
* Null value checks
* Duplicate checks
* Data freshness checks

Output:

```text
data_quality_results
```

---

### Step 4 – Load

Load cleaned data into PostgreSQL:

Tables:

* macro_indicators
* market_prices
* stock_quotes
* data_quality_results

PostgreSQL UPSERT logic prevents duplicate records using:

```sql
ON CONFLICT DO UPDATE
```

---

## Technologies Used

### Programming

* Python 3.12

### Data Processing

* Pandas
* NumPy

### Data Collection

* FredAPI
* yfinance
* requests

### Database

* PostgreSQL 17
* SQLAlchemy
* psycopg2

### Development Tools

* PyCharm
* Git
* GitHub

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
│
│   ├── extract/
│   ├── transform/
│   ├── quality/
│   ├── load/
│   └── utils/
│
├── main.py
│
└── README.md
```

---

## Pipeline Execution

Run the complete pipeline:

```bash
python main.py
```

Pipeline Steps:

1. Extract FRED data
2. Extract market data
3. Extract China stock data
4. Transform macro data
5. Transform market data
6. Transform stock data
7. Run data quality checks
8. Load macro data
9. Load market data
10. Load stock data
11. Load quality results

---

## Sample Runtime

```text
Total Runtime: ~126 seconds
```

---

## Key Data Engineering Concepts Demonstrated

* ETL Pipeline Design
* Data Warehouse Loading
* PostgreSQL Integration
* Incremental Loading (UPSERT)
* Data Quality Monitoring
* Structured Logging
* Automated Workflow Orchestration
* API Integration
* Financial Data Engineering

---

## Author

Vinci Lee

Master of Applied Economics

Bachelor of Statistics

Data Analytics | Data Engineering | Applied Economics
