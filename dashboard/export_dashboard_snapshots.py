"""
Export local ETL outputs into lightweight CSV snapshots for online deployment.

Run this script after a successful local pipeline execution:

    python dashboard/export_dashboard_snapshots.py

The generated files can be committed to GitHub and read by online_app.py.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT_DIR = PROJECT_ROOT / "dashboard" / "snapshots"
LOG_DIR = PROJECT_ROOT / "logs"

load_dotenv(PROJECT_ROOT / ".env")


def get_engine() -> Engine:
    db_host = os.getenv("DB_HOST", "localhost")
    db_port = os.getenv("DB_PORT", "5432")
    db_name = os.getenv("DB_NAME")
    db_user = os.getenv("DB_USER")
    db_password = os.getenv("DB_PASSWORD")

    missing = [
        key for key, value in {
            "DB_NAME": db_name,
            "DB_USER": db_user,
            "DB_PASSWORD": db_password,
        }.items()
        if not value
    ]

    if missing:
        raise RuntimeError(
            "Missing database environment variables: "
            + ", ".join(missing)
        )

    url = (
        f"postgresql+psycopg2://"
        f"{db_user}:{db_password}"
        f"@{db_host}:{db_port}/{db_name}"
    )

    return create_engine(url, pool_pre_ping=True)


def parse_latest_log() -> tuple[pd.DataFrame, pd.DataFrame]:
    summary = {
        "status": "UNKNOWN",
        "runtime_seconds": None,
        "latest_timestamp": None,
        "log_file": None,
    }

    step_rows: list[dict[str, Any]] = []

    if not LOG_DIR.exists():
        return pd.DataFrame([summary]), pd.DataFrame(step_rows)

    logs = sorted(
        LOG_DIR.glob("*.log"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )

    if not logs:
        return pd.DataFrame([summary]), pd.DataFrame(step_rows)

    latest_log = logs[0]
    content = latest_log.read_text(
        encoding="utf-8",
        errors="replace",
    )

    summary["log_file"] = latest_log.name

    timestamps = re.findall(
        r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})",
        content,
    )

    if timestamps:
        summary["latest_timestamp"] = timestamps[-1]

    if "PIPELINE COMPLETED SUCCESSFULLY" in content:
        summary["status"] = "SUCCESS"
    elif "PIPELINE FAILED" in content:
        summary["status"] = "FAILED"
    elif "AUTOMATED DATA PIPELINE STARTED" in content:
        summary["status"] = "INCOMPLETE"

    runtimes = re.findall(
        r"Total Runtime:\s*([0-9.]+)\s*seconds",
        content,
    )

    if runtimes:
        summary["runtime_seconds"] = float(runtimes[-1])

    pattern = re.compile(
        r"\[(\d+)/(\d+)\]\s+(Starting|Completed|Failed):\s+"
        r"(.+?)(?:\s+\(([0-9.]+)\s+seconds\))?$"
    )

    latest_by_step: dict[int, dict[str, Any]] = {}

    for line in content.splitlines():
        message = line.split("|")[-1].strip()
        match = pattern.search(message)

        if not match:
            continue

        event = match.group(3)

        latest_by_step[int(match.group(1))] = {
            "step_number": int(match.group(1)),
            "total_steps": int(match.group(2)),
            "step_name": match.group(4).strip(),
            "status": {
                "Completed": "PASS",
                "Failed": "FAIL",
                "Starting": "INCOMPLETE",
            }[event],
            "runtime_seconds": (
                float(match.group(5))
                if match.group(5)
                else None
            ),
        }

    step_rows = [
        latest_by_step[number]
        for number in sorted(latest_by_step)
    ]

    return pd.DataFrame([summary]), pd.DataFrame(step_rows)


def query_df(engine: Engine, sql: str) -> pd.DataFrame:
    with engine.connect() as connection:
        return pd.read_sql(text(sql), connection)


def export_database_snapshots(engine: Engine) -> None:
    tables = set(inspect(engine).get_table_names())

    inventory_rows = []

    if "macro_indicators" in tables:
        macro = query_df(
            engine,
            """
            SELECT
                COUNT(*) AS rows,
                COUNT(DISTINCT indicator_code) AS entities,
                MIN(date) AS earliest_date,
                MAX(date) AS latest_date
            FROM macro_indicators;
            """,
        ).iloc[0]

        inventory_rows.append({
            "dataset": "Macro Indicators",
            "table_name": "macro_indicators",
            "rows": int(macro["rows"]),
            "entities": int(macro["entities"]),
            "entity_label": "Series",
            "earliest_date": macro["earliest_date"],
            "latest_date": macro["latest_date"],
        })

    if "openbb_market_data" in tables:
        market = query_df(
            engine,
            """
            SELECT
                COUNT(*) AS rows,
                COUNT(DISTINCT symbol) AS entities,
                MIN(date) AS earliest_date,
                MAX(date) AS latest_date
            FROM openbb_market_data;
            """,
        ).iloc[0]

        inventory_rows.append({
            "dataset": "OpenBB Market Data",
            "table_name": "openbb_market_data",
            "rows": int(market["rows"]),
            "entities": int(market["entities"]),
            "entity_label": "Symbols",
            "earliest_date": market["earliest_date"],
            "latest_date": market["latest_date"],
        })

        market_sample = query_df(
            engine,
            """
            SELECT
                date,
                symbol,
                asset_name,
                asset_type,
                close,
                daily_return,
                provider
            FROM openbb_market_data
            ORDER BY symbol, date;
            """,
        )

        market_sample.to_csv(
            SNAPSHOT_DIR / "openbb_market_data_sample.csv",
            index=False,
        )

    if "stock_quotes" in tables:
        quotes = query_df(
            engine,
            """
            SELECT
                COUNT(*) AS rows,
                COUNT(DISTINCT symbol) AS entities,
                MIN(trade_datetime) AS earliest_date,
                MAX(trade_datetime) AS latest_date
            FROM stock_quotes;
            """,
        ).iloc[0]

        inventory_rows.append({
            "dataset": "China Stock Quotes",
            "table_name": "stock_quotes",
            "rows": int(quotes["rows"]),
            "entities": int(quotes["entities"]),
            "entity_label": "Symbols",
            "earliest_date": quotes["earliest_date"],
            "latest_date": quotes["latest_date"],
        })

    pd.DataFrame(inventory_rows).to_csv(
        SNAPSHOT_DIR / "data_inventory.csv",
        index=False,
    )

    if "data_quality_results" in tables:
        quality = query_df(
            engine,
            """
            SELECT *
            FROM data_quality_results
            ORDER BY id DESC
            LIMIT 10;
            """,
        )

        quality.to_csv(
            SNAPSHOT_DIR / "data_quality_results.csv",
            index=False,
        )


def export_local_files() -> None:
    source = (
        PROJECT_ROOT
        / "data"
        / "processed"
        / "ohlc_inconsistency_investigation.csv"
    )

    target = (
        SNAPSHOT_DIR
        / "ohlc_inconsistency_investigation.csv"
    )

    if source.exists():
        pd.read_csv(source).to_csv(target, index=False)
    else:
        pd.DataFrame().to_csv(target, index=False)


def main() -> None:
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)

    run_summary, steps = parse_latest_log()

    run_summary.to_csv(
        SNAPSHOT_DIR / "pipeline_run_summary.csv",
        index=False,
    )

    steps.to_csv(
        SNAPSHOT_DIR / "pipeline_steps.csv",
        index=False,
    )

    engine = get_engine()

    try:
        export_database_snapshots(engine)
    finally:
        engine.dispose()

    export_local_files()

    print("=" * 70)
    print("DASHBOARD SNAPSHOTS EXPORTED")
    print("=" * 70)

    for path in sorted(SNAPSHOT_DIR.glob("*.csv")):
        print(path.relative_to(PROJECT_ROOT))


if __name__ == "__main__":
    main()
