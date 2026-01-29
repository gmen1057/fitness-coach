"""
Simple memory provider using database storage.

Stores chat history in PostgreSQL with basic retrieval.
No AI-powered summarization or semantic search.
"""
from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import delete, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from .protocols import MemoryContext, MemoryMessage, MemoryProvider

if TYPE_CHECKING:
    from app.models.fitness.chat_message import ChatMessage as ChatMessageModel


class SimpleMemory:
    """
    Simple memory provider with database storage.

    Features:
    - Store messages in PostgreSQL
    - Retrieve recent messages for context
    - Pagination support
    - Clear history

    Does NOT support:
    - AI-powered summarization
    - Semantic search
    - Knowledge graphs
    """

    def __init__(self, db: AsyncSession, user_id: UUID):
        """
        Initialize simple memory.

        Args:
            db: Async database session
            user_id: User ID for memory isolation
        """
        self.db = db
        self.user_id = user_id

    async def add_message(
        self,
        role: str,
        content: str,
        metadata: dict | None = None
    ) -> None:
        """Add message to database."""
        from app.models.fitness.chat_message import ChatMessage as ChatMessageModel

        msg = ChatMessageModel(
            user_id=self.user_id,
            role=role,
            content=content,
            tool_calls=metadata.get("tool_calls") if metadata else None,
            created_at=datetime.utcnow()
        )
        self.db.add(msg)
        await self.db.commit()

    async def get_context(
        self,
        query: str | None = None,
        limit: int = 10,
        include_summary: bool = False
    ) -> MemoryContext:
        """
        Get conversation context from recent messages.

        Note: query parameter is ignored (no semantic search in simple memory)
        Note: include_summary is ignored (no summarization in simple memory)
        """
        from app.models.fitness.chat_message import ChatMessage as ChatMessageModel

        # Get recent messages
        stmt = (
            select(ChatMessageModel)
            .where(ChatMessageModel.user_id == self.user_id)
            .order_by(desc(ChatMessageModel.created_at))
            .limit(limit)
        )

        result = await self.db.execute(stmt)
        messages = result.scalars().all()

        # Reverse to get chronological order
        messages = list(reversed(messages))

        # Convert to MemoryMessage
        memory_messages = [
            MemoryMessage(
                role=msg.role,
                content=msg.content,
                timestamp=msg.created_at,
                metadata={"tool_calls": msg.tool_calls} if msg.tool_calls else None
            )
            for msg in messages
        ]

        return MemoryContext(
            recent_messages=memory_messages,
            summary=None,
            entities=[],
            metadata={"total_messages": len(memory_messages)}
        )

    async def get_messages(
        self,
        limit: int = 50,
        offset: int = 0,
        before: datetime | None = None
    ) -> list[MemoryMessage]:
        """Get raw message history with pagination."""
        from app.models.fitness.chat_message import ChatMessage as ChatMessageModel

        stmt = select(ChatMessageModel).where(ChatMessageModel.user_id == self.user_id)

        if before:
            stmt = stmt.where(ChatMessageModel.created_at < before)

        stmt = stmt.order_by(desc(ChatMessageModel.created_at)).offset(offset).limit(limit)

        result = await self.db.execute(stmt)
        messages = result.scalars().all()

        return [
            MemoryMessage(
                role=msg.role,
                content=msg.content,
                timestamp=msg.created_at,
                metadata={"tool_calls": msg.tool_calls} if msg.tool_calls else None
            )
            for msg in messages
        ]

    async def summarize(self) -> str:
        """
        Simple memory doesn't support AI summarization.

        Returns basic statistics instead.
        """
        from app.models.fitness.chat_message import ChatMessage as ChatMessageModel

        # Count messages
        count_stmt = select(func.count()).select_from(ChatMessageModel).where(
            ChatMessageModel.user_id == self.user_id
        )
        result = await self.db.execute(count_stmt)
        count = result.scalar() or 0

        if count == 0:
            return ""

        # Get first and last message dates
        first_stmt = (
            select(ChatMessageModel.created_at)
            .where(ChatMessageModel.user_id == self.user_id)
            .order_by(ChatMessageModel.created_at)
            .limit(1)
        )
        last_stmt = (
            select(ChatMessageModel.created_at)
            .where(ChatMessageModel.user_id == self.user_id)
            .order_by(desc(ChatMessageModel.created_at))
            .limit(1)
        )

        first_result = await self.db.execute(first_stmt)
        last_result = await self.db.execute(last_stmt)

        first_date = first_result.scalar()
        last_date = last_result.scalar()

        return (
            f"Conversation history: {count} messages from "
            f"{first_date.strftime('%Y-%m-%d')} to {last_date.strftime('%Y-%m-%d')}"
        )

    async def clear(self) -> int:
        """Clear all messages for this user."""
        from app.models.fitness.chat_message import ChatMessage as ChatMessageModel

        stmt = delete(ChatMessageModel).where(ChatMessageModel.user_id == self.user_id)
        result = await self.db.execute(stmt)
        await self.db.commit()

        return result.rowcount

    async def close(self) -> None:
        """No cleanup needed for simple memory."""
        pass
