"""
main.py

Main entry point for the Automated Data Pipeline.

Pipeline Workflow
-----------------
1. Extract macroeconomic data from FRED
2. Extract financial market data through OpenBB
3. Extract China stock quote data from Sina Finance

4. Transform macroeconomic data
5. Transform OpenBB financial market data
6. Transform China stock quote data

7. Run data quality checks

8. Load macroeconomic data into PostgreSQL
9. Load OpenBB financial market data into PostgreSQL
10. Load China stock quote data into PostgreSQL
11. Load data quality results into PostgreSQL

Author
------
Vinci Lee
"""

from __future__ import annotations

import time
from collections.abc import Callable

# --------------------------------------------------
# Logger
# --------------------------------------------------

from src.utils.logger import get_logger

# --------------------------------------------------
# Extract Layer
# --------------------------------------------------

from src.extract.fred_extract import run_fred_extract_pipeline
from src.extract.openbb_market_extract import (
    extract_all_market_data,
    save_market_data,
)
from src.extract.sina_stock_extract import run_sina_stock_extract_pipeline

# --------------------------------------------------
# Transform Layer
# --------------------------------------------------

from src.transform.macro_transform import run_macro_transform_pipeline
from src.transform.transform_openbb_market import transform_openbb_market_data
from src.transform.china_stock_transform import transform_china_stock_quotes

# --------------------------------------------------
# Data Quality Layer
# --------------------------------------------------

from src.quality.data_checks import run_data_quality_checks

# --------------------------------------------------
# Load Layer
# --------------------------------------------------

from src.load.load_macro_to_postgres import load_macro_data
from src.load.load_openbb_market_to_postgres import (
    load_openbb_market_to_postgres,
)
from src.load.load_china_stock_to_postgres import load_china_stock_data
from src.load.load_quality_to_postgres import load_quality_results


# --------------------------------------------------
# Create Logger
# --------------------------------------------------

logger = get_logger()


PipelineFunction = Callable[[], object]


def run_openbb_market_extract_pipeline() -> None:
    """Extract OpenBB market data and save the raw CSV output."""

    market_df = extract_all_market_data(
        start_date="2025-01-01",
    )

    save_market_data(market_df)


def run_step(
    step_number: int,
    total_steps: int,
    step_name: str,
    step_function: PipelineFunction,
) -> None:
    """Run one pipeline step with timing, logging, and fail-fast handling."""

    logger.info(
        f"[{step_number}/{total_steps}] Starting: {step_name}"
    )

    step_start_time = time.time()

    try:
        step_function()

        step_runtime = round(
            time.time() - step_start_time,
            2,
        )

        logger.info(
            f"[{step_number}/{total_steps}] Completed: {step_name} "
            f"({step_runtime} seconds)"
        )

    except Exception as exc:
        logger.error(
            f"[{step_number}/{total_steps}] Failed: {step_name}"
        )
        logger.error(
            f"Error Message: {exc}",
            exc_info=True,
        )
        raise


def run_pipeline() -> None:
    """Execute the complete automated ETL pipeline."""

    pipeline_steps: list[tuple[str, PipelineFunction]] = [
        (
            "Extract FRED macroeconomic data",
            run_fred_extract_pipeline,
        ),
        (
            "Extract financial market data through OpenBB",
            run_openbb_market_extract_pipeline,
        ),
        (
            "Extract Sina China stock quote data",
            run_sina_stock_extract_pipeline,
        ),
        (
            "Transform macroeconomic data",
            run_macro_transform_pipeline,
        ),
        (
            "Transform OpenBB financial market data",
            transform_openbb_market_data,
        ),
        (
            "Transform China stock quote data",
            transform_china_stock_quotes,
        ),
        (
            "Run data quality checks",
            run_data_quality_checks,
        ),
        (
            "Load macroeconomic data into PostgreSQL",
            load_macro_data,
        ),
        (
            "Load OpenBB financial market data into PostgreSQL",
            load_openbb_market_to_postgres,
        ),
        (
            "Load China stock quote data into PostgreSQL",
            load_china_stock_data,
        ),
        (
            "Load quality results into PostgreSQL",
            load_quality_results,
        ),
    ]

    total_steps = len(pipeline_steps)
    pipeline_start_time = time.time()

    logger.info("=" * 60)
    logger.info("AUTOMATED DATA PIPELINE STARTED")
    logger.info("=" * 60)

    try:
        for step_number, (step_name, step_function) in enumerate(
            pipeline_steps,
            start=1,
        ):
            run_step(
                step_number=step_number,
                total_steps=total_steps,
                step_name=step_name,
                step_function=step_function,
            )

        total_runtime = round(
            time.time() - pipeline_start_time,
            2,
        )

        logger.info("=" * 60)
        logger.info("PIPELINE COMPLETED SUCCESSFULLY")
        logger.info(f"Total Runtime: {total_runtime} seconds")
        logger.info("=" * 60)

    except Exception:
        failed_runtime = round(
            time.time() - pipeline_start_time,
            2,
        )

        logger.error("=" * 60)
        logger.error("PIPELINE FAILED")
        logger.error(
            f"Runtime Before Failure: {failed_runtime} seconds"
        )
        logger.error("=" * 60)
        raise


if __name__ == "__main__":
    run_pipeline()
