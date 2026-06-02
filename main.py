"""
main.py

Main entry point for the Automated Data Pipeline.

Pipeline Workflow
-----------------
1. Extract macroeconomic data from FRED
2. Extract financial market data from Yahoo Finance
3. Extract China stock quote data from Sina Finance

4. Transform macroeconomic data
5. Transform financial market data
6. Transform China stock quote data

7. Run data quality checks

8. Load macroeconomic data into PostgreSQL
9. Load financial market data into PostgreSQL
10. Load China stock quote data into PostgreSQL
11. Load data quality results into PostgreSQL

Author
------
Vinci Lee
"""

import time

# --------------------------------------------------
# Logger
# --------------------------------------------------

from src.utils.logger import get_logger

# --------------------------------------------------
# Extract Layer
# --------------------------------------------------

from src.extract.fred_extract import run_fred_extract_pipeline
from src.extract.market_extract import run_market_extract_pipeline
from src.extract.sina_stock_extract import run_sina_stock_extract_pipeline

# --------------------------------------------------
# Transform Layer
# --------------------------------------------------

from src.transform.macro_transform import run_macro_transform_pipeline
from src.transform.market_transform import run_market_transform_pipeline
from src.transform.china_stock_transform import transform_china_stock_quotes

# --------------------------------------------------
# Data Quality Layer
# --------------------------------------------------

from src.quality.data_checks import run_data_quality_checks

# --------------------------------------------------
# Load Layer
# --------------------------------------------------

from src.load.load_macro_to_postgres import load_macro_data
from src.load.load_market_to_postgres import load_market_data
from src.load.load_china_stock_to_postgres import load_china_stock_data
from src.load.load_quality_to_postgres import load_quality_results


# --------------------------------------------------
# Create Logger
# --------------------------------------------------

logger = get_logger()


def run_step(step_number, total_steps, step_name, step_function):
    """
    Run a single pipeline step with logging and error handling.

    Parameters
    ----------
    step_number : int
        Current step number.

    total_steps : int
        Total number of pipeline steps.

    step_name : str
        Descriptive name of the pipeline step.

    step_function : function
        Function to execute for this step.

    Returns
    -------
    None
    """

    logger.info(
        f"[{step_number}/{total_steps}] Starting: {step_name}"
    )

    step_start_time = time.time()

    try:
        # Execute the pipeline step
        step_function()

        step_end_time = time.time()

        step_runtime = round(
            step_end_time - step_start_time,
            2
        )

        logger.info(
            f"[{step_number}/{total_steps}] Completed: {step_name} "
            f"({step_runtime} seconds)"
        )

    except Exception as e:
        # Log the failed step and the full traceback
        logger.error(
            f"[{step_number}/{total_steps}] Failed: {step_name}"
        )

        logger.error(
            f"Error Message: {e}",
            exc_info=True
        )

        # Stop the whole pipeline if one step fails
        raise


def run_pipeline():
    """
    Execute the complete ETL pipeline.

    Returns
    -------
    None
    """

    total_steps = 11

    # Record pipeline start time
    pipeline_start_time = time.time()

    logger.info("=" * 60)
    logger.info("AUTOMATED DATA PIPELINE STARTED")
    logger.info("=" * 60)

    try:
        # Define all pipeline steps in execution order.
        #
        # Extract steps should run first because they generate raw CSV files.
        # Transform steps should run after extraction because they clean raw data.
        # Load steps should run after transformation because PostgreSQL should
        # receive cleaned and standardised data.
        pipeline_steps = [
            (
                1,
                "Extract FRED macroeconomic data",
                run_fred_extract_pipeline
            ),
            (
                2,
                "Extract financial market data",
                run_market_extract_pipeline
            ),
            (
                3,
                "Extract Sina China stock quote data",
                run_sina_stock_extract_pipeline
            ),
            (
                4,
                "Transform macroeconomic data",
                run_macro_transform_pipeline
            ),
            (
                5,
                "Transform financial market data",
                run_market_transform_pipeline
            ),
            (
                6,
                "Transform China stock quote data",
                transform_china_stock_quotes
            ),
            (
                7,
                "Run data quality checks",
                run_data_quality_checks
            ),
            (
                8,
                "Load macroeconomic data into PostgreSQL",
                load_macro_data
            ),
            (
                9,
                "Load financial market data into PostgreSQL",
                load_market_data
            ),
            (
                10,
                "Load China stock quote data into PostgreSQL",
                load_china_stock_data
            ),
            (
                11,
                "Load quality results into PostgreSQL",
                load_quality_results
            )
        ]

        # Execute each pipeline step
        for step_number, step_name, step_function in pipeline_steps:
            run_step(
                step_number=step_number,
                total_steps=total_steps,
                step_name=step_name,
                step_function=step_function
            )

        # Calculate total pipeline runtime
        pipeline_end_time = time.time()

        total_runtime = round(
            pipeline_end_time - pipeline_start_time,
            2
        )

        logger.info("=" * 60)
        logger.info("PIPELINE COMPLETED SUCCESSFULLY")
        logger.info(f"Total Runtime: {total_runtime} seconds")
        logger.info("=" * 60)

    except Exception:
        # Calculate failed pipeline runtime
        pipeline_failed_time = time.time()

        failed_runtime = round(
            pipeline_failed_time - pipeline_start_time,
            2
        )

        logger.error("=" * 60)
        logger.error("PIPELINE FAILED")
        logger.error(f"Runtime Before Failure: {failed_runtime} seconds")
        logger.error("=" * 60)

        raise


if __name__ == "__main__":
    run_pipeline()





