"""
fred_extract.py

This module extracts macroeconomic time series data from FRED.

Current function:
- Read FRED API key from .env
- Read indicator list from metadata
- Download selected FRED indicators
- Convert raw FRED series into pandas DataFrames
- Save raw data into data/raw/
"""

from fredapi import Fred
from dotenv import load_dotenv
import pandas as pd
import os
import time
import sys


# Add project root directory to Python path.
# This allows us to import modules from src/ when running this file directly.
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
sys.path.append(PROJECT_ROOT)


# Import FRED indicator metadata
from src.utils.fred_metadata import FRED_INDICATORS


# Load environment variables from .env file
load_dotenv()


# Read FRED API key from environment variable
FRED_API_KEY = os.getenv("FRED_API_KEY")


def extract_fred_series(series_id: str, start_date: str = "2010-01-01") -> pd.DataFrame:
    """
    Extract one time series from FRED.

    Parameters:
        series_id (str):
            FRED series ID, such as 'UNRATE', 'CPIAUCSL', or 'FEDFUNDS'.

        start_date (str):
            Start date for the data extraction.

    Returns:
        pd.DataFrame:
            A dataframe containing date, series_id, and value.
    """

    # Check whether the API key exists
    if FRED_API_KEY is None:
        raise ValueError("FRED_API_KEY is missing. Please add it to your .env file.")

    # Create FRED client
    fred = Fred(api_key=FRED_API_KEY)

    # Download data from FRED
    series = fred.get_series(series_id, observation_start=start_date)

    # Convert pandas Series into DataFrame
    df = series.reset_index()

    # Rename columns into a standard format
    df.columns = ["date", "value"]

    # Add series ID for tracking
    df["series_id"] = series_id

    # Reorder columns
    df = df[["date", "series_id", "value"]]

    return df


def save_raw_data(df: pd.DataFrame, series_id: str) -> None:
    """
    Save extracted raw FRED data into data/raw folder.

    Parameters:
        df (pd.DataFrame):
            Extracted FRED dataframe.

        series_id (str):
            FRED series ID used for naming the output file.
    """

    # Define output folder
    output_dir = "data/raw"

    # Create output folder if it does not exist
    os.makedirs(output_dir, exist_ok=True)

    # Define output file path
    output_path = os.path.join(output_dir, f"fred_{series_id}.csv")

    # Save dataframe as CSV
    df.to_csv(output_path, index=False)

    print(f"Saved raw data to {output_path}")


def run_fred_extract_pipeline(start_date: str = "2010-01-01", sleep_seconds: int = 10) -> None:
    """
    Run the FRED extract pipeline for all indicators in metadata.

    Parameters:
        start_date (str):
            Start date for all FRED series.

        sleep_seconds (int):
            Waiting time between API requests to reduce rate-limit risk.
    """

    # Loop through all indicator codes stored in metadata
    for series_id, metadata in FRED_INDICATORS.items():

        indicator_name = metadata["indicator_name"]

        print(f"\nDownloading {series_id}: {indicator_name}...")

        try:
            # Extract one FRED series
            df = extract_fred_series(series_id, start_date=start_date)

            # Print first few rows for quick checking
            print(df.head())

            # Save raw data to local folder
            save_raw_data(df, series_id)

            # Pause between requests to avoid API rate limit
            time.sleep(sleep_seconds)

        except Exception as e:
            # Continue the pipeline even if one indicator fails
            print(f"Failed to download {series_id}: {e}")

    print("\nFRED extract pipeline finished.")


if __name__ == "__main__":
    # Run the extract pipeline when this file is executed directly
    run_fred_extract_pipeline(start_date="2010-01-01", sleep_seconds=10)




