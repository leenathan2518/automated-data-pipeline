"""
load_quality_to_postgres.py

This module loads data quality check results
into PostgreSQL.

Current function:
- Read data_quality_results.csv
- Connect to PostgreSQL
- Load data into data_quality_results table
"""

import os
import sys
import pandas as pd


# Add project root directory to Python path
PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "../..")
)
sys.path.append(PROJECT_ROOT)


# Import database connection function
from src.load.db_connection import get_engine


def load_quality_results():
    """
    Load data quality results into PostgreSQL.
    """

    # Define CSV path
    csv_path = os.path.join(
        "data",
        "processed",
        "data_quality_results.csv"
    )

    # Check file existence
    if not os.path.exists(csv_path):
        raise FileNotFoundError(
            f"Quality results file not found: {csv_path}"
        )

    # Read CSV file
    df = pd.read_csv(csv_path)

    print(f"Loaded quality results shape: {df.shape}")

    # Convert check_time column
    df["check_time"] = pd.to_datetime(df["check_time"])

    # Create database engine
    engine = get_engine()

    # Load data into PostgreSQL
    df.to_sql(
        name="data_quality_results",
        con=engine,
        if_exists="append",
        index=False
    )

    print(
        f"Successfully loaded {len(df)} rows "
        f"into data_quality_results table."
    )


if __name__ == "__main__":
    load_quality_results()

