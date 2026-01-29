"""
Graph provider protocol for tracking fitness knowledge relationships.

Protocol for knowledge graph implementations that can track:
- Exercise → muscle group relationships
- Exercise progressions and alternatives
- User's workout history and patterns
- Exercise performance trends
"""
from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass
class GraphNode:
    """A node in the knowledge graph."""
    node_type: str  # "exercise" | "muscle_group" | "user" | "workout_session" | "progression"
    node_id: str
    properties: dict  # Arbitrary metadata


@dataclass
class GraphEdge:
    """An edge connecting two nodes."""
    from_id: str
    to_id: str
    relationship: str  # "targets" | "progresses_to" | "alternative_to" | "performed_in" | "completed"
    properties: dict  # e.g., {"weight": 45, "reps": 10, "date": "2026-01-29"}


@dataclass
class GraphQueryResult:
    """Result from a graph query."""
    nodes: list[GraphNode]
    edges: list[GraphEdge]


@runtime_checkable
class GraphProvider(Protocol):
    """
    Protocol for knowledge graph providers.

    Implementations must provide:
    - initialize(): Setup storage
    - add_node(): Add or update node
    - add_edge(): Add or update edge
    - get_node(): Retrieve node by ID
    - query(): Execute graph pattern query
    - get_related(): Find nodes related to a given node
    - delete_node(): Remove node and its edges
    - close(): Cleanup resources
    """

    async def initialize(self) -> None:
        """Initialize graph storage (create indexes, load data)."""
        ...

    async def add_node(
        self,
        node_type: str,
        node_id: str,
        properties: dict | None = None,
    ) -> GraphNode:
        """
        Add or update a node in the graph.

        Args:
            node_type: Type of node (exercise, muscle_group, user, etc.)
            node_id: Unique identifier
            properties: Arbitrary metadata

        Returns:
            Created or updated GraphNode
        """
        ...

    async def add_edge(
        self,
        from_id: str,
        to_id: str,
        relationship: str,
        properties: dict | None = None,
    ) -> GraphEdge:
        """
        Add or update an edge between two nodes.

        Args:
            from_id: Source node ID
            to_id: Target node ID
            relationship: Relationship type
            properties: Edge metadata (weight, date, etc.)

        Returns:
            Created or updated GraphEdge
        """
        ...

    async def get_node(self, node_id: str) -> GraphNode | None:
        """
        Get a node by ID.

        Args:
            node_id: Node identifier

        Returns:
            GraphNode if found, None otherwise
        """
        ...

    async def query(
        self,
        pattern: str,
        params: dict | None = None,
    ) -> GraphQueryResult:
        """
        Execute a graph pattern query.

        For NetworkX: Simple pattern like "exercise->targets->muscle_group"
        For Neo4j: Cypher query

        Args:
            pattern: Query pattern or Cypher query
            params: Query parameters

        Returns:
            GraphQueryResult with matching nodes and edges
        """
        ...

    async def get_related(
        self,
        node_id: str,
        relationship: str | None = None,
        direction: str = "outgoing",  # "outgoing" | "incoming" | "both"
        depth: int = 1,
    ) -> list[GraphNode]:
        """
        Get nodes related to the given node.

        Args:
            node_id: Starting node ID
            relationship: Filter by relationship type (None = all)
            direction: Edge direction to follow
            depth: How many hops to traverse

        Returns:
            List of related GraphNode objects
        """
        ...

    async def delete_node(self, node_id: str) -> None:
        """
        Delete a node and all its edges.

        Args:
            node_id: Node to delete
        """
        ...

    async def close(self) -> None:
        """Cleanup resources (close connections, save state)."""
        ...
