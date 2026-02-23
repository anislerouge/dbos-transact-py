from typing import Optional

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine


def create_readonly_engine(database_url: str) -> Engine:
    """Create a read-only SQLAlchemy engine for direct DB queries."""
    return create_engine(
        database_url,
        pool_size=5,
        max_overflow=10,
        pool_pre_ping=True,
        execution_options={"postgresql_readonly": True},
    )
