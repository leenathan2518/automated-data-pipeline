"""
db_connection.py

This module creates a connection to PostgreSQL.

Current functions:
- Create SQLAlchemy engine
- Test database connection
"""

from sqlalchemy import create_engine
from sqlalchemy import text

from src.config.config import DB_CONFIG


def get_engine():
    """
    Create and return a SQLAlchemy engine.

    Returns
    -------
    sqlalchemy.Engine
        SQLAlchemy engine object.
    """

    # Build PostgreSQL connection string
    connection_string = (
        f"postgresql+psycopg2://"
        f"{DB_CONFIG['user']}:"
        f"{DB_CONFIG['password']}@"
        f"{DB_CONFIG['host']}:"
        f"{DB_CONFIG['port']}/"
        f"{DB_CONFIG['database']}"
    )

    # Create SQLAlchemy engine
    engine = create_engine(
        connection_string
    )

    return engine


def test_connection():
    """
    Test PostgreSQL connection.

    Prints PostgreSQL version if successful.
    """

    engine = get_engine()

    with engine.connect() as conn:

        result = conn.execute(
            text("SELECT version();")
        )

        print(result.fetchone())


if __name__ == "__main__":
    test_connection()



