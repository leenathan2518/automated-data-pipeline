"""
automated_data_pipeline_dag.py

Apache Airflow DAG for the Automated Data Pipeline.

This DAG orchestrates the ETL workflow:

1. Extract FRED macroeconomic data
2. Extract financial market data
3. Transform macroeconomic data
4. Transform financial market data
5. Run data quality checks
6. Load macroeconomic data into PostgreSQL
7. Load market data into PostgreSQL
8. Load quality results into PostgreSQL

Author
------
Vinci Lee
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator


# --------------------------------------------------
# Project Path Setup
# --------------------------------------------------

# Get project root directory
PROJECT_ROOT = Path(__file__).resolve().parents[1]

# Add project root to Python path
# This allows Airflow to import modules from src/
sys.path.append(str(PROJECT_ROOT))


# --------------------------------------------------
# Import Pipeline Functions
# --------------------------------------------------

from src.extract.fred_extract import run_fred_extract_pipeline
from src.extract.market_extract import run_market_extract_pipeline

from src.transform.macro_transform import run_macro_transform_pipeline
from src.transform.market_transform import run_market_transform_pipeline

from src.quality.data_checks import run_data_quality_checks

from src.load.load_macro_to_postgres import load_macro_data
from src.load.load_market_to_postgres import load_market_data
from src.load.load_quality_to_postgres import load_quality_results


# --------------------------------------------------
# Default DAG Arguments
# --------------------------------------------------

default_args = {
    "owner": "Vinci Lee",
    "depends_on_past": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}


# --------------------------------------------------
# DAG Definition
# --------------------------------------------------

with DAG(
    dag_id="automated_data_pipeline",
    description="Automated ETL pipeline for macroeconomic and financial market data",
    default_args=default_args,
    start_date=datetime(2026, 6, 2),
    schedule_interval="@daily",
    catchup=False,
    tags=["etl", "data-engineering", "postgresql", "finance"],
) as dag:

    # --------------------------------------------------
    # Extract Tasks
    # --------------------------------------------------

    extract_fred_task = PythonOperator(
        task_id="extract_fred_macro_data",
        python_callable=run_fred_extract_pipeline,
    )

    extract_market_task = PythonOperator(
        task_id="extract_financial_market_data",
        python_callable=run_market_extract_pipeline,
    )

    # --------------------------------------------------
    # Transform Tasks
    # --------------------------------------------------

    transform_macro_task = PythonOperator(
        task_id="transform_macro_data",
        python_callable=run_macro_transform_pipeline,
    )

    transform_market_task = PythonOperator(
        task_id="transform_market_data",
        python_callable=run_market_transform_pipeline,
    )

    # --------------------------------------------------
    # Data Quality Task
    # --------------------------------------------------

    quality_check_task = PythonOperator(
        task_id="run_data_quality_checks",
        python_callable=run_data_quality_checks,
    )

    # --------------------------------------------------
    # Load Tasks
    # --------------------------------------------------

    load_macro_task = PythonOperator(
        task_id="load_macro_data_to_postgres",
        python_callable=load_macro_data,
    )

    load_market_task = PythonOperator(
        task_id="load_market_data_to_postgres",
        python_callable=load_market_data,
    )

    load_quality_task = PythonOperator(
        task_id="load_quality_results_to_postgres",
        python_callable=load_quality_results,
    )

    # --------------------------------------------------
    # Task Dependencies
    # --------------------------------------------------

    extract_fred_task >> extract_market_task

    extract_market_task >> transform_macro_task
    transform_macro_task >> transform_market_task

    transform_market_task >> quality_check_task

    quality_check_task >> load_macro_task
    load_macro_task >> load_market_task
    load_market_task >> load_quality_task

