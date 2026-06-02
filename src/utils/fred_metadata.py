"""
fred_metadata.py

This file stores metadata for FRED indicators.
Using metadata makes the pipeline easier to maintain and extend.
"""

FRED_INDICATORS = {
    "UNRATE": {
        "indicator_name": "Unemployment Rate",
        "country": "United States",
        "frequency": "Monthly",
        "unit": "Percent"
    },
    "CPIAUCSL": {
        "indicator_name": "Consumer Price Index for All Urban Consumers",
        "country": "United States",
        "frequency": "Monthly",
        "unit": "Index 1982-1984=100"
    },
    "FEDFUNDS": {
        "indicator_name": "Federal Funds Effective Rate",
        "country": "United States",
        "frequency": "Monthly",
        "unit": "Percent"
    }
}