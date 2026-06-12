"""
Load transformed OpenBB market data into PostgreSQL.

This module:
1. Reads the processed OpenBB market CSV.
2. Creates the PostgreSQL table when necessary.
3. Inserts new records.
4. Updates existing symbol/date records.
5. Prevents duplicate observations.
"""

from __future__ import annotations

import os
from pathlib import Path

import numpy as np
import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine


PROJECT_ROOT = Path(__file__).resolve().parents[2]

INPUT_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "openbb_market_data_clean.csv"
)

load_dotenv(PROJECT_ROOT / ".env")


TABLE_NAME = "openbb_market_data"


def create_postgres_engine() -> Engine:
    """Create a SQLAlchemy PostgreSQL engine."""

    db_host = os.getenv("DB_HOST", "localhost")
    db_port = os.getenv("DB_PORT", "5432")
    db_name = os.getenv("DB_NAME")
    db_user = os.getenv("DB_USER")
    db_password = os.getenv("DB_PASSWORD")

    missing_variables = [
        name
        for name, value in {
            "DB_NAME": db_name,
            "DB_USER": db_user,
            "DB_PASSWORD": db_password,
        }.items()
        if not value
    ]

    if missing_variables:
        raise RuntimeError(
            "Missing PostgreSQL environment variables: "
            + ", ".join(missing_variables)
        )

    connection_url = (
        f"postgresql+psycopg2://"
        f"{db_user}:{db_password}"
        f"@{db_host}:{db_port}/{db_name}"
    )

    return create_engine(
        connection_url,
        pool_pre_ping=True,
    )


def load_processed_data() -> pd.DataFrame:
    """Read and prepare the transformed OpenBB CSV."""

    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            f"Processed OpenBB file was not found: {INPUT_FILE}"
        )

    df = pd.read_csv(
        INPUT_FILE,
        parse_dates=[
            "date",
            "extracted_at",
            "transformed_at",
        ],
    )

    print("=" * 70)
    print("LOAD OPENBB MARKET DATA TO POSTGRESQL")
    print("=" * 70)
    print(f"Input file: {INPUT_FILE}")
    print(f"Rows loaded from CSV: {len(df):,}")

    required_columns = [
        "date",
        "symbol",
        "asset_name",
        "asset_type",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "provider",
        "extracted_at",
        "ohlc_valid",
        "daily_return",
        "log_return",
        "intraday_return",
        "daily_range_pct",
        "transformed_at",
    ]

    missing_columns = [
        column
        for column in required_columns
        if column not in df.columns
    ]

    if missing_columns:
        raise ValueError(
            "Missing required columns: "
            + ", ".join(missing_columns)
        )

    df = df[required_columns].copy()

    df["date"] = pd.to_datetime(
        df["date"],
        errors="coerce",
    ).dt.date

    numeric_columns = [
        "open",
        "high",
        "low",
        "close",
        "volume",
        "daily_return",
        "log_return",
        "intraday_return",
        "daily_range_pct",
    ]

    for column in numeric_columns:
        df[column] = pd.to_numeric(
            df[column],
            errors="coerce",
        )

    df["ohlc_valid"] = (
        df["ohlc_valid"]
        .astype("boolean")
    )

    df = df.dropna(
        subset=[
            "date",
            "symbol",
            "close",
        ]
    )

    df = df.drop_duplicates(
        subset=[
            "date",
            "symbol",
        ],
        keep="last",
    )

    # Convert pandas NaN/NaT values into Python None for PostgreSQL.
    df = df.replace(
        {
            np.nan: None,
            pd.NaT: None,
        }
    )

    print(f"Rows prepared for database: {len(df):,}")

    return df


def create_table(engine: Engine) -> None:
    """Create the OpenBB market-data table and indexes."""

    create_table_sql = f"""
    CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
        market_id BIGSERIAL PRIMARY KEY,
        date DATE NOT NULL,
        symbol VARCHAR(30) NOT NULL,
        asset_name VARCHAR(150) NOT NULL,
        asset_type VARCHAR(50) NOT NULL,

        open NUMERIC(20, 8),
        high NUMERIC(20, 8),
        low NUMERIC(20, 8),
        close NUMERIC(20, 8) NOT NULL,
        volume NUMERIC(24, 4),

        provider VARCHAR(50) NOT NULL,
        extracted_at TIMESTAMP,
        transformed_at TIMESTAMP,

        ohlc_valid BOOLEAN,
        daily_return DOUBLE PRECISION,
        log_return DOUBLE PRECISION,
        intraday_return DOUBLE PRECISION,
        daily_range_pct DOUBLE PRECISION,

        loaded_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

        CONSTRAINT uq_openbb_market_symbol_date
            UNIQUE (symbol, date)
    );
    """

    create_indexes_sql = [
        f"""
        CREATE INDEX IF NOT EXISTS
        idx_openbb_market_date
        ON {TABLE_NAME} (date);
        """,
        f"""
        CREATE INDEX IF NOT EXISTS
        idx_openbb_market_symbol
        ON {TABLE_NAME} (symbol);
        """,
        f"""
        CREATE INDEX IF NOT EXISTS
        idx_openbb_market_asset_type
        ON {TABLE_NAME} (asset_type);
        """,
        f"""
        CREATE INDEX IF NOT EXISTS
        idx_openbb_market_provider
        ON {TABLE_NAME} (provider);
        """,
    ]

    with engine.begin() as connection:
        connection.execute(text(create_table_sql))

        for statement in create_indexes_sql:
            connection.execute(text(statement))

    print(f"Table ready: {TABLE_NAME}")


def upsert_market_data(
    engine: Engine,
    df: pd.DataFrame,
) -> int:
    """
    Insert or update OpenBB market records.

    The symbol/date pair is used as the natural unique key.
    """

    upsert_sql = text(
        f"""
        INSERT INTO {TABLE_NAME} (
            date,
            symbol,
            asset_name,
            asset_type,
            open,
            high,
            low,
            close,
            volume,
            provider,
            extracted_at,
            ohlc_valid,
            daily_return,
            log_return,
            intraday_return,
            daily_range_pct,
            transformed_at
        )
        VALUES (
            :date,
            :symbol,
            :asset_name,
            :asset_type,
            :open,
            :high,
            :low,
            :close,
            :volume,
            :provider,
            :extracted_at,
            :ohlc_valid,
            :daily_return,
            :log_return,
            :intraday_return,
            :daily_range_pct,
            :transformed_at
        )
        ON CONFLICT (symbol, date)
        DO UPDATE SET
            asset_name = EXCLUDED.asset_name,
            asset_type = EXCLUDED.asset_type,
            open = EXCLUDED.open,
            high = EXCLUDED.high,
            low = EXCLUDED.low,
            close = EXCLUDED.close,
            volume = EXCLUDED.volume,
            provider = EXCLUDED.provider,
            extracted_at = EXCLUDED.extracted_at,
            ohlc_valid = EXCLUDED.ohlc_valid,
            daily_return = EXCLUDED.daily_return,
            log_return = EXCLUDED.log_return,
            intraday_return = EXCLUDED.intraday_return,
            daily_range_pct = EXCLUDED.daily_range_pct,
            transformed_at = EXCLUDED.transformed_at,
            loaded_at = CURRENT_TIMESTAMP;
        """
    )

    records = df.to_dict(
        orient="records",
    )

    with engine.begin() as connection:
        connection.execute(
            upsert_sql,
            records,
        )

    return len(records)


def verify_database(
    engine: Engine,
) -> None:
    """Run validation queries after loading."""

    summary_sql = text(
        f"""
        SELECT
            COUNT(*) AS total_rows,
            COUNT(DISTINCT symbol) AS total_symbols,
            MIN(date) AS earliest_date,
            MAX(date) AS latest_date
        FROM {TABLE_NAME};
        """
    )

    symbol_sql = text(
        f"""
        SELECT
            symbol,
            asset_name,
            asset_type,
            provider,
            COUNT(*) AS row_count,
            MIN(date) AS earliest_date,
            MAX(date) AS latest_date
        FROM {TABLE_NAME}
        GROUP BY
            symbol,
            asset_name,
            asset_type,
            provider
        ORDER BY symbol;
        """
    )

    duplicate_sql = text(
        f"""
        SELECT COUNT(*) AS duplicate_groups
        FROM (
            SELECT
                symbol,
                date,
                COUNT(*)
            FROM {TABLE_NAME}
            GROUP BY
                symbol,
                date
            HAVING COUNT(*) > 1
        ) duplicates;
        """
    )

    invalid_sql = text(
        f"""
        SELECT COUNT(*) AS invalid_ohlc_rows
        FROM {TABLE_NAME}
        WHERE ohlc_valid = FALSE;
        """
    )

    with engine.connect() as connection:
        summary = connection.execute(
            summary_sql
        ).mappings().one()

        symbol_rows = connection.execute(
            symbol_sql
        ).mappings().all()

        duplicate_count = connection.execute(
            duplicate_sql
        ).scalar_one()

        invalid_count = connection.execute(
            invalid_sql
        ).scalar_one()

    print("\n" + "=" * 70)
    print("DATABASE VERIFICATION")
    print("=" * 70)

    print(f"Total rows: {summary['total_rows']:,}")
    print(f"Total symbols: {summary['total_symbols']}")
    print(
        f"Date range: "
        f"{summary['earliest_date']} to "
        f"{summary['latest_date']}"
    )
    print(f"Duplicate groups: {duplicate_count}")
    print(f"Invalid OHLC rows: {invalid_count}")

    print("\nRows by symbol:")

    for row in symbol_rows:
        print(
            f"{row['symbol']:<10} "
            f"{row['row_count']:>5} rows  "
            f"{row['earliest_date']} to "
            f"{row['latest_date']}  "
            f"[{row['asset_type']}, {row['provider']}]"
        )


def load_openbb_market_to_postgres() -> None:
    """Run the complete PostgreSQL loading process."""

    engine = create_postgres_engine()

    try:
        df = load_processed_data()

        create_table(engine)

        affected_rows = upsert_market_data(
            engine,
            df,
        )

        print(
            f"Rows inserted or updated: "
            f"{affected_rows:,}"
        )

        verify_database(engine)

        print("\n" + "=" * 70)
        print("OPENBB MARKET DATA LOAD COMPLETED SUCCESSFULLY")
        print("=" * 70)

    finally:
        engine.dispose()


def main() -> None:
    """Run the loader directly."""

    load_openbb_market_to_postgres()


if __name__ == "__main__":
    main()
