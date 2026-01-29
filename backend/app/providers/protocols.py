"""
Provider protocols for AI, Embedding, and RAG providers.

Uses typing.Protocol for duck typing flexibility with @runtime_checkable
for isinstance() checks.
"""
from typing import Protocol, AsyncIterator, runtime_checkable
from dataclasses import dataclass, field


@dataclass
class Message:
    """
    Universal message format for all providers.

    Content can be:
    - str: Plain text message
    - list: Structured content blocks (for tool_use, tool_result, etc.)
    """
    role: str  # "user" | "assistant" | "system"
    content: str | list  # str for text, list for structured blocks


@dataclass
class ToolCall:
    """Tool/function call from AI provider."""
    id: str
    name: str
    arguments: dict = field(default_factory=dict)


@dataclass
class CompletionChunk:
    """Streaming chunk from AI provider."""
    type: str  # "text" | "thinking" | "tool_use" | "tool_result" | "done" | "error"
    content: str | None = None
    tool_call: ToolCall | None = None


@runtime_checkable
class AIProvider(Protocol):
    """
    Protocol for AI chat providers.

    Implementations must provide:
    - model_name: Current model identifier
    - supports_tools: Whether function calling is supported
    - supports_thinking: Whether extended thinking/reasoning is exposed
    - chat(): Non-streaming completion
    - chat_stream(): Streaming completion with tool support
    - close(): Cleanup resources
    """

    @property
    def model_name(self) -> str:
        """Return the model identifier."""
        ...

    @property
    def supports_tools(self) -> bool:
        """Return True if provider supports function calling."""
        ...

    @property
    def supports_thinking(self) -> bool:
        """Return True if provider exposes reasoning/thinking blocks."""
        ...

    async def chat(
        self,
        messages: list[Message],
        tools: list[dict] | None = None,
        system: str | None = None,
    ) -> str:
        """Non-streaming chat completion."""
        ...

    async def chat_stream(
        self,
        messages: list[Message],
        tools: list[dict] | None = None,
        system: str | None = None,
    ) -> AsyncIterator[CompletionChunk]:
        """
        Streaming chat completion.

        Yields CompletionChunk with types:
        - "text": Regular text content
        - "thinking": Extended thinking/reasoning (if supported)
        - "tool_use": Tool call started
        - "tool_result": Tool execution result
        - "done": Stream complete
        - "error": Error occurred
        """
        ...

    async def close(self) -> None:
        """Cleanup resources (connections, clients)."""
        ...


@runtime_checkable
class EmbeddingProvider(Protocol):
    """
    Protocol for embedding providers.

    Implementations must provide:
    - dimensions: Vector dimensions for this model
    - embed(): Single text embedding
    - embed_batch(): Batch embedding for efficiency
    - close(): Cleanup resources
    """

    @property
    def dimensions(self) -> int:
        """Return the embedding vector dimensions."""
        ...

    async def embed(self, text: str) -> list[float]:
        """Generate embedding for single text."""
        ...

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for multiple texts (more efficient)."""
        ...

    async def close(self) -> None:
        """Cleanup resources."""
        ...


@dataclass
class SearchResult:
    """Result from RAG vector search."""
    id: str
    content: str
    score: float  # Similarity score (higher = more similar)
    metadata: dict | None = None


@runtime_checkable
class RAGProvider(Protocol):
    """
    Protocol for RAG/vector storage providers.

    Implementations must provide:
    - initialize(): Setup tables/indexes
    - store(): Add or update document
    - search(): Vector similarity search
    - delete(): Remove document
    - close(): Cleanup resources
    """

    async def initialize(self) -> None:
        """Initialize storage (create tables, indexes)."""
        ...

    async def store(
        self,
        id: str,
        content: str,
        embedding: list[float],
        metadata: dict | None = None,
    ) -> None:
        """Store document with embedding."""
        ...

    async def search(
        self,
        query_embedding: list[float],
        limit: int = 5,
        filter: dict | None = None,
    ) -> list[SearchResult]:
        """Search for similar documents."""
        ...

    async def delete(self, id: str) -> None:
        """Delete document by ID."""
        ...

    async def close(self) -> None:
        """Cleanup resources."""
        ...
