"""
Memory provider abstraction layer.

Supports multiple memory strategies:
- Simple: Basic database storage (default, always available)
- LangChain: AI-powered memory (optional, requires langchain extra)

Usage:
    from app.providers.memory import get_memory_provider, MemoryContext

    # Simple memory (default)
    memory = get_memory_provider(db, user_id)

    # LangChain memory with AI summarization
    memory = get_memory_provider(
        db, user_id,
        memory_type="langchain_summary",
        ai_provider=ai
    )

    # Add messages
    await memory.add_message("user", "Show my workout plan")
    await memory.add_message("assistant", "Here's your plan...")

    # Get context for AI
    context = await memory.get_context(limit=10, include_summary=True)
    print(context.summary)
    print(context.recent_messages)

    # Get raw history
    messages = await memory.get_messages(limit=50)

    # Summarize conversation
    summary = await memory.summarize()

    # Clear history
    deleted_count = await memory.clear()
"""
from .factory import (
    MemoryProviderError,
    create_memory_from_settings,
    get_memory_provider,
)
from .protocols import (
    Entity,
    KnowledgeGraphMemory,
    MemoryContext,
    MemoryMessage,
    MemoryProvider,
)
from .simple import SimpleMemory

# Conditionally import LangChain memory
try:
    from .langchain import LangChainMemory
    __all_with_langchain = ["LangChainMemory"]
except ImportError:
    __all_with_langchain = []


__all__ = [
    # Protocols
    "MemoryProvider",
    "KnowledgeGraphMemory",
    # Data classes
    "MemoryMessage",
    "MemoryContext",
    "Entity",
    # Implementations
    "SimpleMemory",
    # Factory functions
    "get_memory_provider",
    "create_memory_from_settings",
    # Exceptions
    "MemoryProviderError",
] + __all_with_langchain
