"""
sina_stock_extract.py

Extract real-time A-share and Hong Kong stock quote data
from Sina Finance.

This module is part of the stock market extension for the
Automated Financial Data Pipeline.

Main functions:
- Convert internal stock codes into Sina Finance symbols
- Request real-time quote data from Sina Finance
- Parse A-share and Hong Kong quote formats separately
- Extract A-share five-level order book data
- Calculate order book imbalance indicators
- Save standardized quote data as CSV

Author
------
Vinci Lee
"""

import time
import random
from pathlib import Path
from datetime import datetime

import requests
import pandas as pd

from src.config.stock_universe import A_SHARES, HK_SHARES


# --------------------------------------------------
# Output Directory
# --------------------------------------------------

RAW_DATA_DIR = Path("data/raw")
RAW_DATA_DIR.mkdir(
    parents=True,
    exist_ok=True
)


# --------------------------------------------------
# Sina Finance Request Settings
# --------------------------------------------------

SINA_BASE_URL = "https://hq.sinajs.cn/list="

HEADERS = {
    "Referer": "https://finance.sina.com.cn",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0 Safari/537.36"
    )
}


def safe_float(value):
    """
    Convert a value to float safely.

    Parameters
    ----------
    value : str
        Raw string value.

    Returns
    -------
    float or None
        Converted float value, or None if conversion fails.
    """

    try:
        return float(value)

    except (ValueError, TypeError):
        return None


def safe_int(value):
    """
    Convert a value to integer safely.

    Parameters
    ----------
    value : str
        Raw string value.

    Returns
    -------
    int or None
        Converted integer value, or None if conversion fails.
    """

    try:
        return int(float(value))

    except (ValueError, TypeError):
        return None


def convert_a_share_to_sina_symbol(symbol: str) -> str:
    """
    Convert an A-share stock code to a Sina Finance symbol.

    Shanghai-listed stocks usually start with:
    - 6
    - 9

    Shenzhen-listed stocks usually start with:
    - 0
    - 2
    - 3

    Parameters
    ----------
    symbol : str
        A-share stock code, for example '600519' or '000001'.

    Returns
    -------
    str
        Sina Finance symbol, for example 'sh600519' or 'sz000001'.
    """

    if symbol.startswith("6") or symbol.startswith("9"):
        return f"sh{symbol}"

    return f"sz{symbol}"


def convert_hk_share_to_sina_symbol(symbol: str) -> str:
    """
    Convert a Hong Kong stock code to a Sina Finance symbol.

    Parameters
    ----------
    symbol : str
        Hong Kong stock code, for example '00700'.

    Returns
    -------
    str
        Sina Finance Hong Kong symbol, for example 'hk00700'.
    """

    return f"hk{symbol}"


def request_sina_quote(sina_symbol: str) -> str:
    """
    Request raw quote data from Sina Finance.

    Parameters
    ----------
    sina_symbol : str
        Sina Finance symbol, for example 'sh600519' or 'hk00700'.

    Returns
    -------
    str
        Raw response text returned by Sina Finance.
    """

    url = f"{SINA_BASE_URL}{sina_symbol}"

    response = requests.get(
        url,
        headers=HEADERS,
        timeout=10
    )

    # Sina Finance returns Chinese text using GBK encoding
    response.encoding = "gbk"

    # Raise error if request fails
    response.raise_for_status()

    return response.text


def extract_quote_content(raw_text: str) -> list:
    """
    Extract comma-separated quote fields from raw Sina response.

    Example raw response:
    var hq_str_sh600519="贵州茅台,1306.000,...";

    Parameters
    ----------
    raw_text : str
        Raw response text from Sina Finance.

    Returns
    -------
    list
        List of quote fields.
    """

    if '="' not in raw_text:
        raise ValueError("Invalid Sina response format.")

    content = raw_text.split('="', 1)[1].split('";', 1)[0]

    if not content:
        raise ValueError("Empty quote content returned by Sina.")

    return content.split(",")


def calculate_order_book_metrics(record: dict) -> dict:
    """
    Calculate derived order book metrics for A-share stocks.

    Metrics:
    - bid_volume_total: total volume from bid 1 to bid 5
    - ask_volume_total: total volume from ask 1 to ask 5
    - bid_ask_volume_diff: bid volume minus ask volume
    - bid_ask_spread: ask1 price minus bid1 price
    - order_imbalance:
      (bid_volume_total - ask_volume_total)
      /
      (bid_volume_total + ask_volume_total)

    Parameters
    ----------
    record : dict
        Parsed A-share quote record.

    Returns
    -------
    dict
        Record with additional order book metrics.
    """

    bid_volumes = [
        record.get("bid1_volume"),
        record.get("bid2_volume"),
        record.get("bid3_volume"),
        record.get("bid4_volume"),
        record.get("bid5_volume")
    ]

    ask_volumes = [
        record.get("ask1_volume"),
        record.get("ask2_volume"),
        record.get("ask3_volume"),
        record.get("ask4_volume"),
        record.get("ask5_volume")
    ]

    bid_volume_total = sum(
        value for value in bid_volumes if value is not None
    )

    ask_volume_total = sum(
        value for value in ask_volumes if value is not None
    )

    record["bid_volume_total"] = bid_volume_total
    record["ask_volume_total"] = ask_volume_total

    record["bid_ask_volume_diff"] = (
        bid_volume_total - ask_volume_total
    )

    bid1_price = record.get("bid1_price")
    ask1_price = record.get("ask1_price")

    if bid1_price is not None and ask1_price is not None:
        record["bid_ask_spread"] = round(
            ask1_price - bid1_price,
            6
        )
    else:
        record["bid_ask_spread"] = None

    if bid_volume_total + ask_volume_total != 0:
        record["order_imbalance"] = round(
            (
                bid_volume_total - ask_volume_total
            )
            /
            (
                bid_volume_total + ask_volume_total
            ),
            6
        )
    else:
        record["order_imbalance"] = None

    return record


def parse_a_share_quote(
    fields: list,
    original_symbol: str,
    sina_symbol: str,
    english_name: str
) -> dict:
    """
    Parse A-share quote fields returned by Sina Finance.

    A-share field mapping:
    0  Chinese name
    1  Open price
    2  Previous close
    3  Current price
    4  High price
    5  Low price
    6  Bid price
    7  Ask price
    8  Volume
    9  Amount

    10 Bid 1 volume
    11 Bid 1 price
    12 Bid 2 volume
    13 Bid 2 price
    14 Bid 3 volume
    15 Bid 3 price
    16 Bid 4 volume
    17 Bid 4 price
    18 Bid 5 volume
    19 Bid 5 price

    20 Ask 1 volume
    21 Ask 1 price
    22 Ask 2 volume
    23 Ask 2 price
    24 Ask 3 volume
    25 Ask 3 price
    26 Ask 4 volume
    27 Ask 4 price
    28 Ask 5 volume
    29 Ask 5 price

    30 Trade date
    31 Trade time

    Parameters
    ----------
    fields : list
        Parsed Sina quote fields.

    original_symbol : str
        Original stock code used in stock_universe.py.

    sina_symbol : str
        Sina Finance symbol.

    english_name : str
        English stock name from stock_universe.py.

    Returns
    -------
    dict
        Standardized A-share stock quote record.
    """

    if len(fields) < 32:
        raise ValueError(
            f"Unexpected A-share field length: {len(fields)}"
        )

    current_price = safe_float(fields[3])
    previous_close = safe_float(fields[2])

    price_change = None
    pct_change = None

    if (
        current_price is not None
        and previous_close is not None
        and previous_close != 0
    ):
        price_change = round(
            current_price - previous_close,
            6
        )

        pct_change = round(
            price_change / previous_close * 100,
            6
        )

    trade_datetime = f"{fields[30]} {fields[31]}"

    record = {
        "symbol": original_symbol,
        "sina_symbol": sina_symbol,
        "name_en": english_name,
        "name_cn": fields[0],
        "market": "A-share",

        "open": safe_float(fields[1]),
        "previous_close": previous_close,
        "current_price": current_price,
        "high": safe_float(fields[4]),
        "low": safe_float(fields[5]),

        "price_change": price_change,
        "pct_change": pct_change,

        "volume": safe_int(fields[8]),
        "amount": safe_float(fields[9]),

        "bid1_volume": safe_int(fields[10]),
        "bid1_price": safe_float(fields[11]),
        "bid2_volume": safe_int(fields[12]),
        "bid2_price": safe_float(fields[13]),
        "bid3_volume": safe_int(fields[14]),
        "bid3_price": safe_float(fields[15]),
        "bid4_volume": safe_int(fields[16]),
        "bid4_price": safe_float(fields[17]),
        "bid5_volume": safe_int(fields[18]),
        "bid5_price": safe_float(fields[19]),

        "ask1_volume": safe_int(fields[20]),
        "ask1_price": safe_float(fields[21]),
        "ask2_volume": safe_int(fields[22]),
        "ask2_price": safe_float(fields[23]),
        "ask3_volume": safe_int(fields[24]),
        "ask3_price": safe_float(fields[25]),
        "ask4_volume": safe_int(fields[26]),
        "ask4_price": safe_float(fields[27]),
        "ask5_volume": safe_int(fields[28]),
        "ask5_price": safe_float(fields[29]),

        "trade_datetime": trade_datetime,
        "source": "Sina Finance",
        "extracted_at": datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )
    }

    record = calculate_order_book_metrics(record)

    return record


def parse_hk_share_quote(
    fields: list,
    original_symbol: str,
    sina_symbol: str,
    english_name: str
) -> dict:
    """
    Parse Hong Kong stock quote fields returned by Sina Finance.

    Hong Kong field mapping:
    0  English/short name
    1  Chinese name
    2  Open price
    3  Previous close
    4  High price
    5  Low price
    6  Current price
    7  Price change
    8  Percentage change
    9  Bid price
    10 Ask price
    11 Amount
    12 Volume
    15 52-week high
    16 52-week low
    17 Trade date
    18 Trade time

    Parameters
    ----------
    fields : list
        Parsed Sina quote fields.

    original_symbol : str
        Original Hong Kong stock code.

    sina_symbol : str
        Sina Finance Hong Kong symbol.

    english_name : str
        English stock name from stock_universe.py.

    Returns
    -------
    dict
        Standardized Hong Kong stock quote record.
    """

    if len(fields) < 19:
        raise ValueError(
            f"Unexpected HK-share field length: {len(fields)}"
        )

    trade_datetime = f"{fields[17]} {fields[18]}"

    return {
        "symbol": original_symbol,
        "sina_symbol": sina_symbol,
        "name_en": english_name,
        "name_cn": fields[1],
        "market": "HK-share",

        "open": safe_float(fields[2]),
        "previous_close": safe_float(fields[3]),
        "current_price": safe_float(fields[6]),
        "high": safe_float(fields[4]),
        "low": safe_float(fields[5]),

        "price_change": safe_float(fields[7]),
        "pct_change": safe_float(fields[8]),

        "volume": safe_int(fields[12]),
        "amount": safe_float(fields[11]),

        # HK quote only provides top bid/ask price in this interface
        "bid1_volume": None,
        "bid1_price": safe_float(fields[9]),
        "bid2_volume": None,
        "bid2_price": None,
        "bid3_volume": None,
        "bid3_price": None,
        "bid4_volume": None,
        "bid4_price": None,
        "bid5_volume": None,
        "bid5_price": None,

        "ask1_volume": None,
        "ask1_price": safe_float(fields[10]),
        "ask2_volume": None,
        "ask2_price": None,
        "ask3_volume": None,
        "ask3_price": None,
        "ask4_volume": None,
        "ask4_price": None,
        "ask5_volume": None,
        "ask5_price": None,

        "bid_volume_total": None,
        "ask_volume_total": None,
        "bid_ask_volume_diff": None,

        "bid_ask_spread": (
            round(
                safe_float(fields[10]) - safe_float(fields[9]),
                6
            )
            if safe_float(fields[9]) is not None
            and safe_float(fields[10]) is not None
            else None
        ),

        "order_imbalance": None,

        "trade_datetime": trade_datetime,
        "source": "Sina Finance",
        "extracted_at": datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )
    }


def extract_a_share_quote(symbol: str, name: str) -> dict:
    """
    Extract and parse one A-share stock quote.

    Parameters
    ----------
    symbol : str
        A-share stock code.

    name : str
        English stock name.

    Returns
    -------
    dict
        Standardized A-share quote record.
    """

    sina_symbol = convert_a_share_to_sina_symbol(symbol)

    print(f"Extracting A-share: {symbol} - {name}")

    raw_text = request_sina_quote(sina_symbol)

    fields = extract_quote_content(raw_text)

    return parse_a_share_quote(
        fields=fields,
        original_symbol=symbol,
        sina_symbol=sina_symbol,
        english_name=name
    )


def extract_hk_share_quote(symbol: str, name: str) -> dict:
    """
    Extract and parse one Hong Kong stock quote.

    Parameters
    ----------
    symbol : str
        Hong Kong stock code.

    name : str
        English stock name.

    Returns
    -------
    dict
        Standardized Hong Kong quote record.
    """

    sina_symbol = convert_hk_share_to_sina_symbol(symbol)

    print(f"Extracting HK share: {symbol} - {name}")

    raw_text = request_sina_quote(sina_symbol)

    fields = extract_quote_content(raw_text)

    return parse_hk_share_quote(
        fields=fields,
        original_symbol=symbol,
        sina_symbol=sina_symbol,
        english_name=name
    )


def run_sina_stock_extract_pipeline():
    """
    Run Sina Finance stock quote extraction pipeline.

    This function extracts real-time stock quote data for
    both A-shares and Hong Kong stocks, then saves the
    standardized records into a CSV file.

    Returns
    -------
    None
    """

    records = []

    # --------------------------------------------------
    # Extract A-share quotes
    # --------------------------------------------------

    for symbol, name in A_SHARES.items():

        try:
            record = extract_a_share_quote(
                symbol=symbol,
                name=name
            )

            records.append(record)

        except Exception as e:
            print(
                f"Failed to extract A-share {symbol}: {e}"
            )

        # Add random delay to reduce request pressure
        time.sleep(
            random.uniform(0.5, 1.2)
        )

    # --------------------------------------------------
    # Extract Hong Kong stock quotes
    # --------------------------------------------------

    for symbol, name in HK_SHARES.items():

        try:
            record = extract_hk_share_quote(
                symbol=symbol,
                name=name
            )

            records.append(record)

        except Exception as e:
            print(
                f"Failed to extract HK share {symbol}: {e}"
            )

        # Add random delay to reduce request pressure
        time.sleep(
            random.uniform(0.5, 1.2)
        )

    # Stop the pipeline if no data was extracted
    if not records:
        raise ValueError("No Sina stock data was extracted.")

    df = pd.DataFrame(records)

    output_path = RAW_DATA_DIR / "sina_stock_quotes_raw.csv"

    df.to_csv(
        output_path,
        index=False,
        encoding="utf-8-sig"
    )

    print("=" * 60)
    print("Sina stock extraction completed.")
    print(f"Output path: {output_path}")
    print(f"Total records: {len(df)}")
    print("=" * 60)


if __name__ == "__main__":
    run_sina_stock_extract_pipeline()

