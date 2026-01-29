"""
Graph provider for fitness knowledge tracking.

Supports:
- NetworkX: Lightweight in-memory graph with JSON persistence (default)
- Neo4j: Production-grade graph database (optional, requires [neo4j] extra)

Usage:
    from app.providers.graph import get_graph_provider

    # Get configured provider
    graph = await get_graph_provider()

    # Add fitness knowledge
    await graph.add_node("exercise", "squat", {"name": "Squat", "difficulty": 3})
    await graph.add_edge("squat", "quads", "targets", {"primary": True})

    # Query relationships
    results = await graph.query("exercise->targets->muscle_group")

    # Find related exercises
    alternatives = await graph.get_related("squat", "alternative_to")
"""
from .protocols import (
    GraphNode,
    GraphEdge,
    GraphQueryResult,
    GraphProvider,
)
from .networkx_graph import NetworkXGraphProvider

# Try to import Neo4j provider (optional)
try:
    from .neo4j_graph import Neo4jGraphProvider
except ImportError:
    Neo4jGraphProvider = None  # type: ignore


# Singleton instance
_graph_provider: GraphProvider | None = None


async def get_graph_provider(
    provider: str = "networkx",
    **kwargs,
) -> GraphProvider:
    """
    Get or create the configured graph provider.

    Args:
        provider: "networkx" (default) or "neo4j"
        **kwargs: Provider-specific configuration

    Returns:
        Initialized GraphProvider instance

    Raises:
        ValueError: If provider is not supported
        ImportError: If Neo4j provider is requested but not installed

    Examples:
        # Use default NetworkX provider
        graph = await get_graph_provider()

        # Use Neo4j provider
        graph = await get_graph_provider(
            provider="neo4j",
            uri="neo4j://localhost:7687",
            username="neo4j",
            password="password",
        )
    """
    global _graph_provider

    if _graph_provider is not None:
        return _graph_provider

    if provider == "networkx":
        _graph_provider = NetworkXGraphProvider(**kwargs)
    elif provider == "neo4j":
        if Neo4jGraphProvider is None:
            raise ImportError(
                "Neo4j provider requires the neo4j package. "
                "Install with: pip install 'fitness-coach[neo4j]'"
            )
        _graph_provider = Neo4jGraphProvider(**kwargs)
    else:
        raise ValueError(f"Unknown graph provider: {provider}")

    await _graph_provider.initialize()
    return _graph_provider


async def reset_graph_provider() -> None:
    """Reset the singleton provider (useful for testing)."""
    global _graph_provider
    if _graph_provider:
        await _graph_provider.close()
        _graph_provider = None


__all__ = [
    # Protocols
    "GraphProvider",
    # Data classes
    "GraphNode",
    "GraphEdge",
    "GraphQueryResult",
    # Implementations
    "NetworkXGraphProvider",
    "Neo4jGraphProvider",
    # Factory
    "get_graph_provider",
    "reset_graph_provider",
]
