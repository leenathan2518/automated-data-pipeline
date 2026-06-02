"""
china_stock_extract.py

Extract A-share and Hong Kong stock daily price data
using AKShare.

This module is a feasibility test for the future
China & Hong Kong market data pipeline.

Author
------
Vinci Lee
"""

from pathlib import Path
from datetime import datetime

import pandas as pd
import akshare as ak

from src.config.stock_universe import A_SHARES, HK_SHARES


# --------------------------------------------------
# Output Directory
# --------------------------------------------------

RAW_DATA_DIR = Path("data/raw")
RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)


def extract_a_share_daily(symbol: str, name: str):
    """
    Extract daily historical price data for one A-share stock.

    Parameters
    ----------
    symbol : str
        A-share stock code, for example '600519'.

    name : str
        Stock name.

    Returns
    -------
    pandas.DataFrame
        Raw A-share daily price data.
    """

    print(f"Extracting A-share: {symbol} - {name}")

    df = ak.stock_zh_a_hist(
        symbol=symbol,
        period="daily",
        start_date="20240101",
        end_date=datetime.today().strftime("%Y%m%d"),
        adjust=""
    )

    df["symbol"] = symbol
    df["name"] = name
    df["market"] = "A-share"
    df["source"] = "AKShare"

    return df


def extract_hk_share_daily(symbol: str, name: str):
    """
    Extract daily historical price data for one Hong Kong stock.

    Parameters
    ----------
    symbol : str
        Hong Kong stock code, for example '00700'.

    name : str
        Stock name.

    Returns
    -------
    pandas.DataFrame
        Raw Hong Kong daily price data.
    """

    print(f"Extracting HK share: {symbol} - {name}")

    df = ak.stock_hk_hist(
        symbol=symbol,
        period="daily",
        start_date="20240101",
        end_date=datetime.today().strftime("%Y%m%d"),
        adjust=""
    )

    df["symbol"] = symbol
    df["name"] = name
    df["market"] = "HK-share"
    df["source"] = "AKShare"

    return df


def run_china_stock_extract_pipeline():
    """
    Run China and Hong Kong stock extraction pipeline.

    This function extracts daily price data for the test
    stock universe and saves the combined raw dataset as CSV.

    Returns
    -------
    None
    """

    all_data = []

    # Extract A-share data
    for symbol, name in A_SHARES.items():

        try:
            df = extract_a_share_daily(
                symbol=symbol,
                name=name
            )

            all_data.append(df)

        except Exception as e:
            print(f"Failed to extract A-share {symbol}: {e}")

    # Extract Hong Kong share data
    for symbol, name in HK_SHARES.items():

        try:
            df = extract_hk_share_daily(
                symbol=symbol,
                name=name
            )

            all_data.append(df)

        except Exception as e:
            print(f"Failed to extract HK share {symbol}: {e}")

    if not all_data:
        raise ValueError("No stock data was extracted.")

    combined_df = pd.concat(
        all_data,
        ignore_index=True
    )

    output_path = RAW_DATA_DIR / "china_hk_stock_daily_raw.csv"

    combined_df.to_csv(
        output_path,
        index=False,
        encoding="utf-8-sig"
    )

    print(f"Raw stock data saved to: {output_path}")
    print(f"Total rows: {len(combined_df)}")


if __name__ == "__main__":
    run_china_stock_extract_pipeline()

