"""
load_macro_to_postgres.py

This module loads processed macroeconomic data into PostgreSQL.

Current function:
- Read processed macro CSV
- Connect to PostgreSQL
- Upsert data into macro_indicators table
"""

import os
import sys
import pandas as pd
from sqlalchemy import text


PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "../..")
)
sys.path.append(PROJECT_ROOT)


from src.load.db_connection import get_engine


def load_macro_data():
    """
    Load processed macro data into PostgreSQL using UPSERT.

    UPSERT logic:
    - If date + country + indicator_code already exists, update the row.
    - If it does not exist, insert a new row.
    """

    csv_path = os.path.join(
        "data",
        "processed",
        "macro_indicators_processed.csv"
    )

    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"Processed macro file not found: {csv_path}")

    df = pd.read_csv(csv_path)

    print(f"Loaded macro CSV shape: {df.shape}")

    df["date"] = pd.to_datetime(df["date"]).dt.date

    engine = get_engine()

    with engine.begin() as conn:

        for _, row in df.iterrows():

            query = text("""
                INSERT INTO macro_indicators
                (
                    date,
                    country,
                    indicator_code,
                    indicator_name,
                    value,
                    frequency,
                    unit,
                    source
                )
                VALUES
                (
                    :date,
                    :country,
                    :indicator_code,
                    :indicator_name,
                    :value,
                    :frequency,
                    :unit,
                    :source
                )
                ON CONFLICT (date, country, indicator_code)
                DO UPDATE SET
                    indicator_name = EXCLUDED.indicator_name,
                    value = EXCLUDED.value,
                    frequency = EXCLUDED.frequency,
                    unit = EXCLUDED.unit,
                    source = EXCLUDED.source;
            """)

            conn.execute(
                query,
                {
                    "date": row["date"],
                    "country": row["country"],
                    "indicator_code": row["indicator_code"],
                    "indicator_name": row["indicator_name"],
                    "value": row["value"],
                    "frequency": row["frequency"],
                    "unit": row["unit"],
                    "source": row["source"],
                }
            )

    print(
        f"Successfully upserted {len(df)} rows "
        f"into macro_indicators table."
    )


if __name__ == "__main__":
    load_macro_data()


