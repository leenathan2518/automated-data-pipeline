"""
market_transform.py

This module transforms raw Yahoo Finance market CSV files
into one standardized market prices dataset.

Current function:
- Read raw market CSV files from data/raw/
- Add metadata such as asset name, asset type, and source
- Standardize column names and column order
- Save processed market data into data/processed/
"""

import os
import sys
import pandas as pd


# Add project root directory to Python path.
# This allows us to import metadata when running this file directly.
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
sys.path.append(PROJECT_ROOT)


# Import market ticker metadata
from src.utils.market_metadata import MARKET_TICKERS


def clean_ticker_for_filename(ticker: str) -> str:
    """
    Convert ticker symbols into safe file names.

    This must match the same logic used in market_extract.py.

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


def transform_market_file(ticker: str) -> pd.DataFrame:
    """
    Transform one raw market CSV file into standardized format.

    Parameters:
        ticker (str):
            Yahoo Finance ticker, such as 'SPY', '^TNX', or 'ES=F'.

    Returns:
        pd.DataFrame:
            Standardized market price dataframe.
    """

    # Convert ticker into the filename format used by market_extract.py
    safe_ticker = clean_ticker_for_filename(ticker)

    # Define raw file path
    raw_path = os.path.join("data", "raw", f"market_{safe_ticker}.csv")

    # Check whether the raw file exists
    if not os.path.exists(raw_path):
        raise FileNotFoundError(f"Raw file not found: {raw_path}")

    # Read raw market CSV file
    df = pd.read_csv(raw_path)

    # Get metadata for this ticker
    metadata = MARKET_TICKERS[ticker]

    # Convert date column to datetime format
    df["date"] = pd.to_datetime(df["date"])

    # Add metadata columns
    df["asset_name"] = metadata["asset_name"]
    df["asset_type"] = metadata["asset_type"]
    df["source"] = metadata["source"]

    # Make sure all expected price columns exist.
    # If a column is missing, create it with missing values.
    expected_price_columns = [
        "open",
        "high",
        "low",
        "close",
        "adj_close",
        "volume",
    ]

    for col in expected_price_columns:
        if col not in df.columns:
            df[col] = pd.NA

    # Keep standardized columns only
    df = df[
        [
            "date",
            "ticker",
            "asset_name",
            "asset_type",
            "open",
            "high",
            "low",
            "close",
            "adj_close",
            "volume",
            "source",
        ]
    ]

    return df


def run_market_transform_pipeline() -> pd.DataFrame:
    """
    Run transformation for all market tickers.

    Returns:
        pd.DataFrame:
            Combined standardized market prices dataset.
    """

    transformed_dfs = []

    # Loop through all tickers in metadata
    for ticker in MARKET_TICKERS.keys():

        print(f"Transforming {ticker}...")

        try:
            # Transform one raw market file
            df = transform_market_file(ticker)

            # Store transformed dataframe in list
            transformed_dfs.append(df)

        except Exception as e:
            # Continue even if one ticker fails
            print(f"Failed to transform {ticker}: {e}")

    # Stop clearly if no files were transformed
    if not transformed_dfs:
        raise ValueError("No market files were transformed. Please check data/raw folder.")

    # Combine all transformed market dataframes
    combined_df = pd.concat(transformed_dfs, ignore_index=True)

    # Sort data for easier checking and later database loading
    combined_df = combined_df.sort_values(by=["ticker", "date"])

    # Create processed data folder if it does not exist
    output_dir = os.path.join("data", "processed")
    os.makedirs(output_dir, exist_ok=True)

    # Save combined processed dataset
    output_path = os.path.join(output_dir, "market_prices_processed.csv")
    combined_df.to_csv(output_path, index=False)

    print(f"\nSaved processed market data to {output_path}")

    return combined_df


if __name__ == "__main__":
    # Run market transformation when this file is executed directly
    market_df = run_market_transform_pipeline()

    # Print first few rows for checking
    print(market_df.head())

    # Print shape for checking total rows and columns
    print(f"\nProcessed market data shape: {market_df.shape}")

