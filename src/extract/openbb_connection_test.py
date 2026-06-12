"""
OpenBB connection test.

This script verifies:
1. OpenBB has been installed correctly.
2. The Yahoo Finance provider is available.
3. The existing FRED API key can be used through OpenBB.
4. OpenBB responses can be converted into pandas DataFrames.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from openbb import obb


# Locate the project root:
# D:/Automated_Data_Pipeline
PROJECT_ROOT = Path(__file__).resolve().parents[2]

# Load the existing .env file.
load_dotenv(PROJECT_ROOT / ".env")


def configure_openbb() -> None:
    """Load provider credentials into the current OpenBB session."""

    fred_api_key = os.getenv("FRED_API_KEY")

    if not fred_api_key:
        raise RuntimeError(
            "FRED_API_KEY was not found in the project .env file."
        )

    # The credential is only assigned to the current Python session.
    obb.user.credentials.fred_api_key = fred_api_key


def test_market_data() -> None:
    """Test historical S&P 500 data through the yfinance provider."""

    response = obb.index.price.historical(
        symbol="^GSPC",
        start_date="2026-01-01",
        provider="yfinance",
    )

    market_df = response.to_df()

    if market_df.empty:
        raise RuntimeError("OpenBB returned an empty market DataFrame.")

    print("\n" + "=" * 70)
    print("OPENBB MARKET DATA TEST")
    print("=" * 70)
    print(market_df.tail())
    print(f"\nRows returned: {len(market_df):,}")
    print(f"Provider: {response.provider}")


def test_fred_data() -> None:
    """Test US unemployment data through the FRED provider."""

    response = obb.economy.fred_series(
        symbol="UNRATE",
        start_date="2025-01-01",
        provider="fred",
    )

    fred_df = response.to_df()

    if fred_df.empty:
        raise RuntimeError("OpenBB returned an empty FRED DataFrame.")

    print("\n" + "=" * 70)
    print("OPENBB FRED DATA TEST")
    print("=" * 70)
    print(fred_df.tail())
    print(f"\nRows returned: {len(fred_df):,}")
    print(f"Provider: {response.provider}")


def main() -> None:
    """Run all OpenBB connection tests."""

    configure_openbb()

    print("=" * 70)
    print("INSTALLED OPENBB PROVIDERS")
    print("=" * 70)
    print(obb.coverage.providers)

    test_market_data()
    test_fred_data()

    print("\n" + "=" * 70)
    print("OPENBB CONNECTION TEST COMPLETED SUCCESSFULLY")
    print("=" * 70)


if __name__ == "__main__":
    main()

