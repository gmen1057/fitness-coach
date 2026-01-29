"""
Memory provider protocols for conversation history and context.

Defines interfaces for:
- Simple memory: Basic chat history storage
- Enhanced memory: LangChain-based memory strategies (buffer, summary, etc.)
- Knowledge graph memory: Entity relationships and patterns
"""
from typing import Protocol, runtime_checkable
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class MemoryMessage:
    """Memory message with metadata."""
    role: str  # "user" | "assistant" | "system"
    content: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: dict | None = None


@dataclass
class Entity:
    """Knowledge graph entity (exercise, muscle group, user pattern)."""
    id: str
    type: str  # "exercise" | "muscle_group" | "user_pattern" | "goal"
    name: str
    properties: dict = field(default_factory=dict)
    related_entities: list[str] = field(default_factory=list)


@dataclass
class MemoryContext:
    """Enriched context for AI agent."""
    recent_messages: list[MemoryMessage]
    summary: str | None = None
    entities: list[Entity] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)


@runtime_checkable
class MemoryProvider(Protocol):
    """
    Protocol for memory providers.

    All memory providers must implement these methods for:
    - Adding messages to memory
    - Retrieving context for AI agent
    - Summarizing conversation history
    - Clearing history
    """

    async def add_message(
        self,
        role: str,
        content: str,
        metadata: dict | None = None
    ) -> None:
        """
        Add message to memory.

        Args:
            role: Message role ("user" | "assistant" | "system")
            content: Message content
            metadata: Optional metadata (tool calls, timestamps, etc.)
        """
        ...

    async def get_context(
        self,
        query: str | None = None,
        limit: int = 10,
        include_summary: bool = False
    ) -> MemoryContext:
        """
        Get conversation context for AI agent.

        Args:
            query: Optional query for semantic search (if supported)
            limit: Maximum number of recent messages to include
            include_summary: Whether to include conversation summary

        Returns:
            MemoryContext with messages, optional summary, and metadata
        """
        ...

    async def get_messages(
        self,
        limit: int = 50,
        offset: int = 0,
        before: datetime | None = None
    ) -> list[MemoryMessage]:
        """
        Get raw message history with pagination.

        Args:
            limit: Maximum number of messages to return
            offset: Number of messages to skip
            before: Get messages before this timestamp

        Returns:
            List of messages in reverse chronological order
        """
        ...

    async def summarize(self) -> str:
        """
        Generate summary of conversation history.

        Returns:
            Summary text (empty string if no history)
        """
        ...

    async def clear(self) -> int:
        """
        Clear all memory for this user.

        Returns:
            Number of messages deleted
        """
        ...

    async def close(self) -> None:
        """Cleanup resources (connections, clients)."""
        ...


@runtime_checkable
class KnowledgeGraphMemory(Protocol):
    """
    Extended protocol for knowledge graph capabilities.

    Tracks entities (exercises, muscle groups, goals) and their relationships.
    Useful for understanding user patterns and providing personalized advice.
    """

    async def add_entity(
        self,
        entity_type: str,
        name: str,
        properties: dict | None = None
    ) -> Entity:
        """Add or update entity in knowledge graph."""
        ...

    async def link_entities(
        self,
        entity1_id: str,
        entity2_id: str,
        relationship: str
    ) -> None:
        """Create relationship between entities."""
        ...

    async def get_entities(
        self,
        query: str | None = None,
        entity_type: str | None = None,
        limit: int = 10
    ) -> list[Entity]:
        """
        Get entities from knowledge graph.

        Args:
            query: Optional query for semantic search
            entity_type: Filter by entity type
            limit: Maximum number of entities to return

        Returns:
            List of entities with their properties and relationships
        """
        ...

    async def get_related_entities(
        self,
        entity_id: str,
        relationship: str | None = None,
        limit: int = 10
    ) -> list[Entity]:
        """Get entities related to given entity."""
        ...
