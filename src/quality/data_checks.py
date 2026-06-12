"""
This module runs data quality checks for processed datasets.

Current checks:
- Missing values check
- Duplicate key check
- Date freshness check
- Negative price check
- OHLC consistency check
- Return-value sanity check
- Expected OpenBB symbol coverage check

Outputs:
- data/processed/data_quality_results.csv
"""

from __future__ import annotations

import os
from datetime import datetime
from typing import Iterable

import pandas as pd


def load_processed_data(file_path: str) -> pd.DataFrame:
    """
    Load a processed CSV file.

    Parameters
    ----------
    file_path : str
        Path to the processed CSV file.

    Returns
    -------
    pd.DataFrame
        Loaded dataframe.
    """

    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    return pd.read_csv(file_path)


def build_result(
    table_name: str,
    check_name: str,
    check_result: str,
    failed_rows: int,
    details: str,
) -> dict:
    """Create one standardised data-quality result record."""

    return {
        "table_name": table_name,
        "check_name": check_name,
        "check_result": check_result,
        "failed_rows": int(failed_rows),
        "details": details,
        "check_time": datetime.now(),
    }


def check_missing_values(
    df: pd.DataFrame,
    table_name: str,
    required_columns: Iterable[str] | None = None,
) -> dict:
    """
    Check missing values.

    When required_columns is supplied, only business-critical columns are
    checked. This avoids treating expected null values, such as the first
    return observation for each symbol, as data-quality failures.
    """

    columns = list(required_columns) if required_columns else list(df.columns)

    missing_columns = [
        column for column in columns
        if column not in df.columns
    ]

    if missing_columns:
        return build_result(
            table_name=table_name,
            check_name="missing_values_check",
            check_result="FAIL",
            failed_rows=len(missing_columns),
            details=f"Required columns not found: {missing_columns}",
        )

    missing_count = int(df[columns].isna().sum().sum())

    return build_result(
        table_name=table_name,
        check_name="missing_values_check",
        check_result="PASS" if missing_count == 0 else "WARNING",
        failed_rows=missing_count,
        details=(
            f"Missing values in checked columns {columns}: "
            f"{missing_count}"
        ),
    )


def check_duplicate_rows(
    df: pd.DataFrame,
    table_name: str,
    subset_columns: list[str],
) -> dict:
    """Check duplicate rows based on selected natural-key columns."""

    missing_columns = [
        column for column in subset_columns
        if column not in df.columns
    ]

    if missing_columns:
        return build_result(
            table_name=table_name,
            check_name="duplicate_rows_check",
            check_result="FAIL",
            failed_rows=len(missing_columns),
            details=f"Key columns not found: {missing_columns}",
        )

    duplicate_count = int(
        df.duplicated(
            subset=subset_columns,
            keep=False,
        ).sum()
    )

    return build_result(
        table_name=table_name,
        check_name="duplicate_rows_check",
        check_result="PASS" if duplicate_count == 0 else "FAIL",
        failed_rows=duplicate_count,
        details=(
            f"Duplicate rows based on {subset_columns}: "
            f"{duplicate_count}"
        ),
    )


def check_date_freshness(
    df: pd.DataFrame,
    table_name: str,
    date_column: str = "date",
    warning_threshold_days: int | None = None,
) -> dict:
    """
    Check the age of the latest date in a dataset.

    A future date is always treated as a failure. A configurable threshold
    can be used to issue a warning when the data are older than expected.
    """

    if date_column not in df.columns:
        return build_result(
            table_name=table_name,
            check_name="date_freshness_check",
            check_result="FAIL",
            failed_rows=1,
            details=f"Date column not found: {date_column}",
        )

    parsed_dates = pd.to_datetime(
        df[date_column],
        errors="coerce",
    )

    if parsed_dates.notna().sum() == 0:
        return build_result(
            table_name=table_name,
            check_name="date_freshness_check",
            check_result="FAIL",
            failed_rows=len(df),
            details="No valid dates were found.",
        )

    latest_date = parsed_dates.max().normalize()
    today = pd.Timestamp.today().normalize()
    days_old = int((today - latest_date).days)

    if days_old < 0:
        status = "FAIL"
        failed_rows = 1
    elif (
        warning_threshold_days is not None
        and days_old > warning_threshold_days
    ):
        status = "WARNING"
        failed_rows = 1
    else:
        status = "PASS"
        failed_rows = 0

    return build_result(
        table_name=table_name,
        check_name="date_freshness_check",
        check_result=status,
        failed_rows=failed_rows,
        details=(
            f"Latest date: {latest_date.date()}, "
            f"Days old: {days_old}, "
            f"Warning threshold: {warning_threshold_days}"
        ),
    )


def check_negative_values(
    df: pd.DataFrame,
    table_name: str,
    columns: list[str],
) -> dict:
    """Check whether selected numeric columns contain negative values."""

    available_columns = [
        column for column in columns
        if column in df.columns
    ]

    negative_count = 0

    for column in available_columns:
        values = pd.to_numeric(
            df[column],
            errors="coerce",
        )
        negative_count += int((values < 0).sum())

    missing_columns = [
        column for column in columns
        if column not in df.columns
    ]

    status = "PASS" if negative_count == 0 else "FAIL"

    return build_result(
        table_name=table_name,
        check_name="negative_values_check",
        check_result=status,
        failed_rows=negative_count,
        details=(
            f"Negative values in {available_columns}: {negative_count}. "
            f"Missing optional columns: {missing_columns}"
        ),
    )


def check_ohlc_consistency(
    df: pd.DataFrame,
    table_name: str,
) -> dict:
    """
    Check that high/low values are consistent with open and close values.

    Valid rows should satisfy:
    - high >= low
    - high >= open and close
    - low <= open and close
    """

    required_columns = ["open", "high", "low", "close"]

    missing_columns = [
        column for column in required_columns
        if column not in df.columns
    ]

    if missing_columns:
        return build_result(
            table_name=table_name,
            check_name="ohlc_consistency_check",
            check_result="FAIL",
            failed_rows=len(missing_columns),
            details=f"OHLC columns not found: {missing_columns}",
        )

    numeric = df[required_columns].apply(
        pd.to_numeric,
        errors="coerce",
    )

    complete_rows = numeric.notna().all(axis=1)

    invalid_mask = complete_rows & (
        (numeric["high"] < numeric["low"])
        | (numeric["high"] < numeric["open"])
        | (numeric["high"] < numeric["close"])
        | (numeric["low"] > numeric["open"])
        | (numeric["low"] > numeric["close"])
    )

    invalid_count = int(invalid_mask.sum())

    return build_result(
        table_name=table_name,
        check_name="ohlc_consistency_check",
        check_result="PASS" if invalid_count == 0 else "WARNING",
        failed_rows=invalid_count,
        details=(
            f"Rows with inconsistent OHLC values: {invalid_count}. "
            "These may reflect incomplete current-day data, futures contract "
            "roll adjustments, settlement-price differences, or provider revisions."
        ),
    )


def check_return_sanity(
    df: pd.DataFrame,
    table_name: str,
    columns: list[str],
    absolute_limit: float = 1.0,
) -> dict:
    """
    Flag extreme return values.

    Values with an absolute magnitude above 1.0 represent movements greater
    than 100 percent and are treated as warnings for manual investigation.
    """

    available_columns = [
        column for column in columns
        if column in df.columns
    ]

    if not available_columns:
        return build_result(
            table_name=table_name,
            check_name="return_sanity_check",
            check_result="FAIL",
            failed_rows=len(columns),
            details=f"Return columns not found: {columns}",
        )

    extreme_count = 0

    for column in available_columns:
        values = pd.to_numeric(
            df[column],
            errors="coerce",
        )
        extreme_count += int(
            (values.abs() > absolute_limit).sum()
        )

    return build_result(
        table_name=table_name,
        check_name="return_sanity_check",
        check_result="PASS" if extreme_count == 0 else "WARNING",
        failed_rows=extreme_count,
        details=(
            f"Return values with absolute magnitude above "
            f"{absolute_limit}: {extreme_count}"
        ),
    )


def check_expected_symbols(
    df: pd.DataFrame,
    table_name: str,
    expected_symbols: set[str],
) -> dict:
    """Check that all configured OpenBB market symbols are present."""

    if "symbol" not in df.columns:
        return build_result(
            table_name=table_name,
            check_name="expected_symbols_check",
            check_result="FAIL",
            failed_rows=len(expected_symbols),
            details="Symbol column not found.",
        )

    actual_symbols = set(
        df["symbol"]
        .dropna()
        .astype(str)
        .str.strip()
        .unique()
    )

    missing_symbols = sorted(
        expected_symbols - actual_symbols
    )

    unexpected_symbols = sorted(
        actual_symbols - expected_symbols
    )

    return build_result(
        table_name=table_name,
        check_name="expected_symbols_check",
        check_result="PASS" if not missing_symbols else "FAIL",
        failed_rows=len(missing_symbols),
        details=(
            f"Missing symbols: {missing_symbols or 'None'}. "
            f"Unexpected symbols: {unexpected_symbols or 'None'}."
        ),
    )


def run_data_quality_checks() -> pd.DataFrame:
    """
    Run data quality checks for macro and OpenBB market datasets.

    Returns
    -------
    pd.DataFrame
        Data quality check results.
    """

    results = []

    macro_path = os.path.join(
        "data",
        "processed",
        "macro_indicators_processed.csv",
    )

    openbb_market_path = os.path.join(
        "data",
        "processed",
        "openbb_market_data_clean.csv",
    )

    macro_df = load_processed_data(macro_path)
    market_df = load_processed_data(openbb_market_path)

    # --------------------------------------------------
    # Macro data checks
    # --------------------------------------------------

    results.append(
        check_missing_values(
            macro_df,
            "macro_indicators",
            required_columns=[
                "date",
                "country",
                "indicator_code",
                "value",
            ],
        )
    )

    results.append(
        check_duplicate_rows(
            macro_df,
            "macro_indicators",
            subset_columns=[
                "date",
                "country",
                "indicator_code",
            ],
        )
    )

    results.append(
        check_date_freshness(
            macro_df,
            "macro_indicators",
            warning_threshold_days=120,
        )
    )

    # --------------------------------------------------
    # OpenBB market data checks
    # --------------------------------------------------

    results.append(
        check_missing_values(
            market_df,
            "openbb_market_data",
            required_columns=[
                "date",
                "symbol",
                "asset_name",
                "asset_type",
                "close",
                "provider",
                "extracted_at",
                "transformed_at",
            ],
        )
    )

    results.append(
        check_duplicate_rows(
            market_df,
            "openbb_market_data",
            subset_columns=["date", "symbol"],
        )
    )

    results.append(
        check_date_freshness(
            market_df,
            "openbb_market_data",
            warning_threshold_days=7,
        )
    )

    results.append(
        check_negative_values(
            market_df,
            "openbb_market_data",
            columns=[
                "open",
                "high",
                "low",
                "close",
                "volume",
            ],
        )
    )

    results.append(
        check_ohlc_consistency(
            market_df,
            "openbb_market_data",
        )
    )

    results.append(
        check_return_sanity(
            market_df,
            "openbb_market_data",
            columns=[
                "daily_return",
                "log_return",
                "intraday_return",
                "daily_range_pct",
            ],
            absolute_limit=1.0,
        )
    )

    results.append(
        check_expected_symbols(
            market_df,
            "openbb_market_data",
            expected_symbols={
                "^GSPC",
                "^DJI",
                "^IXIC",
                "^TNX",
                "^TYX",
                "DX-Y.NYB",
                "ES=F",
                "YM=F",
            },
        )
    )

    # Save inconsistent OHLC rows for manual investigation.
    ohlc_columns = ["open", "high", "low", "close"]

    ohlc_numeric = market_df[ohlc_columns].apply(
        pd.to_numeric,
        errors="coerce",
    )

    ohlc_complete = ohlc_numeric.notna().all(axis=1)

    ohlc_invalid_mask = ohlc_complete & (
        (ohlc_numeric["high"] < ohlc_numeric["low"])
        | (ohlc_numeric["high"] < ohlc_numeric["open"])
        | (ohlc_numeric["high"] < ohlc_numeric["close"])
        | (ohlc_numeric["low"] > ohlc_numeric["open"])
        | (ohlc_numeric["low"] > ohlc_numeric["close"])
    )

    investigation_columns = [
        column
        for column in [
            "date",
            "symbol",
            "asset_name",
            "asset_type",
            "open",
            "high",
            "low",
            "close",
            "provider",
        ]
        if column in market_df.columns
    ]

    ohlc_invalid_rows = market_df.loc[
        ohlc_invalid_mask,
        investigation_columns,
    ]

    investigation_path = os.path.join(
        "data",
        "processed",
        "ohlc_inconsistency_investigation.csv",
    )

    if not ohlc_invalid_rows.empty:
        ohlc_invalid_rows.to_csv(
            investigation_path,
            index=False,
        )

        print(
            "Saved OHLC inconsistency investigation file to "
            f"{investigation_path}"
        )
    elif os.path.exists(investigation_path):
        # Remove a stale investigation file when the latest run has no issues.
        os.remove(investigation_path)

    results_df = pd.DataFrame(results)

    output_path = os.path.join(
        "data",
        "processed",
        "data_quality_results.csv",
    )

    results_df.to_csv(
        output_path,
        index=False,
    )

    print("=" * 70)
    print("DATA QUALITY SUMMARY")
    print("=" * 70)
    print(
        results_df[
            [
                "table_name",
                "check_name",
                "check_result",
                "failed_rows",
            ]
        ].to_string(index=False)
    )
    print(f"\nSaved data quality results to {output_path}")

    return results_df


if __name__ == "__main__":
    quality_results = run_data_quality_checks()
    print("\nDetailed results:")
    print(quality_results.to_string(index=False))
