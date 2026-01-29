"""
Database models for Fitness Coach.

This package contains all SQLAlchemy models for the application.
"""

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base

# Base for all models
Base = declarative_base()


def create_engine_and_session(database_url: str, echo: bool = False):
    """
    Create async engine and session factory.

    Args:
        database_url: PostgreSQL connection string (asyncpg format)
        echo: Enable SQL query logging

    Returns:
        Tuple of (engine, async_session_factory)
    """
    engine = create_async_engine(
        database_url,
        echo=echo,
        pool_size=5,
        max_overflow=10,
        pool_pre_ping=True,
    )

    session_factory = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )

    return engine, session_factory


async def init_db(engine):
    """
    Initialize database (create all tables).

    Args:
        engine: SQLAlchemy async engine
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


__all__ = [
    "Base",
    "create_engine_and_session",
    "init_db",
]
