"""
Thread-safe provider factories with lazy imports.

Uses double-check locking pattern for thread safety.
Lazy imports minimize cold start time.
"""
import threading
from typing import TYPE_CHECKING

from .protocols import AIProvider, EmbeddingProvider, RAGProvider
from .graph.protocols import GraphProvider

if TYPE_CHECKING:
    from ..config import Settings


class ProviderNotAvailableError(Exception):
    """Raised when provider dependencies are not installed."""
    pass


class ProviderConfigError(Exception):
    """Raised when provider configuration is invalid."""
    pass


# Thread-safe singletons
_ai_provider: AIProvider | None = None
_ai_provider_lock = threading.Lock()

_embedding_provider: EmbeddingProvider | None = None
_embedding_provider_lock = threading.Lock()

_rag_provider: RAGProvider | None = None
_rag_provider_lock = threading.Lock()
_rag_initialized = False

_graph_provider: GraphProvider | None = None
_graph_provider_lock = threading.Lock()
_graph_initialized = False


def _get_settings() -> "Settings":
    """Get settings with lazy import."""
    from ..config import get_settings
    return get_settings()


def get_ai_provider() -> AIProvider:
    """
    Get AI provider instance (thread-safe singleton).

    Returns cached instance or creates new one based on settings.

    Raises:
        ProviderNotAvailableError: If provider package not installed
        ProviderConfigError: If required API key missing
    """
    global _ai_provider

    if _ai_provider is None:
        with _ai_provider_lock:
            # Double-check locking
            if _ai_provider is None:
                _ai_provider = _create_ai_provider()

    return _ai_provider


def _create_ai_provider() -> AIProvider:
    """Create AI provider based on settings."""
    settings = _get_settings()

    match settings.ai_provider:
        case "anthropic":
            try:
                from .ai.anthropic import AnthropicProvider
            except ImportError:
                raise ProviderNotAvailableError(
                    "Anthropic not installed. Run: pip install fitness-coach[anthropic]"
                )

            if not settings.anthropic_api_key:
                raise ProviderConfigError("FITNESS_ANTHROPIC_API_KEY required")

            return AnthropicProvider(
                api_key=settings.anthropic_api_key.get_secret_value(),
                model=settings.anthropic_model,
            )

        case "openai":
            try:
                from .ai.openai import OpenAIProvider
            except ImportError:
                raise ProviderNotAvailableError(
                    "OpenAI not installed. Run: pip install fitness-coach[openai]"
                )

            if not settings.openai_api_key:
                raise ProviderConfigError("FITNESS_OPENAI_API_KEY required")

            return OpenAIProvider(
                api_key=settings.openai_api_key.get_secret_value(),
                model=settings.openai_model,
            )

        case "ollama":
            from .ai.ollama import OllamaProvider
            return OllamaProvider(
                base_url=settings.ollama_base_url,
                model=settings.ollama_model,
            )

        case _:
            raise ProviderConfigError(f"Unknown AI provider: {settings.ai_provider}")


def get_embedding_provider() -> EmbeddingProvider | None:
    """
    Get embedding provider instance (thread-safe singleton).

    Returns None if embedding_provider="none".
    """
    global _embedding_provider

    settings = _get_settings()
    if settings.embedding_provider == "none":
        return None

    if _embedding_provider is None:
        with _embedding_provider_lock:
            if _embedding_provider is None:
                _embedding_provider = _create_embedding_provider()

    return _embedding_provider


def _create_embedding_provider() -> EmbeddingProvider:
    """Create embedding provider based on settings."""
    settings = _get_settings()

    match settings.embedding_provider:
        case "openai":
            try:
                from .embedding.openai import OpenAIEmbedding
            except ImportError:
                raise ProviderNotAvailableError(
                    "OpenAI not installed. Run: pip install fitness-coach[openai]"
                )

            if not settings.openai_api_key:
                raise ProviderConfigError("FITNESS_OPENAI_API_KEY required for embeddings")

            return OpenAIEmbedding(
                api_key=settings.openai_api_key.get_secret_value(),
                model=settings.openai_embedding_model,
            )

        case "ollama":
            from .embedding.ollama import OllamaEmbeddings
            return OllamaEmbeddings(
                base_url=settings.ollama_base_url,
                model=settings.ollama_embedding_model,
            )

        case _:
            raise ProviderConfigError(f"Unknown embedding provider: {settings.embedding_provider}")


async def get_rag_provider() -> RAGProvider | None:
    """
    Get RAG provider instance (thread-safe, async initialization).

    Returns None if rag_provider="none".
    Must be called from async context due to DB initialization.
    """
    global _rag_provider, _rag_initialized

    settings = _get_settings()
    if settings.rag_provider == "none":
        return None

    if _rag_provider is None or not _rag_initialized:
        with _rag_provider_lock:
            if _rag_provider is None:
                _rag_provider = await _create_rag_provider()
                _rag_initialized = True

    return _rag_provider


async def _create_rag_provider() -> RAGProvider:
    """Create RAG provider based on settings."""
    settings = _get_settings()

    match settings.rag_provider:
        case "pgvector":
            try:
                from .rag.pgvector import PgVectorRAG
            except ImportError:
                raise ProviderNotAvailableError(
                    "pgvector not installed. Run: pip install fitness-coach[pgvector]"
                )

            provider = PgVectorRAG(
                database_url=settings.database_url,
                collection=settings.rag_collection,
                dimensions=settings.embedding_dimensions,
            )
            await provider.initialize()
            return provider

        case "sqlite":
            try:
                from .rag.sqlite_vec import SQLiteVecRAG
            except ImportError:
                raise ProviderNotAvailableError(
                    "sqlite-vec not installed. Run: pip install fitness-coach[sqlite-vec]"
                )

            provider = SQLiteVecRAG(
                db_path=settings.sqlite_vec_path,
                dimensions=settings.embedding_dimensions,
            )
            await provider.initialize()
            return provider

        case _:
            raise ProviderConfigError(f"Unknown RAG provider: {settings.rag_provider}")


async def get_graph_provider() -> GraphProvider | None:
    """
    Get knowledge graph provider instance (thread-safe, async initialization).

    Returns None if graph_provider="none".
    Must be called from async context due to initialization.
    """
    global _graph_provider, _graph_initialized

    settings = _get_settings()
    if settings.graph_provider == "none":
        return None

    if _graph_provider is None or not _graph_initialized:
        with _graph_provider_lock:
            if _graph_provider is None:
                _graph_provider = await _create_graph_provider()
                _graph_initialized = True

    return _graph_provider


async def _create_graph_provider() -> GraphProvider:
    """Create graph provider based on settings."""
    settings = _get_settings()

    match settings.graph_provider:
        case "networkx":
            from .graph import NetworkXGraphProvider

            provider = NetworkXGraphProvider(
                storage_path=settings.graph_storage_path,
            )
            await provider.initialize()
            return provider

        case "neo4j":
            try:
                from .graph import Neo4jGraphProvider
            except ImportError:
                raise ProviderNotAvailableError(
                    "Neo4j not installed. Run: pip install fitness-coach[neo4j]"
                )

            if not settings.neo4j_uri:
                raise ProviderConfigError("FITNESS_NEO4J_URI required for graph provider")

            provider = Neo4jGraphProvider(
                uri=settings.neo4j_uri,
                username=settings.neo4j_username,
                password=settings.neo4j_password.get_secret_value() if settings.neo4j_password else "password",
            )
            await provider.initialize()
            return provider

        case _:
            raise ProviderConfigError(f"Unknown graph provider: {settings.graph_provider}")


async def cleanup_providers() -> None:
    """Cleanup all provider resources. Call on shutdown."""
    global _ai_provider, _embedding_provider, _rag_provider, _rag_initialized, _graph_provider, _graph_initialized

    if _ai_provider is not None:
        await _ai_provider.close()
        _ai_provider = None

    if _embedding_provider is not None:
        await _embedding_provider.close()
        _embedding_provider = None

    if _rag_provider is not None:
        await _rag_provider.close()
        _rag_provider = None
        _rag_initialized = False

    if _graph_provider is not None:
        await _graph_provider.close()
        _graph_provider = None
        _graph_initialized = False


def reset_providers() -> None:
    """Reset all provider singletons. Used for testing."""
    global _ai_provider, _embedding_provider, _rag_provider, _rag_initialized, _graph_provider, _graph_initialized

    _ai_provider = None
    _embedding_provider = None
    _rag_provider = None
    _rag_initialized = False
    _graph_provider = None
    _graph_initialized = False
