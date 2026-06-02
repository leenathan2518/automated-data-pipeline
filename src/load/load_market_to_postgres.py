"""
load_market_to_postgres.py

This module loads processed financial market data into PostgreSQL.

Current function:
- Read processed market CSV
- Connect to PostgreSQL
- Upsert data into market_prices table
"""

import os
import sys
import pandas as pd
from sqlalchemy import text


PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "../..")
)
sys.path.append(PROJECT_ROOT)


from src.load.db_connection import get_engine


def load_market_data():
    """
    Load processed market price data into PostgreSQL using UPSERT.

    UPSERT logic:
    - If date + ticker already exists, update the row.
    - If it does not exist, insert a new row.
    """

    csv_path = os.path.join(
        "data",
        "processed",
        "market_prices_processed.csv"
    )

    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"Processed market file not found: {csv_path}")

    df = pd.read_csv(csv_path)

    print(f"Loaded market CSV shape: {df.shape}")

    df["date"] = pd.to_datetime(df["date"]).dt.date

    numeric_columns = [
        "open",
        "high",
        "low",
        "close",
        "adj_close",
        "volume"
    ]

    for col in numeric_columns:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    engine = get_engine()

    with engine.begin() as conn:

        for _, row in df.iterrows():

            query = text("""
                INSERT INTO market_prices
                (
                    date,
                    ticker,
                    asset_name,
                    asset_type,
                    open,
                    high,
                    low,
                    close,
                    adj_close,
                    volume,
                    source
                )
                VALUES
                (
                    :date,
                    :ticker,
                    :asset_name,
                    :asset_type,
                    :open,
                    :high,
                    :low,
                    :close,
                    :adj_close,
                    :volume,
                    :source
                )
                ON CONFLICT (date, ticker)
                DO UPDATE SET
                    asset_name = EXCLUDED.asset_name,
                    asset_type = EXCLUDED.asset_type,
                    open = EXCLUDED.open,
                    high = EXCLUDED.high,
                    low = EXCLUDED.low,
                    close = EXCLUDED.close,
                    adj_close = EXCLUDED.adj_close,
                    volume = EXCLUDED.volume,
                    source = EXCLUDED.source;
            """)

            conn.execute(
                query,
                {
                    "date": row["date"],
                    "ticker": row["ticker"],
                    "asset_name": row["asset_name"],
                    "asset_type": row["asset_type"],
                    "open": None if pd.isna(row["open"]) else row["open"],
                    "high": None if pd.isna(row["high"]) else row["high"],
                    "low": None if pd.isna(row["low"]) else row["low"],
                    "close": None if pd.isna(row["close"]) else row["close"],
                    "adj_close": None if pd.isna(row["adj_close"]) else row["adj_close"],
                    "volume": None if pd.isna(row["volume"]) else int(row["volume"]),
                    "source": row["source"],
                }
            )

    print(
        f"Successfully upserted {len(df)} rows "
        f"into market_prices table."
    )


if __name__ == "__main__":
    load_market_data()

