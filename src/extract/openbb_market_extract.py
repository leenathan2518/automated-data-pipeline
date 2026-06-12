"""
Extract market data through OpenBB.

This module retrieves:
- US equity indices
- Treasury yield indices
- US Dollar Index
- Equity index futures

The extracted data are standardized into one long-format DataFrame
and saved as a CSV file for the downstream ETL pipeline.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path
import time

import pandas as pd
from openbb import obb


PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_DATA_DIR = PROJECT_ROOT / "data" / "raw"
OUTPUT_FILE = RAW_DATA_DIR / "openbb_market_data.csv"


# Index-type instruments retrieved through OpenBB's index endpoint.
INDEX_SYMBOLS = {
    "^GSPC": "S&P 500",
    "^DJI": "Dow Jones Industrial Average",
    "^IXIC": "Nasdaq Composite",
    "^TNX": "US 10-Year Treasury Yield",
    "^TYX": "US 30-Year Treasury Yield",
    "DX-Y.NYB": "US Dollar Index",
}


# Futures retrieved through OpenBB's futures endpoint.
FUTURES_SYMBOLS = {
    "ES=F": "S&P 500 Futures",
    "YM=F": "Dow Jones Futures",
}


def standardize_market_data(
    df: pd.DataFrame,
    symbol: str,
    asset_name: str,
    asset_type: str,
    provider: str,
) -> pd.DataFrame:
    """
    Convert an OpenBB DataFrame into the pipeline's standard long format.
    """

    if df.empty:
        return pd.DataFrame()

    standardized = df.reset_index().copy()

    # OpenBB normally returns the date as the index.
    if "date" not in standardized.columns:
        first_column = standardized.columns[0]
        standardized = standardized.rename(columns={first_column: "date"})

    standardized["date"] = pd.to_datetime(
        standardized["date"],
        errors="coerce",
    ).dt.date

    required_price_columns = [
        "open",
        "high",
        "low",
        "close",
        "volume",
    ]

    # Some instruments, especially yields, may not contain volume.
    for column in required_price_columns:
        if column not in standardized.columns:
            standardized[column] = pd.NA

    standardized["symbol"] = symbol
    standardized["asset_name"] = asset_name
    standardized["asset_type"] = asset_type
    standardized["provider"] = provider
    standardized["extracted_at"] = pd.Timestamp.now()

    output_columns = [
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

    standardized = standardized[output_columns]

    standardized = standardized.dropna(
        subset=["date", "close"]
    )

    return standardized


def extract_index_data(
    symbol: str,
    asset_name: str,
    start_date: str,
    end_date: str,
) -> pd.DataFrame:
    """Extract one index or index-like instrument through OpenBB."""

    response = obb.index.price.historical(
        symbol=symbol,
        start_date=start_date,
        end_date=end_date,
        provider="yfinance",
    )

    return standardize_market_data(
        df=response.to_df(),
        symbol=symbol,
        asset_name=asset_name,
        asset_type="index",
        provider=response.provider,
    )


def extract_futures_data(
    symbol: str,
    asset_name: str,
    start_date: str,
    end_date: str,
) -> pd.DataFrame:
    """Extract one futures contract through OpenBB."""

    response = obb.derivatives.futures.historical(
        symbol=symbol,
        start_date=start_date,
        end_date=end_date,
        provider="yfinance",
    )

    return standardize_market_data(
        df=response.to_df(),
        symbol=symbol,
        asset_name=asset_name,
        asset_type="futures",
        provider=response.provider,
    )


def extract_all_market_data(
    start_date: str = "2025-01-01",
    end_date: str | None = None,
    request_delay: float = 1.0,
) -> pd.DataFrame:
    """
    Extract all configured market instruments.

    Errors affecting one symbol are logged without stopping the entire batch.
    """

    if end_date is None:
        end_date = date.today().isoformat()

    collected_frames: list[pd.DataFrame] = []
    failed_symbols: list[str] = []

    print("=" * 70)
    print("OPENBB MARKET DATA EXTRACTION")
    print("=" * 70)
    print(f"Start date: {start_date}")
    print(f"End date:   {end_date}")

    for symbol, asset_name in INDEX_SYMBOLS.items():
        print(f"\nExtracting index: {symbol} - {asset_name}")

        try:
            df = extract_index_data(
                symbol=symbol,
                asset_name=asset_name,
                start_date=start_date,
                end_date=end_date,
            )

            collected_frames.append(df)
            print(f"Rows extracted: {len(df):,}")

        except Exception as exc:
            failed_symbols.append(symbol)
            print(f"Extraction failed: {exc}")

        time.sleep(request_delay)

    for symbol, asset_name in FUTURES_SYMBOLS.items():
        print(f"\nExtracting futures: {symbol} - {asset_name}")

        try:
            df = extract_futures_data(
                symbol=symbol,
                asset_name=asset_name,
                start_date=start_date,
                end_date=end_date,
            )

            collected_frames.append(df)
            print(f"Rows extracted: {len(df):,}")

        except Exception as exc:
            failed_symbols.append(symbol)
            print(f"Extraction failed: {exc}")

        time.sleep(request_delay)

    valid_frames = [
        frame for frame in collected_frames
        if not frame.empty
    ]

    if not valid_frames:
        raise RuntimeError(
            "OpenBB did not return data for any configured symbol."
        )

    combined_df = pd.concat(
        valid_frames,
        ignore_index=True,
    )

    combined_df = combined_df.drop_duplicates(
        subset=["date", "symbol"],
        keep="last",
    )

    combined_df = combined_df.sort_values(
        by=["symbol", "date"],
    ).reset_index(drop=True)

    print("\n" + "=" * 70)
    print("EXTRACTION SUMMARY")
    print("=" * 70)
    print(f"Total rows: {len(combined_df):,}")
    print(f"Successful symbols: {combined_df['symbol'].nunique()}")

    if failed_symbols:
        print(f"Failed symbols: {', '.join(failed_symbols)}")
    else:
        print("Failed symbols: None")

    return combined_df


def save_market_data(df: pd.DataFrame) -> Path:
    """Save extracted data into the raw-data directory."""

    RAW_DATA_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    df.to_csv(
        OUTPUT_FILE,
        index=False,
    )

    print(f"\nSaved to: {OUTPUT_FILE}")

    return OUTPUT_FILE


def main() -> None:
    """Run the complete OpenBB market extraction process."""

    market_df = extract_all_market_data(
        start_date="2025-01-01",
    )

    save_market_data(market_df)

    print("\nSample:")
    print(market_df.tail(10))

    print("\nRows by symbol:")
    print(
        market_df.groupby(
            ["symbol", "asset_name", "asset_type"]
        ).size()
    )


if __name__ == "__main__":
    main()