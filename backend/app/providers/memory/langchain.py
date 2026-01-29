"""
LangChain-based memory provider with AI summarization and semantic search.

Optional dependency - requires `pip install fitness-coach[langchain]`

Features:
- ConversationBufferMemory: Store recent N messages
- ConversationSummaryMemory: AI-powered summarization
- ConversationBufferWindowMemory: Sliding window of messages
- VectorStoreRetrieverMemory: Semantic search over history (with RAG)

Uses LangChain's memory abstractions for flexibility.
"""
from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

try:
    from langchain.memory import (
        ConversationBufferMemory,
        ConversationBufferWindowMemory,
        ConversationSummaryMemory,
    )
    from langchain.schema import AIMessage, BaseMessage, HumanMessage, SystemMessage
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False
    # Type stubs for when langchain is not installed (allows module to be imported)
    BaseMessage = object  # type: ignore[misc,assignment]
    HumanMessage = object  # type: ignore[misc,assignment]
    AIMessage = object  # type: ignore[misc,assignment]
    SystemMessage = object  # type: ignore[misc,assignment]
    ConversationBufferMemory = None  # type: ignore[misc,assignment]
    ConversationBufferWindowMemory = None  # type: ignore[misc,assignment]
    ConversationSummaryMemory = None  # type: ignore[misc,assignment]

from sqlalchemy.ext.asyncio import AsyncSession

from .protocols import MemoryContext, MemoryMessage, MemoryProvider
from .simple import SimpleMemory

if TYPE_CHECKING:
    from app.providers.protocols import AIProvider


class LangChainMemory:
    """
    LangChain-based memory provider.

    Wraps LangChain memory strategies with database persistence.
    Supports multiple memory types:
    - buffer: Keep last N messages
    - summary: AI-powered conversation summary
    - buffer_window: Sliding window of messages

    Args:
        db: Async database session
        user_id: User ID for memory isolation
        ai_provider: AI provider for summarization
        memory_type: Type of memory ("buffer" | "summary" | "buffer_window")
        window_size: Number of messages to keep (for buffer_window)
    """

    def __init__(
        self,
        db: AsyncSession,
        user_id: UUID,
        ai_provider: "AIProvider",
        memory_type: str = "buffer",
        window_size: int = 10
    ):
        if not LANGCHAIN_AVAILABLE:
            raise ImportError(
                "LangChain not installed. Run: pip install fitness-coach[langchain]"
            )

        self.db = db
        self.user_id = user_id
        self.ai_provider = ai_provider
        self.memory_type = memory_type
        self.window_size = window_size

        # Use SimpleMemory for database persistence
        self.simple_memory = SimpleMemory(db, user_id)

        # Initialize LangChain memory
        self._langchain_memory = self._create_langchain_memory()

    def _create_langchain_memory(self):
        """Create LangChain memory instance based on type."""
        if self.memory_type == "buffer":
            return ConversationBufferMemory(
                return_messages=True,
                memory_key="chat_history"
            )
        elif self.memory_type == "summary":
            # Note: ConversationSummaryMemory requires LangChain LLM wrapper
            # We'll implement custom summarization using our AI provider
            return ConversationBufferMemory(
                return_messages=True,
                memory_key="chat_history"
            )
        elif self.memory_type == "buffer_window":
            return ConversationBufferWindowMemory(
                k=self.window_size,
                return_messages=True,
                memory_key="chat_history"
            )
        else:
            raise ValueError(f"Unknown memory type: {self.memory_type}")

    def _to_langchain_message(self, msg: MemoryMessage) -> BaseMessage:
        """Convert MemoryMessage to LangChain message."""
        if msg.role == "user":
            return HumanMessage(content=msg.content)
        elif msg.role == "assistant":
            return AIMessage(content=msg.content)
        elif msg.role == "system":
            return SystemMessage(content=msg.content)
        else:
            return HumanMessage(content=msg.content)

    def _from_langchain_message(self, msg: BaseMessage) -> MemoryMessage:
        """Convert LangChain message to MemoryMessage."""
        if isinstance(msg, HumanMessage):
            role = "user"
        elif isinstance(msg, AIMessage):
            role = "assistant"
        elif isinstance(msg, SystemMessage):
            role = "system"
        else:
            role = "user"

        return MemoryMessage(
            role=role,
            content=msg.content,
            timestamp=datetime.utcnow()
        )

    async def add_message(
        self,
        role: str,
        content: str,
        metadata: dict | None = None
    ) -> None:
        """Add message to both database and LangChain memory."""
        # Save to database
        await self.simple_memory.add_message(role, content, metadata)

        # Add to LangChain memory
        if role == "user":
            self._langchain_memory.chat_memory.add_user_message(content)
        elif role == "assistant":
            self._langchain_memory.chat_memory.add_ai_message(content)

    async def get_context(
        self,
        query: str | None = None,
        limit: int = 10,
        include_summary: bool = False
    ) -> MemoryContext:
        """
        Get conversation context with optional AI summary.

        If include_summary=True and memory_type="summary", generates AI summary.
        Otherwise behaves like simple memory with windowing.
        """
        # Load recent messages from database into LangChain memory
        await self._sync_memory(limit)

        # Get messages from LangChain memory
        lc_messages = self._langchain_memory.chat_memory.messages
        memory_messages = [self._from_langchain_message(msg) for msg in lc_messages]

        # Generate summary if requested
        summary = None
        if include_summary and self.memory_type == "summary":
            summary = await self._generate_summary(memory_messages)

        return MemoryContext(
            recent_messages=memory_messages,
            summary=summary,
            entities=[],
            metadata={
                "memory_type": self.memory_type,
                "total_messages": len(memory_messages)
            }
        )

    async def _sync_memory(self, limit: int) -> None:
        """Sync database messages to LangChain memory."""
        # Clear LangChain memory
        self._langchain_memory.clear()

        # Load recent messages
        db_context = await self.simple_memory.get_context(limit=limit)

        # Add to LangChain memory
        for msg in db_context.recent_messages:
            lc_msg = self._to_langchain_message(msg)
            self._langchain_memory.chat_memory.add_message(lc_msg)

    async def _generate_summary(self, messages: list[MemoryMessage]) -> str:
        """Generate AI summary of conversation."""
        if not messages:
            return ""

        # Build conversation text
        conversation_text = "\n".join([
            f"{msg.role}: {msg.content}" for msg in messages
        ])

        # Use AI provider to summarize
        from app.providers.protocols import Message

        summary_prompt = [
            Message(
                role="user",
                content=f"""Summarize this fitness conversation in 2-3 sentences.
Focus on user's goals, progress, and key topics discussed.

Conversation:
{conversation_text}

Summary:"""
            )
        ]

        summary = await self.ai_provider.chat(
            messages=summary_prompt,
            system="You are a helpful assistant that summarizes conversations concisely."
        )

        return summary.strip()

    async def get_messages(
        self,
        limit: int = 50,
        offset: int = 0,
        before: datetime | None = None
    ) -> list[MemoryMessage]:
        """Delegate to simple memory for raw message retrieval."""
        return await self.simple_memory.get_messages(limit, offset, before)

    async def summarize(self) -> str:
        """Generate AI-powered summary of entire conversation."""
        # Get all recent messages (more than just window)
        messages = await self.simple_memory.get_messages(limit=50)

        if not messages:
            return ""

        # Reverse to chronological order
        messages = list(reversed(messages))

        return await self._generate_summary(messages)

    async def clear(self) -> int:
        """Clear both database and LangChain memory."""
        self._langchain_memory.clear()
        return await self.simple_memory.clear()

    async def close(self) -> None:
        """Cleanup resources."""
        await self.simple_memory.close()
