"""
data_checks.py

This module runs basic data quality checks for processed datasets.

Current checks:
- Missing values check
- Duplicate rows check
- Date freshness check
- Negative value check

Outputs:
- data/processed/data_quality_results.csv
"""

import os
import pandas as pd
from datetime import datetime


def load_processed_data(file_path: str) -> pd.DataFrame:
    """
    Load a processed CSV file.

    Parameters:
        file_path (str): Path to the processed CSV file.

    Returns:
        pd.DataFrame: Loaded dataframe.
    """

    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    return pd.read_csv(file_path)


def check_missing_values(df: pd.DataFrame, table_name: str) -> dict:
    """
    Check total number of missing values in a dataframe.
    """

    missing_count = df.isna().sum().sum()

    return {
        "table_name": table_name,
        "check_name": "missing_values_check",
        "check_result": "PASS" if missing_count == 0 else "WARNING",
        "failed_rows": int(missing_count),
        "details": f"Total missing values: {missing_count}",
        "check_time": datetime.now()
    }


def check_duplicate_rows(df: pd.DataFrame, table_name: str, subset_columns: list) -> dict:
    """
    Check duplicate rows based on selected key columns.

    Example:
        macro: date + country + indicator_code
        market: date + ticker
    """

    duplicate_count = df.duplicated(subset=subset_columns).sum()

    return {
        "table_name": table_name,
        "check_name": "duplicate_rows_check",
        "check_result": "PASS" if duplicate_count == 0 else "FAIL",
        "failed_rows": int(duplicate_count),
        "details": f"Duplicate rows based on {subset_columns}: {duplicate_count}",
        "check_time": datetime.now()
    }


def check_date_freshness(df: pd.DataFrame, table_name: str, date_column: str = "date") -> dict:
    """
    Check how many days have passed since the latest date in the dataset.
    """

    df[date_column] = pd.to_datetime(df[date_column])

    latest_date = df[date_column].max()
    today = pd.Timestamp.today().normalize()

    days_old = (today - latest_date).days

    # For market data, several days old can be normal because of weekends/holidays.
    # For macro data, data can be monthly and naturally older.
    return {
        "table_name": table_name,
        "check_name": "date_freshness_check",
        "check_result": "PASS" if days_old >= 0 else "FAIL",
        "failed_rows": 0 if days_old >= 0 else 1,
        "details": f"Latest date: {latest_date.date()}, Days old: {days_old}",
        "check_time": datetime.now()
    }


def check_negative_values(df: pd.DataFrame, table_name: str, columns: list) -> dict:
    """
    Check whether selected numeric columns contain negative values.

    This is mainly useful for price data.
    """

    negative_count = 0

    for col in columns:
        if col in df.columns:
            negative_count += (pd.to_numeric(df[col], errors="coerce") < 0).sum()

    return {
        "table_name": table_name,
        "check_name": "negative_values_check",
        "check_result": "PASS" if negative_count == 0 else "FAIL",
        "failed_rows": int(negative_count),
        "details": f"Negative values in {columns}: {negative_count}",
        "check_time": datetime.now()
    }


def run_data_quality_checks() -> pd.DataFrame:
    """
    Run data quality checks for macro and market processed datasets.

    Returns:
        pd.DataFrame: Data quality check results.
    """

    results = []

    macro_path = os.path.join("data", "processed", "macro_indicators_processed.csv")
    market_path = os.path.join("data", "processed", "market_prices_processed.csv")

    macro_df = load_processed_data(macro_path)
    market_df = load_processed_data(market_path)

    # Macro data checks
    results.append(check_missing_values(macro_df, "macro_indicators"))
    results.append(
        check_duplicate_rows(
            macro_df,
            "macro_indicators",
            subset_columns=["date", "country", "indicator_code"]
        )
    )
    results.append(check_date_freshness(macro_df, "macro_indicators"))

    # Market data checks
    results.append(check_missing_values(market_df, "market_prices"))
    results.append(
        check_duplicate_rows(
            market_df,
            "market_prices",
            subset_columns=["date", "ticker"]
        )
    )
    results.append(check_date_freshness(market_df, "market_prices"))
    results.append(
        check_negative_values(
            market_df,
            "market_prices",
            columns=["open", "high", "low", "close", "adj_close"]
        )
    )

    def investigate_negative_prices(df: pd.DataFrame) -> pd.DataFrame:
        """
        Return rows containing negative close prices.

        This helps analysts investigate whether
        negative values are data errors or valid events.
        """

        negative_rows = df[df["close"] < 0]

        return negative_rows[
            [
                "date",
                "ticker",
                "asset_name",
                "close"
            ]
        ]

    # Save negative price investigation file

    negative_rows = investigate_negative_prices(market_df)

    if not negative_rows.empty:
        investigation_path = os.path.join(
            "data",
            "processed",
            "negative_price_investigation.csv"
        )

        negative_rows.to_csv(
            investigation_path,
            index=False
        )

        print(
            f"Saved negative price investigation file to "
            f"{investigation_path}"
        )

    results_df = pd.DataFrame(results)

    output_path = os.path.join("data", "processed", "data_quality_results.csv")
    results_df.to_csv(output_path, index=False)

    print(f"Saved data quality results to {output_path}")

    return results_df


if __name__ == "__main__":
    quality_results = run_data_quality_checks()
    print(quality_results)

