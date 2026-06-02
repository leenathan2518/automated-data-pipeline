"""
config.py

Project configuration.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# FRED

FRED_API_KEY = os.getenv("FRED_API_KEY")

# PostgreSQL

DB_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "port": os.getenv("DB_PORT"),
    "database": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD")
}

