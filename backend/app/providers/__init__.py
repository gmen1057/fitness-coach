"""
Provider abstraction layer for Fitness Coach.

Supports multiple AI, Embedding, RAG, Graph, and Memory providers with a unified interface.

Usage:
    from app.providers import get_ai_provider, get_embedding_provider, get_rag_provider, get_graph_provider

    # Get configured providers
    ai = get_ai_provider()
    embeddings = get_embedding_provider()
    rag = await get_rag_provider()
    graph = await get_graph_provider()

    # Use providers
    async for chunk in ai.chat_stream(messages, tools, system):
        print(chunk.content)

    vector = await embeddings.embed("workout text")
    results = await rag.search(vector, limit=5)

    # Track exercise relationships
    await graph.add_node("exercise", "squat", {"name": "Squat"})
    await graph.add_edge("squat", "quads", "targets", {"primary": True})
    related = await graph.get_related("squat", "alternative_to")

    # Memory providers
    from app.providers.memory import get_memory_provider

    memory = get_memory_provider(db, user_id)
    await memory.add_message("user", "Hello")
    context = await memory.get_context(limit=10)
"""
from .protocols import (
    Message,
    ToolCall,
    CompletionChunk,
    SearchResult,
    AIProvider,
    EmbeddingProvider,
    RAGProvider,
)
from .graph.protocols import (
    GraphNode,
    GraphEdge,
    GraphQueryResult,
    GraphProvider,
)
from .factory import (
    get_ai_provider,
    get_embedding_provider,
    get_rag_provider,
    get_graph_provider,
    cleanup_providers,
    reset_providers,
    ProviderNotAvailableError,
    ProviderConfigError,
)

# Memory providers are imported from their own submodule
# from app.providers.memory import get_memory_provider, MemoryProvider, etc.

__all__ = [
    # Protocols
    "AIProvider",
    "EmbeddingProvider",
    "RAGProvider",
    "GraphProvider",
    # Data classes
    "Message",
    "ToolCall",
    "CompletionChunk",
    "SearchResult",
    "GraphNode",
    "GraphEdge",
    "GraphQueryResult",
    # Factory functions
    "get_ai_provider",
    "get_embedding_provider",
    "get_rag_provider",
    "get_graph_provider",
    "cleanup_providers",
    "reset_providers",
    # Exceptions
    "ProviderNotAvailableError",
    "ProviderConfigError",
    # Note: Memory providers exported from app.providers.memory
    # Note: Graph providers exported from app.providers.graph
]
