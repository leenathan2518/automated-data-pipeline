"""
stock_universe.py

Stock universe configuration.

This module defines the stocks tracked by the
Automated Financial Data Pipeline.

Author
------
Vinci Lee
"""

# ==================================================
# A-SHARES
# ==================================================

A_SHARES = {

    # Financials
    "000001": "Ping An Bank",
    "600036": "China Merchants Bank",

    # Consumer
    "600519": "Kweichow Moutai",

    # New Energy
    "300750": "CATL",
    "002594": "BYD",

    # Semiconductors
    "688981": "SMIC"
}

# ==================================================
# HONG KONG SHARES
# ==================================================

HK_SHARES = {

    "00700": "Tencent",
    "09988": "Alibaba",
    "03690": "Meituan"
}


# ==================================================
# COMBINED STOCK UNIVERSE
# ==================================================

ALL_STOCKS = {
    **A_SHARES,
    **HK_SHARES
}

