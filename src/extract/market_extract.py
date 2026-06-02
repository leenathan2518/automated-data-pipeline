"""
market_extract.py

This module extracts financial market data from Yahoo Finance.

Current function:
- Read ticker list from metadata
- Download historical market data using yfinance
- Standardize raw columns
- Save each ticker's raw data into data/raw/
"""

import os
import sys
import time
import pandas as pd
import yfinance as yf


# Add project root directory to Python path.
# This allows us to import modules from src/ when running this file directly.
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
sys.path.append(PROJECT_ROOT)


# Import market ticker metadata
from src.utils.market_metadata import MARKET_TICKERS


def clean_ticker_for_filename(ticker: str) -> str:
    """
    Convert ticker symbols into safe file names.

    Examples:
        '^TNX' becomes 'TNX'
        'CL=F' becomes 'CL_F'
        'DX-Y.NYB' becomes 'DX_Y_NYB'
    """

    return (
        ticker.replace("^", "")
        .replace("=", "_")
        .replace("-", "_")
        .replace(".", "_")
    )


def extract_market_data(ticker: str, start_date: str = "2010-01-01") -> pd.DataFrame:
    """
    Extract historical market data for one ticker from Yahoo Finance.

    Parameters:
        ticker (str):
            Yahoo Finance ticker, such as 'SPY', '^TNX', or 'DX-Y.NYB'.

        start_date (str):
            Start date for historical data extraction.

    Returns:
        pd.DataFrame:
            Raw market dataframe with date, ticker, OHLC prices, and volume.
    """

    # Download historical price data from Yahoo Finance
    df = yf.download(
        ticker,
        start=start_date,
        progress=False,
        auto_adjust=False
    )

    # Check whether Yahoo Finance returned data
    if df.empty:
        raise ValueError(f"No data returned for ticker: {ticker}")

    # Convert index into a normal date column
    df = df.reset_index()

    # yfinance may return MultiIndex columns in newer versions.
    # Example: ('Close', 'SPY') instead of 'Close'.
    # We only keep the first level such as 'Close'.
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    # Standardize column names
    df.columns = [str(col).lower().replace(" ", "_") for col in df.columns]

    # Add ticker column for tracking
    df["ticker"] = ticker

    # Keep useful raw columns only
    expected_columns = [
        "date",
        "ticker",
        "open",
        "high",
        "low",
        "close",
        "adj_close",
        "volume",
    ]

    # Some tickers may not have all columns, so keep only existing columns
    existing_columns = [col for col in expected_columns if col in df.columns]
    df = df[existing_columns]

    return df


def save_raw_market_data(df: pd.DataFrame, ticker: str) -> None:
    """
    Save raw market data into data/raw folder.

    Parameters:
        df (pd.DataFrame):
            Extracted market dataframe.

        ticker (str):
            Yahoo Finance ticker used for naming the output file.
    """

    # Define output folder
    output_dir = os.path.join("data", "raw")

    # Create output folder if it does not exist
    os.makedirs(output_dir, exist_ok=True)

    # Clean ticker name for file path
    safe_ticker = clean_ticker_for_filename(ticker)

    # Define output file path
    output_path = os.path.join(output_dir, f"market_{safe_ticker}.csv")

    # Save dataframe as CSV
    df.to_csv(output_path, index=False)

    print(f"Saved raw market data to {output_path}")


def run_market_extract_pipeline(start_date: str = "2010-01-01", sleep_seconds: int = 5) -> None:
    """
    Run market data extraction for all tickers in metadata.

    Parameters:
        start_date (str):
            Start date for all market data.

        sleep_seconds (int):
            Waiting time between requests to reduce rate-limit risk.
    """

    # Loop through all tickers stored in metadata
    for ticker, metadata in MARKET_TICKERS.items():

        asset_name = metadata["asset_name"]

        print(f"\nDownloading {ticker}: {asset_name}...")

        try:
            # Extract one ticker
            df = extract_market_data(ticker, start_date=start_date)

            # Print first few rows for quick checking
            print(df.head())

            # Save raw data to local folder
            save_raw_market_data(df, ticker)

            # Pause between requests to avoid request limits
            time.sleep(sleep_seconds)

        except Exception as e:
            # Continue the pipeline even if one ticker fails
            print(f"Failed to download {ticker}: {e}")

    print("\nMarket extract pipeline finished.")


if __name__ == "__main__":
    # Run the market extract pipeline when this file is executed directly
    run_market_extract_pipeline(start_date="2010-01-01", sleep_seconds=5)

