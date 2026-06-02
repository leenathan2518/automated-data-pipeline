"""
macro_transform.py

This module transforms raw FRED CSV files into a standardized macroeconomic dataset.

Current function:
- Read raw FRED CSV files from data/raw/
- Add metadata such as indicator name, country, frequency, and unit
- Standardize column names and order
- Save processed macro data into data/processed/
"""

import os
import sys
import pandas as pd


# Add project root directory to Python path.
# This allows us to import metadata when running this file directly.
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
sys.path.append(PROJECT_ROOT)


# Import FRED indicator metadata
from src.utils.fred_metadata import FRED_INDICATORS


def transform_fred_file(series_id: str) -> pd.DataFrame:
    """
    Transform one raw FRED CSV file into standardized format.

    Parameters:
        series_id (str):
            FRED series ID, such as 'UNRATE', 'CPIAUCSL', or 'FEDFUNDS'.

    Returns:
        pd.DataFrame:
            Standardized macroeconomic dataframe.
    """

    # Define raw file path
    raw_path = os.path.join("data", "raw", f"fred_{series_id}.csv")

    # Check whether the raw file exists
    if not os.path.exists(raw_path):
        raise FileNotFoundError(f"Raw file not found: {raw_path}")

    # Read raw CSV file
    df = pd.read_csv(raw_path)

    # Get metadata for this indicator
    metadata = FRED_INDICATORS[series_id]

    # Convert date column to datetime format
    df["date"] = pd.to_datetime(df["date"])

    # Add metadata columns
    df["indicator_code"] = series_id
    df["indicator_name"] = metadata["indicator_name"]
    df["country"] = metadata["country"]
    df["frequency"] = metadata["frequency"]
    df["unit"] = metadata["unit"]
    df["source"] = "FRED"

    # Keep standardized columns only
    df = df[
        [
            "date",
            "country",
            "indicator_code",
            "indicator_name",
            "value",
            "frequency",
            "unit",
            "source",
        ]
    ]

    return df


def run_macro_transform_pipeline() -> pd.DataFrame:
    """
    Run transformation for all FRED indicators.

    Returns:
        pd.DataFrame:
            Combined standardized macroeconomic dataset.
    """

    transformed_dfs = []

    # Loop through all indicators in metadata
    for series_id in FRED_INDICATORS.keys():

        print(f"Transforming {series_id}...")

        try:
            # Transform one raw FRED file
            df = transform_fred_file(series_id)

            # Store transformed dataframe in list
            transformed_dfs.append(df)

        except Exception as e:
            # Continue even if one file fails
            print(f"Failed to transform {series_id}: {e}")

    # Combine all transformed dataframes
    combined_df = pd.concat(transformed_dfs, ignore_index=True)

    # Create processed data folder if it does not exist
    output_dir = os.path.join("data", "processed")
    os.makedirs(output_dir, exist_ok=True)

    # Save combined processed dataset
    output_path = os.path.join(output_dir, "macro_indicators_processed.csv")
    combined_df.to_csv(output_path, index=False)

    print(f"\nSaved processed macro data to {output_path}")

    return combined_df


if __name__ == "__main__":
    # Run macro transformation when this file is executed directly
    macro_df = run_macro_transform_pipeline()

    # Print first few rows for checking
    print(macro_df.head())

    # Print shape for checking total rows and columns
    print(f"\nProcessed data shape: {macro_df.shape}")

