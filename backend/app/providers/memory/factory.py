"""
Memory provider factory.

Creates memory provider instances based on configuration.
Supports simple (default) and langchain (optional) memory providers.
"""
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from .protocols import MemoryProvider
from .simple import SimpleMemory

if TYPE_CHECKING:
    from app.providers.protocols import AIProvider


class MemoryProviderError(Exception):
    """Raised when memory provider configuration is invalid."""
    pass


def get_memory_provider(
    db: AsyncSession,
    user_id: UUID,
    memory_type: str = "simple",
    ai_provider: "AIProvider | None" = None,
    **kwargs
) -> MemoryProvider:
    """
    Get memory provider instance.

    Args:
        db: Async database session
        user_id: User ID for memory isolation
        memory_type: Type of memory provider ("simple" | "langchain_buffer" | "langchain_summary" | "langchain_window")
        ai_provider: AI provider for summarization (required for langchain types)
        **kwargs: Additional provider-specific options

    Returns:
        Memory provider instance

    Raises:
        MemoryProviderError: If configuration is invalid
        ImportError: If LangChain not installed for langchain_* types

    Examples:
        # Simple memory (default)
        memory = get_memory_provider(db, user_id)

        # LangChain buffer memory
        memory = get_memory_provider(
            db, user_id,
            memory_type="langchain_buffer",
            ai_provider=ai
        )

        # LangChain summary memory
        memory = get_memory_provider(
            db, user_id,
            memory_type="langchain_summary",
            ai_provider=ai
        )

        # LangChain window memory
        memory = get_memory_provider(
            db, user_id,
            memory_type="langchain_window",
            ai_provider=ai,
            window_size=20
        )
    """
    if memory_type == "simple":
        return SimpleMemory(db, user_id)

    elif memory_type.startswith("langchain_"):
        if ai_provider is None:
            raise MemoryProviderError(
                "ai_provider required for LangChain memory types"
            )

        try:
            from .langchain import LangChainMemory
        except ImportError:
            raise ImportError(
                "LangChain not installed. Run: pip install fitness-coach[langchain]"
            )

        # Extract LangChain memory type
        lc_type = memory_type.replace("langchain_", "")

        if lc_type not in ["buffer", "summary", "buffer_window"]:
            raise MemoryProviderError(
                f"Unknown LangChain memory type: {lc_type}. "
                f"Valid types: buffer, summary, buffer_window"
            )

        window_size = kwargs.get("window_size", 10)

        return LangChainMemory(
            db=db,
            user_id=user_id,
            ai_provider=ai_provider,
            memory_type=lc_type,
            window_size=window_size
        )

    else:
        raise MemoryProviderError(
            f"Unknown memory type: {memory_type}. "
            f"Valid types: simple, langchain_buffer, langchain_summary, langchain_window"
        )


async def create_memory_from_settings(
    db: AsyncSession,
    user_id: UUID,
    ai_provider: "AIProvider | None" = None
) -> MemoryProvider:
    """
    Create memory provider from application settings.

    Reads FITNESS_MEMORY_TYPE from environment:
    - "simple" (default): Basic database storage
    - "langchain_buffer": LangChain buffer memory
    - "langchain_summary": LangChain summary memory
    - "langchain_window": LangChain sliding window

    Args:
        db: Async database session
        user_id: User ID
        ai_provider: AI provider (required for langchain types)

    Returns:
        Memory provider instance
    """
    from app.config import get_settings

    settings = get_settings()
    memory_type = getattr(settings, "memory_type", "simple")
    window_size = getattr(settings, "memory_window_size", 10)

    return get_memory_provider(
        db=db,
        user_id=user_id,
        memory_type=memory_type,
        ai_provider=ai_provider,
        window_size=window_size
    )
