import logging
from pathlib import Path


def get_logger(name: str = "automated_data_pipeline"):
    """
    Create and configure a logger.

    Parameters
    ----------
    name : str
        Name of the logger.

    Returns
    -------
    logging.Logger
        Configured logger instance.
    """

    # Create logs directory if it does not exist
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    # Create logger object
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    # Prevent duplicate handlers
    if logger.handlers:
        return logger

    # Define log format
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Save logs to file
    file_handler = logging.FileHandler(
        "logs/pipeline.log",
        encoding="utf-8"
    )
    file_handler.setFormatter(formatter)

    # Display logs in terminal
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    # Add handlers to logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger

