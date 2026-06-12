"""
Lightweight monitoring dashboard for the Automated Data Pipeline.

Pages
-----
1. Pipeline Overview
2. Data Quality Monitor
3. Data Inventory

The dashboard reads PostgreSQL tables created by the ETL pipeline and parses
the latest log file for pipeline status and runtime information.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

import pandas as pd
import plotly.express as px
import streamlit as st
from dotenv import load_dotenv
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine


# ---------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[1]
LOG_DIR = PROJECT_ROOT / "logs"

load_dotenv(PROJECT_ROOT / ".env")

st.set_page_config(
    page_title="Automated Data Pipeline Monitor",
    page_icon="📊",
    layout="wide",
)


# ---------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------

@st.cache_resource
def get_engine() -> Engine:
    """Create and cache the PostgreSQL engine."""

    db_host = os.getenv("DB_HOST", "localhost")
    db_port = os.getenv("DB_PORT", "5432")
    db_name = os.getenv("DB_NAME")
    db_user = os.getenv("DB_USER")
    db_password = os.getenv("DB_PASSWORD")

    missing = [
        name
        for name, value in {
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

    connection_url = (
        f"postgresql+psycopg2://"
        f"{db_user}:{db_password}"
        f"@{db_host}:{db_port}/{db_name}"
    )

    return create_engine(
        connection_url,
        pool_pre_ping=True,
    )


@st.cache_data(ttl=60)
def get_table_names() -> list[str]:
    """Return available PostgreSQL table names."""

    engine = get_engine()
    return inspect(engine).get_table_names()


@st.cache_data(ttl=60)
def read_query(query: str, params: dict[str, Any] | None = None) -> pd.DataFrame:
    """Run a SQL query and return a DataFrame."""

    engine = get_engine()

    with engine.connect() as connection:
        return pd.read_sql(
            text(query),
            connection,
            params=params,
        )


def table_exists(table_name: str) -> bool:
    """Check whether a table exists."""

    return table_name in get_table_names()


# ---------------------------------------------------------------------
# Log parsing
# ---------------------------------------------------------------------

@st.cache_data(ttl=30)
def parse_latest_log() -> dict[str, Any]:
    """
    Parse the latest log file.

    Returns inferred pipeline status, runtime, timestamp, and step records.
    """

    result = {
        "status": "UNKNOWN",
        "runtime_seconds": None,
        "latest_timestamp": None,
        "log_file": None,
        "steps": [],
    }

    if not LOG_DIR.exists():
        return result

    log_files = sorted(
        LOG_DIR.glob("*.log"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )

    if not log_files:
        return result

    latest_log = log_files[0]
    result["log_file"] = latest_log.name

    try:
        content = latest_log.read_text(
            encoding="utf-8",
            errors="replace",
        )
    except OSError:
        return result

    timestamp_matches = re.findall(
        r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})",
        content,
    )

    if timestamp_matches:
        result["latest_timestamp"] = timestamp_matches[-1]

    if "PIPELINE COMPLETED SUCCESSFULLY" in content:
        result["status"] = "SUCCESS"
    elif "PIPELINE FAILED" in content:
        result["status"] = "FAILED"
    elif "AUTOMATED DATA PIPELINE STARTED" in content:
        result["status"] = "RUNNING_OR_INCOMPLETE"

    runtime_matches = re.findall(
        r"Total Runtime:\s*([0-9.]+)\s*seconds",
        content,
    )

    if runtime_matches:
        result["runtime_seconds"] = float(runtime_matches[-1])

    step_pattern = re.compile(
        r"\[(\d+)/(\d+)\]\s+(Starting|Completed|Failed):\s+(.+?)(?:\s+\(([0-9.]+)\s+seconds\))?$"
    )

    steps = []

    for line in content.splitlines():
        message = line.split("|")[-1].strip()
        match = step_pattern.search(message)

        if not match:
            continue

        step_number = int(match.group(1))
        total_steps = int(match.group(2))
        event = match.group(3)
        step_name = match.group(4).strip()
        runtime = float(match.group(5)) if match.group(5) else None

        steps.append(
            {
                "step_number": step_number,
                "total_steps": total_steps,
                "event": event,
                "step_name": step_name,
                "runtime_seconds": runtime,
            }
        )

    # Keep the latest event for each step.
    step_map: dict[int, dict[str, Any]] = {}

    for step in steps:
        step_map[step["step_number"]] = step

    result["steps"] = [
        step_map[key]
        for key in sorted(step_map)
    ]

    return result


# ---------------------------------------------------------------------
# Data loaders
# ---------------------------------------------------------------------

@st.cache_data(ttl=60)
def load_latest_quality_results() -> pd.DataFrame:
    """Load the latest batch of quality results."""

    if not table_exists("data_quality_results"):
        return pd.DataFrame()

    columns_df = read_query(
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'data_quality_results'
        ORDER BY ordinal_position;
        """
    )

    columns = set(columns_df["column_name"].tolist())

    time_column = None

    for candidate in ["check_time", "checked_at", "created_at"]:
        if candidate in columns:
            time_column = candidate
            break

    if time_column is None:
        return read_query(
            """
            SELECT *
            FROM data_quality_results
            ORDER BY id DESC
            LIMIT 100;
            """
        )

    return read_query(
        f"""
        SELECT *
        FROM data_quality_results
        WHERE {time_column} = (
            SELECT MAX({time_column})
            FROM data_quality_results
        )
        ORDER BY table_name, check_name;
        """
    )


@st.cache_data(ttl=60)
def load_ohlc_investigation() -> pd.DataFrame:
    """Load the local OHLC investigation file when available."""

    path = (
        PROJECT_ROOT
        / "data"
        / "processed"
        / "ohlc_inconsistency_investigation.csv"
    )

    if not path.exists():
        return pd.DataFrame()

    return pd.read_csv(path)


@st.cache_data(ttl=60)
def load_inventory() -> pd.DataFrame:
    """Build a data-inventory summary from PostgreSQL."""

    records: list[dict[str, Any]] = []

    if table_exists("macro_indicators"):
        macro = read_query(
            """
            SELECT
                COUNT(*) AS rows,
                COUNT(DISTINCT indicator_code) AS series_count,
                MIN(date) AS earliest_date,
                MAX(date) AS latest_date
            FROM macro_indicators;
            """
        ).iloc[0]

        records.append(
            {
                "dataset": "Macro Indicators",
                "table_name": "macro_indicators",
                "rows": int(macro["rows"]),
                "entities": int(macro["series_count"]),
                "entity_label": "Series",
                "earliest_date": macro["earliest_date"],
                "latest_date": macro["latest_date"],
            }
        )

    if table_exists("openbb_market_data"):
        market = read_query(
            """
            SELECT
                COUNT(*) AS rows,
                COUNT(DISTINCT symbol) AS symbol_count,
                MIN(date) AS earliest_date,
                MAX(date) AS latest_date
            FROM openbb_market_data;
            """
        ).iloc[0]

        records.append(
            {
                "dataset": "OpenBB Market Data",
                "table_name": "openbb_market_data",
                "rows": int(market["rows"]),
                "entities": int(market["symbol_count"]),
                "entity_label": "Symbols",
                "earliest_date": market["earliest_date"],
                "latest_date": market["latest_date"],
            }
        )

    if table_exists("stock_quotes"):
        quotes = read_query(
            """
            SELECT
                COUNT(*) AS rows,
                COUNT(DISTINCT symbol) AS symbol_count,
                MIN(trade_datetime) AS earliest_date,
                MAX(trade_datetime) AS latest_date
            FROM stock_quotes;
            """
        ).iloc[0]

        records.append(
            {
                "dataset": "China Stock Quotes",
                "table_name": "stock_quotes",
                "rows": int(quotes["rows"]),
                "entities": int(quotes["symbol_count"]),
                "entity_label": "Symbols",
                "earliest_date": quotes["earliest_date"],
                "latest_date": quotes["latest_date"],
            }
        )

    return pd.DataFrame(records)


@st.cache_data(ttl=60)
def load_market_series(symbol: str) -> pd.DataFrame:
    """Load one OpenBB market time series."""

    return read_query(
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
        WHERE symbol = :symbol
        ORDER BY date;
        """,
        params={"symbol": symbol},
    )


@st.cache_data(ttl=60)
def load_market_symbols() -> pd.DataFrame:
    """Load available OpenBB symbols."""

    if not table_exists("openbb_market_data"):
        return pd.DataFrame()

    return read_query(
        """
        SELECT DISTINCT
            symbol,
            asset_name,
            asset_type,
            provider
        FROM openbb_market_data
        ORDER BY symbol;
        """
    )


# ---------------------------------------------------------------------
# UI helpers
# ---------------------------------------------------------------------

def status_badge(status: str) -> str:
    """Return a simple status label."""

    mapping = {
        "SUCCESS": "✅ SUCCESS",
        "FAILED": "❌ FAILED",
        "RUNNING_OR_INCOMPLETE": "🟡 INCOMPLETE",
        "UNKNOWN": "⚪ UNKNOWN",
    }

    return mapping.get(status, status)


def render_sidebar() -> str:
    """Render sidebar navigation."""

    st.sidebar.title("Pipeline Monitor")

    page = st.sidebar.radio(
        "Navigation",
        [
            "Pipeline Overview",
            "Data Quality Monitor",
            "Data Inventory",
        ],
    )

    if st.sidebar.button("Refresh data"):
        st.cache_data.clear()
        st.rerun()

    st.sidebar.caption(
        "Monitoring interface for the automated ETL pipeline."
    )

    return page


# ---------------------------------------------------------------------
# Pages
# ---------------------------------------------------------------------

def render_overview() -> None:
    """Render pipeline overview page."""

    st.title("Automated Data Pipeline Monitor")
    st.caption(
        "Operational overview of extraction, transformation, validation, "
        "PostgreSQL loading, and pipeline logs."
    )

    log_info = parse_latest_log()
    quality_df = load_latest_quality_results()
    inventory_df = load_inventory()

    warning_count = 0
    fail_count = 0

    if not quality_df.empty and "check_result" in quality_df.columns:
        warning_count = int(
            (quality_df["check_result"] == "WARNING").sum()
        )
        fail_count = int(
            (quality_df["check_result"] == "FAIL").sum()
        )

    latest_market_date = "N/A"
    latest_macro_date = "N/A"
    latest_quote_time = "N/A"

    if not inventory_df.empty:
        for _, row in inventory_df.iterrows():
            if row["table_name"] == "openbb_market_data":
                latest_market_date = str(row["latest_date"])
            elif row["table_name"] == "macro_indicators":
                latest_macro_date = str(row["latest_date"])
            elif row["table_name"] == "stock_quotes":
                latest_quote_time = str(row["latest_date"])

    col1, col2, col3, col4 = st.columns(4)

    col1.metric(
        "Last Run Status",
        status_badge(log_info["status"]),
    )

    col2.metric(
        "Total Runtime",
        (
            f"{log_info['runtime_seconds']:.2f} sec"
            if log_info["runtime_seconds"] is not None
            else "N/A"
        ),
    )

    col3.metric(
        "Quality Warnings",
        warning_count,
    )

    col4.metric(
        "Quality Failures",
        fail_count,
    )

    st.subheader("Latest Data Availability")

    data_col1, data_col2, data_col3 = st.columns(3)

    data_col1.metric(
        "Latest OpenBB Date",
        latest_market_date,
    )

    data_col2.metric(
        "Latest Macro Date",
        latest_macro_date,
    )

    data_col3.metric(
        "Latest China Quote",
        latest_quote_time,
    )

    st.subheader("Pipeline Steps")

    steps_df = pd.DataFrame(log_info["steps"])

    if steps_df.empty:
        st.info(
            "No step-level log records were found in the latest log file."
        )
    else:
        steps_df["status"] = steps_df["event"].map(
            {
                "Completed": "PASS",
                "Failed": "FAIL",
                "Starting": "INCOMPLETE",
            }
        )

        display_columns = [
            "step_number",
            "step_name",
            "status",
            "runtime_seconds",
        ]

        st.dataframe(
            steps_df[display_columns],
            width='stretch',
            hide_index=True,
        )

        completed_steps = int(
            (steps_df["event"] == "Completed").sum()
        )

        total_steps = int(
            steps_df["total_steps"].max()
        )

        st.progress(
            min(completed_steps / total_steps, 1.0),
            text=f"{completed_steps} of {total_steps} steps completed",
        )

    with st.expander("Latest log metadata"):
        st.write(
            {
                "log_file": log_info["log_file"],
                "latest_timestamp": log_info["latest_timestamp"],
                "status": log_info["status"],
                "runtime_seconds": log_info["runtime_seconds"],
            }
        )


def render_quality() -> None:
    """Render data quality page."""

    st.title("Data Quality Monitor")
    st.caption(
        "Latest validation results and investigation details."
    )

    quality_df = load_latest_quality_results()

    if quality_df.empty:
        st.warning(
            "The data_quality_results table is unavailable or contains no data."
        )
        return

    status_order = ["PASS", "WARNING", "FAIL"]

    counts = (
        quality_df["check_result"]
        .value_counts()
        .reindex(status_order, fill_value=0)
    )

    col1, col2, col3 = st.columns(3)

    col1.metric("PASS", int(counts["PASS"]))
    col2.metric("WARNING", int(counts["WARNING"]))
    col3.metric("FAIL", int(counts["FAIL"]))

    st.subheader("Latest Check Results")

    preferred_columns = [
        "table_name",
        "check_name",
        "check_result",
        "failed_rows",
        "details",
        "check_time",
    ]

    visible_columns = [
        column
        for column in preferred_columns
        if column in quality_df.columns
    ]

    st.dataframe(
        quality_df[visible_columns],
        width='stretch',
        hide_index=True,
    )

    chart_df = (
        quality_df["check_result"]
        .value_counts()
        .rename_axis("status")
        .reset_index(name="checks")
    )

    fig = px.bar(
        chart_df,
        x="status",
        y="checks",
        title="Quality Check Status Distribution",
    )

    st.plotly_chart(
        fig,
        width='stretch',
    )

    st.subheader("OHLC Investigation")

    investigation_df = load_ohlc_investigation()

    if investigation_df.empty:
        st.success(
            "No OHLC inconsistency investigation rows are currently present."
        )
    else:
        st.warning(
            f"{len(investigation_df)} upstream OHLC inconsistencies "
            "were retained for review."
        )

        st.dataframe(
            investigation_df,
            width='stretch',
            hide_index=True,
        )


def render_inventory() -> None:
    """Render data inventory page."""

    st.title("Data Inventory")
    st.caption(
        "Current PostgreSQL dataset sizes, coverage, and market-series preview."
    )

    inventory_df = load_inventory()

    if inventory_df.empty:
        st.warning("No supported pipeline tables were found.")
        return

    st.subheader("Database Inventory")

    st.dataframe(
        inventory_df,
        width='stretch',
        hide_index=True,
    )

    fig = px.bar(
        inventory_df,
        x="dataset",
        y="rows",
        text="rows",
        title="Rows by Dataset",
    )

    st.plotly_chart(
        fig,
        width='stretch',
    )

    st.subheader("OpenBB Market Series")

    symbols_df = load_market_symbols()

    if symbols_df.empty:
        st.info("The openbb_market_data table is unavailable.")
        return

    label_map = {
        row["symbol"]: f"{row['symbol']} — {row['asset_name']}"
        for _, row in symbols_df.iterrows()
    }

    selected_symbol = st.selectbox(
        "Select a market series",
        options=symbols_df["symbol"].tolist(),
        format_func=lambda symbol: label_map[symbol],
    )

    series_df = load_market_series(selected_symbol)

    if series_df.empty:
        st.info("No observations were found for the selected symbol.")
        return

    fig = px.line(
        series_df,
        x="date",
        y="close",
        title=label_map[selected_symbol],
    )

    st.plotly_chart(
        fig,
        width='stretch',
    )

    summary_col1, summary_col2, summary_col3 = st.columns(3)

    summary_col1.metric(
        "Observations",
        len(series_df),
    )

    summary_col2.metric(
        "Latest Close",
        f"{series_df['close'].iloc[-1]:,.4f}",
    )

    summary_col3.metric(
        "Provider",
        str(series_df["provider"].iloc[-1]),
    )

    st.dataframe(
        series_df.tail(20),
        width='stretch',
        hide_index=True,
    )


# ---------------------------------------------------------------------
# Application
# ---------------------------------------------------------------------

def main() -> None:
    """Run the Streamlit application."""

    page = render_sidebar()

    try:
        if page == "Pipeline Overview":
            render_overview()
        elif page == "Data Quality Monitor":
            render_quality()
        else:
            render_inventory()

    except Exception as exc:
        st.error("The dashboard could not load the requested data.")
        st.exception(exc)


if __name__ == "__main__":
    main()
