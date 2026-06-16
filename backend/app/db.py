"""
Database session management with SQLAlchemy async.

Provides:
- Async engine and session factory
- get_db() dependency for FastAPI routes
- init_db() for table creation
"""
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import get_settings

# Import Base from models (the canonical source)
from app.models import Base

settings = get_settings()

# Create async engine
engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,
)

# Session factory
async_session = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncSession:
    """
    FastAPI dependency for getting database session.

    Usage:
        @router.get("/endpoint")
        async def endpoint(db: AsyncSession = Depends(get_db)):
            ...

    Note: The session auto-commits on successful exit (no exception).
    Endpoints can still call db.commit() explicitly for early commits.
    """
    async with async_session() as session:
        try:
            yield session
            # Auto-commit on successful completion
            # (Harmless if endpoint already committed - just a no-op)
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db():
    """
    Initialize database tables.

    Creates all tables defined in SQLAlchemy models.
    Called during app startup.

    Note: Models must be imported before calling this to register tables.
    """
    # Import models to ensure they're registered with Base.metadata
    from app.models.fitness import (  # noqa: F401
        BloodMarker,
        BodyWeightLog,
        ChatMessage,
        DayExercise,
        DayWarmup,
        ExerciseResult,
        InjuryEpisode,
        PlanDay,
        PlanWeek,
        UserSession,
        WorkoutLog,
        WorkoutPlan,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
