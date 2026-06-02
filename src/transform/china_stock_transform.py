"""
Transform China stock quote CSV before loading into PostgreSQL.

This script cleans data exported by sina_stock_extract.py:
1. Keeps stock symbols as strings, preserving leading zeros.
2. Parses both A-share and HK-share datetime formats.
3. Fills missing trade_datetime with extracted_at only if necessary.
4. Converts numeric columns safely.
5. Recalculates bid/ask derived fields.
6. Exports a cleaned CSV for PostgreSQL loading.
"""

from pathlib import Path

import pandas as pd


RAW_FILE = Path("data/raw/sina_stock_quotes_raw.csv")
PROCESSED_FILE = Path("data/processed/china_stock_quotes_clean.csv")


NUMERIC_COLUMNS = [
    "open", "previous_close", "current_price", "high", "low",
    "price_change", "pct_change", "volume", "amount",

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
    "bid_ask_volume_diff", "bid_ask_spread", "order_imbalance",
]


BID_VOLUME_COLUMNS = [
    "bid1_volume", "bid2_volume", "bid3_volume", "bid4_volume", "bid5_volume"
]

ASK_VOLUME_COLUMNS = [
    "ask1_volume", "ask2_volume", "ask3_volume", "ask4_volume", "ask5_volume"
]


def transform_china_stock_quotes(
    input_path: Path = RAW_FILE,
    output_path: Path = PROCESSED_FILE,
) -> pd.DataFrame:
    """
    Clean China stock quote data and export a PostgreSQL-ready CSV.
    """

    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    # Important:
    # keep_default_na=False prevents empty cells from immediately becoming NaN strings.
    # symbol and sina_symbol must be read as strings to preserve leading zeros.
    df = pd.read_csv(
        input_path,
        dtype={
            "symbol": "string",
            "sina_symbol": "string",
            "name_en": "string",
            "name_cn": "string",
            "market": "string",
            "source": "string",
        },
        keep_default_na=False,
    )

    # Clean text fields
    text_columns = ["symbol", "sina_symbol", "name_en", "name_cn", "market", "source"]
    for col in text_columns:
        if col in df.columns:
            df[col] = df[col].astype("string").str.strip()

    # Do NOT use zfill here.
    # A-share symbols are usually 6 digits, HK-share symbols are usually 5 digits.
    # The raw CSV already contains correct symbols such as 000001, 002594, 00700, 09988.
    df["symbol"] = df["symbol"].astype("string").str.strip()

    # Standardise datetime text before parsing.
    # A-share example: 2026-06-02 15:00:00
    # HK-share example: 2026/06/02 16:08
    df["trade_datetime"] = (
        df["trade_datetime"]
        .astype("string")
        .str.strip()
        .str.replace("/", "-", regex=False)
    )

    df["extracted_at"] = (
        df["extracted_at"]
        .astype("string")
        .str.strip()
        .str.replace("/", "-", regex=False)
    )

    df["trade_datetime"] = pd.to_datetime(df["trade_datetime"], errors="coerce")
    df["extracted_at"] = pd.to_datetime(df["extracted_at"], errors="coerce")

    # Only use extracted_at as fallback when trade_datetime is truly missing.
    df["trade_datetime"] = df["trade_datetime"].fillna(df["extracted_at"])

    # Convert numeric columns safely.
    # Empty strings will become NaN.
    for col in NUMERIC_COLUMNS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # Recalculate derived fields.
    # For HK shares, volume columns may be missing, so min_count=1 keeps all-missing rows as NaN.
    df["bid_volume_total"] = df[BID_VOLUME_COLUMNS].sum(axis=1, min_count=1)
    df["ask_volume_total"] = df[ASK_VOLUME_COLUMNS].sum(axis=1, min_count=1)

    df["bid_ask_volume_diff"] = df["bid_volume_total"] - df["ask_volume_total"]

    df["bid_ask_spread"] = df["ask1_price"] - df["bid1_price"]

    denominator = df["bid_volume_total"] + df["ask_volume_total"]
    df["order_imbalance"] = df["bid_ask_volume_diff"] / denominator
    df.loc[denominator == 0, "order_imbalance"] = pd.NA

    # Remove rows without essential identifiers.
    df = df.dropna(subset=["symbol", "sina_symbol", "market", "trade_datetime"])

    # Export cleaned CSV.
    output_path.parent.mkdir(parents=True, exist_ok=True)

    df.to_csv(
        output_path,
        index=False,
        encoding="utf-8-sig",
        na_rep="",
        date_format="%Y-%m-%d %H:%M:%S",
    )

    print("=" * 60)
    print("China stock quote transformation completed")
    print(f"Input file:  {input_path}")
    print(f"Output file: {output_path}")
    print(f"Rows: {len(df)}")
    print("=" * 60)

    print("\nPreview:")
    print(df[["symbol", "sina_symbol", "market", "trade_datetime", "extracted_at"]])

    return df


if __name__ == "__main__":
    transform_china_stock_quotes()



