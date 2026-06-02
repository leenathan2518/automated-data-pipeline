"""
load_china_stock_to_postgres.py

Load cleaned Sina Finance China stock quote data into PostgreSQL.

This module loads the transformed A-share and Hong Kong stock quote
data from data/processed/china_stock_quotes_clean.csv into the
stock_quotes table.

Main features:
- Read cleaned stock quote CSV
- Preserve stock symbols as strings
- Convert datetime columns safely
- Convert empty / NaN / NaT values to None
- Insert data into PostgreSQL
- Avoid duplicate records using PostgreSQL ON CONFLICT

Author
------
Vinci Lee
"""

from pathlib import Path

import pandas as pd
from sqlalchemy import text

from src.load.db_connection import get_engine


INPUT_FILE = Path("data/processed/china_stock_quotes_clean.csv")


NUMERIC_COLUMNS = [
    "open", "previous_close", "current_price", "high", "low",
    "price_change", "pct_change",
    "volume", "amount",

    "bid1_volume", "bid1_price",
    "bid2_volume", "bid2_price",
    "bid3_volume", "bid3_price",
    "bid4_volume", "bid4_price",
    "bid5_volume", "bid5_price",

    "ask1_volume", "ask1_price",
    "ask2_volume", "ask2_price",
    "ask3_volume", "ask3_price",
    "ask4_volume", "ask4_price",
    "ask5_volume", "ask5_price",

    "bid_volume_total", "ask_volume_total",
    "bid_ask_volume_diff",
    "bid_ask_spread", "order_imbalance",
]


TEXT_COLUMNS = [
    "symbol", "sina_symbol", "name_en", "name_cn", "market", "source",
]


DATETIME_COLUMNS = [
    "trade_datetime", "extracted_at",
]


def clean_value(value):
    """
    Convert pandas missing values to Python None.

    PostgreSQL accepts None as NULL, but it does not accept pandas NaT.
    """

    if pd.isna(value):
        return None

    return value


def load_china_stock_data() -> None:
    """
    Load cleaned Sina stock quote data into PostgreSQL.
    """

    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            f"Input file not found: {INPUT_FILE}. "
            "Please run: python -m src.transform.china_stock_transform"
        )

    df = pd.read_csv(
        INPUT_FILE,
        dtype={
            "symbol": "string",
            "sina_symbol": "string",
            "name_en": "string",
            "name_cn": "string",
            "market": "string",
            "source": "string",
        },
        keep_default_na=True,
    )

    # Clean text columns
    for col in TEXT_COLUMNS:
        if col in df.columns:
            df[col] = df[col].astype("string").str.strip()

    # Convert numeric columns
    for col in NUMERIC_COLUMNS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # Convert datetime columns
    for col in DATETIME_COLUMNS:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")

    # Drop invalid rows
    df = df.dropna(
        subset=[
            "symbol",
            "sina_symbol",
            "market",
            "trade_datetime",
        ]
    )

    # Convert pandas Timestamp to normal Python datetime
    for col in DATETIME_COLUMNS:
        if col in df.columns:
            df[col] = df[col].dt.to_pydatetime()

    # Convert pandas NA / NaN / NaT to Python None
    df = df.astype(object)
    df = df.map(clean_value)

    records = df.to_dict(orient="records")

    if not records:
        raise ValueError(
            "No valid records found in cleaned China stock quote CSV."
        )

    print("Preview before loading:")
    print(
        df[
            [
                "symbol",
                "sina_symbol",
                "market",
                "trade_datetime",
                "extracted_at",
            ]
        ]
    )

    engine = get_engine()

    insert_sql = text(
        """
        INSERT INTO stock_quotes (
            symbol,
            sina_symbol,
            name_en,
            name_cn,
            market,

            open,
            previous_close,
            current_price,
            high,
            low,

            price_change,
            pct_change,

            volume,
            amount,

            bid1_volume,
            bid1_price,
            bid2_volume,
            bid2_price,
            bid3_volume,
            bid3_price,
            bid4_volume,
            bid4_price,
            bid5_volume,
            bid5_price,

            ask1_volume,
            ask1_price,
            ask2_volume,
            ask2_price,
            ask3_volume,
            ask3_price,
            ask4_volume,
            ask4_price,
            ask5_volume,
            ask5_price,

            bid_volume_total,
            ask_volume_total,
            bid_ask_volume_diff,
            bid_ask_spread,
            order_imbalance,

            trade_datetime,
            source,
            extracted_at
        )
        VALUES (
            :symbol,
            :sina_symbol,
            :name_en,
            :name_cn,
            :market,

            :open,
            :previous_close,
            :current_price,
            :high,
            :low,

            :price_change,
            :pct_change,

            :volume,
            :amount,

            :bid1_volume,
            :bid1_price,
            :bid2_volume,
            :bid2_price,
            :bid3_volume,
            :bid3_price,
            :bid4_volume,
            :bid4_price,
            :bid5_volume,
            :bid5_price,

            :ask1_volume,
            :ask1_price,
            :ask2_volume,
            :ask2_price,
            :ask3_volume,
            :ask3_price,
            :ask4_volume,
            :ask4_price,
            :ask5_volume,
            :ask5_price,

            :bid_volume_total,
            :ask_volume_total,
            :bid_ask_volume_diff,
            :bid_ask_spread,
            :order_imbalance,

            :trade_datetime,
            :source,
            :extracted_at
        )
        ON CONFLICT (symbol, market, trade_datetime)
        DO UPDATE SET
            sina_symbol = EXCLUDED.sina_symbol,
            name_en = EXCLUDED.name_en,
            name_cn = EXCLUDED.name_cn,

            open = EXCLUDED.open,
            previous_close = EXCLUDED.previous_close,
            current_price = EXCLUDED.current_price,
            high = EXCLUDED.high,
            low = EXCLUDED.low,

            price_change = EXCLUDED.price_change,
            pct_change = EXCLUDED.pct_change,

            volume = EXCLUDED.volume,
            amount = EXCLUDED.amount,

            bid1_volume = EXCLUDED.bid1_volume,
            bid1_price = EXCLUDED.bid1_price,
            bid2_volume = EXCLUDED.bid2_volume,
            bid2_price = EXCLUDED.bid2_price,
            bid3_volume = EXCLUDED.bid3_volume,
            bid3_price = EXCLUDED.bid3_price,
            bid4_volume = EXCLUDED.bid4_volume,
            bid4_price = EXCLUDED.bid4_price,
            bid5_volume = EXCLUDED.bid5_volume,
            bid5_price = EXCLUDED.bid5_price,

            ask1_volume = EXCLUDED.ask1_volume,
            ask1_price = EXCLUDED.ask1_price,
            ask2_volume = EXCLUDED.ask2_volume,
            ask2_price = EXCLUDED.ask2_price,
            ask3_volume = EXCLUDED.ask3_volume,
            ask3_price = EXCLUDED.ask3_price,
            ask4_volume = EXCLUDED.ask4_volume,
            ask4_price = EXCLUDED.ask4_price,
            ask5_volume = EXCLUDED.ask5_volume,
            ask5_price = EXCLUDED.ask5_price,

            bid_volume_total = EXCLUDED.bid_volume_total,
            ask_volume_total = EXCLUDED.ask_volume_total,
            bid_ask_volume_diff = EXCLUDED.bid_ask_volume_diff,
            bid_ask_spread = EXCLUDED.bid_ask_spread,
            order_imbalance = EXCLUDED.order_imbalance,

            source = EXCLUDED.source,
            extracted_at = EXCLUDED.extracted_at;
        """
    )

    with engine.begin() as conn:
        conn.execute(insert_sql, records)

    print("=" * 60)
    print(f"Loaded {len(records)} stock quote records into PostgreSQL.")
    print("=" * 60)


if __name__ == "__main__":
    load_china_stock_data()


