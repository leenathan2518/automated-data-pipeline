"""
Transform raw OpenBB market data.

This module:
1. Reads the raw OpenBB CSV file.
2. Standardizes dates and numeric columns.
3. Removes invalid and duplicate observations.
4. Adds derived market-return fields.
5. Saves a clean processed dataset for PostgreSQL loading.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]

INPUT_FILE = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "openbb_market_data.csv"
)

OUTPUT_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "openbb_market_data_clean.csv"
)


NUMERIC_COLUMNS = [
    "open",
    "high",
    "low",
    "close",
    "volume",
]


REQUIRED_COLUMNS = [
    "date",
    "symbol",
    "asset_name",
    "asset_type",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "provider",
    "extracted_at",
]


def load_raw_market_data() -> pd.DataFrame:
    """Load the raw OpenBB market data CSV."""

    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            f"Raw OpenBB market file was not found: {INPUT_FILE}"
        )

    df = pd.read_csv(INPUT_FILE)

    print("=" * 70)
    print("OPENBB MARKET DATA TRANSFORMATION")
    print("=" * 70)
    print(f"Input file: {INPUT_FILE}")
    print(f"Raw rows: {len(df):,}")

    return df


def validate_schema(df: pd.DataFrame) -> None:
    """Validate that all expected OpenBB columns are present."""

    missing_columns = [
        column
        for column in REQUIRED_COLUMNS
        if column not in df.columns
    ]

    if missing_columns:
        raise ValueError(
            "Missing required columns: "
            + ", ".join(missing_columns)
        )


def clean_market_data(df: pd.DataFrame) -> pd.DataFrame:
    """Clean and standardize the OpenBB market dataset."""

    cleaned = df.copy()

    validate_schema(cleaned)

    # Standardize date fields.
    cleaned["date"] = pd.to_datetime(
        cleaned["date"],
        errors="coerce",
    )

    cleaned["extracted_at"] = pd.to_datetime(
        cleaned["extracted_at"],
        errors="coerce",
    )

    # Standardize text fields.
    text_columns = [
        "symbol",
        "asset_name",
        "asset_type",
        "provider",
    ]

    for column in text_columns:
        cleaned[column] = (
            cleaned[column]
            .astype("string")
            .str.strip()
        )

    # Convert price and volume fields to numeric.
    for column in NUMERIC_COLUMNS:
        cleaned[column] = pd.to_numeric(
            cleaned[column],
            errors="coerce",
        )

    # Remove records that cannot identify an instrument or observation.
    cleaned = cleaned.dropna(
        subset=[
            "date",
            "symbol",
            "close",
        ]
    )

    # Prices and yields should not be negative.
    price_columns = [
        "open",
        "high",
        "low",
        "close",
    ]

    for column in price_columns:
        cleaned.loc[
            cleaned[column] < 0,
            column,
        ] = np.nan

    # Volume may legitimately be zero for yield indices.
    cleaned.loc[
        cleaned["volume"] < 0,
        "volume",
    ] = np.nan

    # Remove duplicate symbol/date records.
    cleaned = cleaned.sort_values(
        by=[
            "symbol",
            "date",
            "extracted_at",
        ]
    )

    cleaned = cleaned.drop_duplicates(
        subset=[
            "symbol",
            "date",
        ],
        keep="last",
    )

    # Check OHLC consistency.
    cleaned["ohlc_valid"] = (
        cleaned["high"].isna()
        | cleaned["low"].isna()
        | (
            cleaned["high"]
            >= cleaned["low"]
        )
    )

    # Calculate daily simple return and logarithmic return.
    cleaned = cleaned.sort_values(
        by=[
            "symbol",
            "date",
        ]
    )

    cleaned["daily_return"] = (
        cleaned
        .groupby("symbol")["close"]
        .pct_change()
    )

    cleaned["log_return"] = (
        cleaned
        .groupby("symbol")["close"]
        .transform(
            lambda series: np.log(
                series / series.shift(1)
            )
        )
    )

    # Intraday percentage movement.
    cleaned["intraday_return"] = np.where(
        cleaned["open"].notna()
        & cleaned["close"].notna()
        & cleaned["open"].ne(0),
        (
            cleaned["close"]
            - cleaned["open"]
        )
        / cleaned["open"],
        np.nan,
    )

    # Daily trading range relative to the opening value.
    cleaned["daily_range_pct"] = np.where(
        cleaned["open"].notna()
        & cleaned["high"].notna()
        & cleaned["low"].notna()
        & cleaned["open"].ne(0),
        (
            cleaned["high"]
            - cleaned["low"]
        )
        / cleaned["open"],
        np.nan,
    )

    # Add ETL metadata.
    cleaned["transformed_at"] = pd.Timestamp.now()

    cleaned = cleaned.reset_index(drop=True)

    return cleaned


def print_quality_summary(df: pd.DataFrame) -> None:
    """Print a concise quality and transformation summary."""

    print("\n" + "=" * 70)
    print("TRANSFORMATION SUMMARY")
    print("=" * 70)

    print(f"Clean rows: {len(df):,}")
    print(f"Symbols: {df['symbol'].nunique()}")
    print(
        f"Date range: "
        f"{df['date'].min().date()} to "
        f"{df['date'].max().date()}"
    )

    print(
        "Invalid OHLC rows: "
        f"{(~df['ohlc_valid']).sum():,}"
    )

    print(
        "Missing close values: "
        f"{df['close'].isna().sum():,}"
    )

    print(
        "Duplicate symbol/date rows: "
        f"{df.duplicated(['symbol', 'date']).sum():,}"
    )

    print("\nRows by symbol:")

    summary = (
        df.groupby(
            [
                "symbol",
                "asset_name",
                "asset_type",
            ]
        )
        .size()
        .rename("rows")
    )

    print(summary)


def save_clean_market_data(
    df: pd.DataFrame,
) -> Path:
    """Save the transformed OpenBB dataset."""

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    df.to_csv(
        OUTPUT_FILE,
        index=False,
        date_format="%Y-%m-%d",
    )

    print(f"\nSaved to: {OUTPUT_FILE}")

    return OUTPUT_FILE


def transform_openbb_market_data() -> pd.DataFrame:
    """Run the complete OpenBB transformation process."""

    raw_df = load_raw_market_data()

    clean_df = clean_market_data(raw_df)

    print_quality_summary(clean_df)

    save_clean_market_data(clean_df)

    return clean_df


def main() -> None:
    """Run the transformation script directly."""

    clean_df = transform_openbb_market_data()

    print("\nSample:")
    print(
        clean_df[
            [
                "date",
                "symbol",
                "close",
                "daily_return",
                "log_return",
                "intraday_return",
                "daily_range_pct",
            ]
        ].tail(10)
    )


if __name__ == "__main__":
    main()

