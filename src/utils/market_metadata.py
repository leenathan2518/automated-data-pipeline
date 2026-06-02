"""
market_metadata.py

This file stores metadata for financial market indicators.

Using metadata allows us to:
- Keep ticker information in one place
- Add or remove assets easily
- Standardize asset names and asset types
"""

MARKET_TICKERS = {
    "SPY": {
        "asset_name": "S&P 500 ETF",
        "asset_type": "Equity ETF",
        "source": "Yahoo Finance"
    },
    "QQQ": {
        "asset_name": "Nasdaq 100 ETF",
        "asset_type": "Equity ETF",
        "source": "Yahoo Finance"
    },
    "GLD": {
        "asset_name": "Gold ETF",
        "asset_type": "Commodity ETF",
        "source": "Yahoo Finance"
    },
    "CL=F": {
        "asset_name": "Crude Oil Futures",
        "asset_type": "Commodity Futures",
        "source": "Yahoo Finance"
    },
    "^TNX": {
        "asset_name": "US 10-Year Treasury Yield",
        "asset_type": "Bond Yield",
        "source": "Yahoo Finance"
    },
    "^TYX": {
        "asset_name": "US 30-Year Treasury Yield",
        "asset_type": "Bond Yield",
        "source": "Yahoo Finance"
    },
    "DX-Y.NYB": {
        "asset_name": "US Dollar Index",
        "asset_type": "Currency Index",
        "source": "Yahoo Finance"
    },
    "YM=F": {
        "asset_name": "Dow Futures / US 30",
        "asset_type": "Equity Index Futures",
        "source": "Yahoo Finance"
    },
    "ES=F": {
        "asset_name": "S&P 500 Futures / US 500",
        "asset_type": "Equity Index Futures",
        "source": "Yahoo Finance"
    }
}