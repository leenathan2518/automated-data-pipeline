"""
test_sina_quote_fields.py

Test how many valid fields can be extracted from
Sina Finance quote data.

This script uses the test stock universe defined in:

src/config/stock_universe.py

Purpose:
- Test A-share and Hong Kong quote availability
- Count returned fields
- Print field index mapping
- Check whether bid/ask order book data is available
- Help design the final stock extraction schema

Author
------
Vinci Lee
"""

import time
import requests

from src.config.stock_universe import A_SHARES, HK_SHARES


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


def convert_a_share_to_sina_symbol(symbol: str) -> str:
    """
    Convert an A-share stock code to a Sina Finance symbol.

    Parameters
    ----------
    symbol : str
        A-share stock code.

    Returns
    -------
    str
        Sina Finance symbol.
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
        Hong Kong stock code.

    Returns
    -------
    str
        Sina Finance Hong Kong stock symbol.
    """

    return f"hk{symbol}"


def request_sina_quote(sina_symbol: str) -> str:
    """
    Request quote data from Sina Finance.

    Parameters
    ----------
    sina_symbol : str
        Sina Finance stock symbol.

    Returns
    -------
    str
        Raw response text.
    """

    url = f"{SINA_BASE_URL}{sina_symbol}"

    response = requests.get(
        url,
        headers=HEADERS,
        timeout=10
    )

    response.encoding = "gbk"
    response.raise_for_status()

    return response.text


def extract_quote_fields(raw_text: str) -> list:
    """
    Extract quote fields from Sina raw response.

    Parameters
    ----------
    raw_text : str
        Raw Sina response text.

    Returns
    -------
    list
        Parsed quote fields.
    """

    if '="' not in raw_text:
        raise ValueError("Invalid Sina response format.")

    content = raw_text.split('="', 1)[1].split('";', 1)[0]

    if not content:
        raise ValueError("Empty quote content.")

    return content.split(",")


def print_field_report(
    market: str,
    symbol: str,
    name: str,
    sina_symbol: str,
    fields: list
):
    """
    Print a detailed field report for one stock.

    Parameters
    ----------
    market : str
        Market name: A-share or HK-share.

    symbol : str
        Original stock code.

    name : str
        English stock name.

    sina_symbol : str
        Sina Finance stock symbol.

    fields : list
        Parsed quote fields.

    Returns
    -------
    None
    """

    print("\n" + "=" * 80)
    print(f"Market: {market}")
    print(f"Stock: {symbol} - {name}")
    print(f"Sina Symbol: {sina_symbol}")
    print(f"Total Fields Returned: {len(fields)}")
    print("-" * 80)

    # Print all returned fields with their index positions
    for index, value in enumerate(fields):
        print(f"{index:02d}: {value}")

    print("-" * 80)

    # A-share quote usually contains five-level bid/ask data
    if market == "A-share" and len(fields) >= 32:

        print("A-share Basic Data Check:")
        print(f"Chinese Name      : {fields[0]}")
        print(f"Open Price        : {fields[1]}")
        print(f"Previous Close    : {fields[2]}")
        print(f"Current Price     : {fields[3]}")
        print(f"High Price        : {fields[4]}")
        print(f"Low Price         : {fields[5]}")
        print(f"Volume            : {fields[8]}")
        print(f"Amount            : {fields[9]}")
        print(f"Trade Date        : {fields[30]}")
        print(f"Trade Time        : {fields[31]}")

        print("\nA-share Five-level Order Book Check:")
        print(f"Bid 1 Volume      : {fields[10]}")
        print(f"Bid 1 Price       : {fields[11]}")
        print(f"Bid 2 Volume      : {fields[12]}")
        print(f"Bid 2 Price       : {fields[13]}")
        print(f"Bid 3 Volume      : {fields[14]}")
        print(f"Bid 3 Price       : {fields[15]}")
        print(f"Bid 4 Volume      : {fields[16]}")
        print(f"Bid 4 Price       : {fields[17]}")
        print(f"Bid 5 Volume      : {fields[18]}")
        print(f"Bid 5 Price       : {fields[19]}")

        print(f"Ask 1 Volume      : {fields[20]}")
        print(f"Ask 1 Price       : {fields[21]}")
        print(f"Ask 2 Volume      : {fields[22]}")
        print(f"Ask 2 Price       : {fields[23]}")
        print(f"Ask 3 Volume      : {fields[24]}")
        print(f"Ask 3 Price       : {fields[25]}")
        print(f"Ask 4 Volume      : {fields[26]}")
        print(f"Ask 4 Price       : {fields[27]}")
        print(f"Ask 5 Volume      : {fields[28]}")
        print(f"Ask 5 Price       : {fields[29]}")

        bid_volume_total = sum(
            int(float(fields[i]))
            for i in [10, 12, 14, 16, 18]
        )

        ask_volume_total = sum(
            int(float(fields[i]))
            for i in [20, 22, 24, 26, 28]
        )

        print("\nDerived Order Book Metrics:")
        print(f"Total Bid Volume  : {bid_volume_total}")
        print(f"Total Ask Volume  : {ask_volume_total}")
        print(
            f"Bid-Ask Difference: "
            f"{bid_volume_total - ask_volume_total}"
        )

        if bid_volume_total + ask_volume_total != 0:

            imbalance = (
                bid_volume_total - ask_volume_total
            ) / (
                bid_volume_total + ask_volume_total
            )

            print(f"Order Imbalance   : {round(imbalance, 4)}")

    # Hong Kong quote has fewer fields and usually no five-level order book
    elif market == "HK-share" and len(fields) >= 19:

        print("HK-share Basic Data Check:")
        print(f"English Name      : {fields[0]}")
        print(f"Chinese Name      : {fields[1]}")
        print(f"Open Price        : {fields[2]}")
        print(f"Previous Close    : {fields[3]}")
        print(f"High Price        : {fields[4]}")
        print(f"Low Price         : {fields[5]}")
        print(f"Current Price     : {fields[6]}")
        print(f"Change            : {fields[7]}")
        print(f"Pct Change        : {fields[8]}")
        print(f"Amount            : {fields[11]}")
        print(f"Volume            : {fields[12]}")
        print(f"Trade Date        : {fields[17]}")
        print(f"Trade Time        : {fields[18]}")

    else:
        print("Warning: Unexpected field structure.")


def run_sina_field_test():
    """
    Run Sina quote field test for the test stock universe.

    Returns
    -------
    None
    """

    print("=" * 80)
    print("SINA FINANCE QUOTE FIELD TEST STARTED")
    print("=" * 80)

    # --------------------------------------------------
    # Test A-share stocks
    # --------------------------------------------------

    for symbol, name in A_SHARES.items():

        sina_symbol = convert_a_share_to_sina_symbol(symbol)

        try:
            raw_text = request_sina_quote(sina_symbol)
            fields = extract_quote_fields(raw_text)

            print_field_report(
                market="A-share",
                symbol=symbol,
                name=name,
                sina_symbol=sina_symbol,
                fields=fields
            )

        except Exception as e:
            print(f"Failed to test A-share {symbol}: {e}")

        # Add delay to reduce request pressure
        time.sleep(0.5)

    # --------------------------------------------------
    # Test Hong Kong stocks
    # --------------------------------------------------

    for symbol, name in HK_SHARES.items():

        sina_symbol = convert_hk_share_to_sina_symbol(symbol)

        try:
            raw_text = request_sina_quote(sina_symbol)
            fields = extract_quote_fields(raw_text)

            print_field_report(
                market="HK-share",
                symbol=symbol,
                name=name,
                sina_symbol=sina_symbol,
                fields=fields
            )

        except Exception as e:
            print(f"Failed to test HK share {symbol}: {e}")

        # Add delay to reduce request pressure
        time.sleep(0.5)

    print("\n" + "=" * 80)
    print("SINA FINANCE QUOTE FIELD TEST COMPLETED")
    print("=" * 80)


if __name__ == "__main__":
    run_sina_field_test()

