"""
Quick smoke tests for memory providers.

Run with: pytest app/providers/memory/test_memory.py
"""
from datetime import datetime
from uuid import uuid4

import pytest

from app.providers.memory import (
    MemoryProvider,
    MemoryProviderError,
    SimpleMemory,
    get_memory_provider,
)


@pytest.fixture
def user_id():
    """Generate test user ID."""
    return uuid4()


class TestSimpleMemory:
    """Test simple memory provider."""

    @pytest.mark.asyncio
    async def test_protocol_compliance(self, db, user_id):
        """Simple memory implements MemoryProvider protocol."""
        memory = get_memory_provider(db, user_id)
        assert isinstance(memory, MemoryProvider)

    @pytest.mark.asyncio
    async def test_add_and_retrieve(self, db, user_id):
        """Can add and retrieve messages."""
        memory = get_memory_provider(db, user_id)

        # Add messages
        await memory.add_message("user", "Hello")
        await memory.add_message("assistant", "Hi there!")

        # Retrieve context
        context = await memory.get_context(limit=10)

        assert len(context.recent_messages) == 2
        assert context.recent_messages[0].role == "user"
        assert context.recent_messages[0].content == "Hello"
        assert context.recent_messages[1].role == "assistant"
        assert context.recent_messages[1].content == "Hi there!"

    @pytest.mark.asyncio
    async def test_message_ordering(self, db, user_id):
        """Messages are returned in chronological order."""
        memory = get_memory_provider(db, user_id)

        # Add messages
        await memory.add_message("user", "First")
        await memory.add_message("assistant", "Second")
        await memory.add_message("user", "Third")

        # Get context
        context = await memory.get_context(limit=10)

        assert len(context.recent_messages) == 3
        assert context.recent_messages[0].content == "First"
        assert context.recent_messages[1].content == "Second"
        assert context.recent_messages[2].content == "Third"

    @pytest.mark.asyncio
    async def test_limit(self, db, user_id):
        """Limit parameter works correctly."""
        memory = get_memory_provider(db, user_id)

        # Add 5 messages
        for i in range(5):
            await memory.add_message("user", f"Message {i}")

        # Get only 3
        context = await memory.get_context(limit=3)

        assert len(context.recent_messages) == 3
        # Should get the 3 most recent (2, 3, 4)
        assert context.recent_messages[0].content == "Message 2"

    @pytest.mark.asyncio
    async def test_clear(self, db, user_id):
        """Can clear conversation history."""
        memory = get_memory_provider(db, user_id)

        # Add messages
        await memory.add_message("user", "Test 1")
        await memory.add_message("assistant", "Test 2")

        # Clear
        deleted = await memory.clear()
        assert deleted == 2

        # Verify empty
        context = await memory.get_context(limit=10)
        assert len(context.recent_messages) == 0

    @pytest.mark.asyncio
    async def test_metadata(self, db, user_id):
        """Can store and retrieve metadata."""
        memory = get_memory_provider(db, user_id)

        # Add message with metadata
        await memory.add_message(
            "assistant",
            "Here's your plan",
            metadata={"tool_calls": [{"name": "get_plan", "result": "success"}]}
        )

        # Retrieve
        context = await memory.get_context(limit=1)
        msg = context.recent_messages[0]

        assert msg.metadata is not None
        assert "tool_calls" in msg.metadata

    @pytest.mark.asyncio
    async def test_pagination(self, db, user_id):
        """Can paginate through history."""
        memory = get_memory_provider(db, user_id)

        # Add 10 messages
        for i in range(10):
            await memory.add_message("user", f"Message {i}")

        # Get first page
        page1 = await memory.get_messages(limit=5, offset=0)
        assert len(page1) == 5

        # Get second page
        page2 = await memory.get_messages(limit=5, offset=5)
        assert len(page2) == 5

        # Pages should not overlap
        page1_content = {msg.content for msg in page1}
        page2_content = {msg.content for msg in page2}
        assert not page1_content.intersection(page2_content)

    @pytest.mark.asyncio
    async def test_summarize_basic(self, db, user_id):
        """Summarize returns basic stats for simple memory."""
        memory = get_memory_provider(db, user_id)

        # Add some messages
        await memory.add_message("user", "Hello")
        await memory.add_message("assistant", "Hi")

        # Get summary
        summary = await memory.summarize()

        assert "2" in summary  # Should mention 2 messages
        assert summary != ""

    @pytest.mark.asyncio
    async def test_isolation_between_users(self, db):
        """Users cannot see each other's messages."""
        user1 = uuid4()
        user2 = uuid4()

        memory1 = get_memory_provider(db, user1)
        memory2 = get_memory_provider(db, user2)

        # Add message for user1
        await memory1.add_message("user", "User 1 message")

        # User2 should not see it
        context2 = await memory2.get_context(limit=10)
        assert len(context2.recent_messages) == 0


class TestMemoryFactory:
    """Test memory provider factory."""

    def test_simple_memory_default(self, db, user_id):
        """Simple memory is default."""
        memory = get_memory_provider(db, user_id)
        assert isinstance(memory, SimpleMemory)

    def test_invalid_memory_type(self, db, user_id):
        """Invalid memory type raises error."""
        with pytest.raises(MemoryProviderError):
            get_memory_provider(db, user_id, memory_type="invalid")

    def test_langchain_requires_ai_provider(self, db, user_id):
        """LangChain memory requires ai_provider."""
        with pytest.raises(MemoryProviderError):
            get_memory_provider(
                db, user_id,
                memory_type="langchain_summary",
                ai_provider=None
            )


class TestLangChainMemory:
    """
    Test LangChain memory provider.

    These tests are skipped if langchain is not installed.
    """

    @pytest.mark.skipif(
        not __import__('importlib.util').util.find_spec('langchain'),
        reason="LangChain not installed"
    )
    @pytest.mark.asyncio
    async def test_langchain_buffer(self, db, user_id, ai_provider):
        """LangChain buffer memory works."""
        memory = get_memory_provider(
            db, user_id,
            memory_type="langchain_buffer",
            ai_provider=ai_provider
        )

        await memory.add_message("user", "Test")
        context = await memory.get_context(limit=10)

        assert len(context.recent_messages) == 1
        assert context.metadata["memory_type"] == "buffer"

    @pytest.mark.skipif(
        not __import__('importlib.util').util.find_spec('langchain'),
        reason="LangChain not installed"
    )
    @pytest.mark.asyncio
    async def test_langchain_window(self, db, user_id, ai_provider):
        """Window memory limits message count."""
        memory = get_memory_provider(
            db, user_id,
            memory_type="langchain_window",
            ai_provider=ai_provider,
            window_size=3
        )

        # Add 5 messages
        for i in range(5):
            await memory.add_message("user", f"Message {i}")

        # Should only keep last 3
        context = await memory.get_context()
        assert len(context.recent_messages) <= 3


# Fixtures for testing

@pytest.fixture
async def db():
    """Mock database session for testing."""
    from unittest.mock import AsyncMock
    return AsyncMock()


@pytest.fixture
def ai_provider():
    """Mock AI provider for testing."""
    from unittest.mock import AsyncMock, MagicMock

    provider = MagicMock()
    provider.chat = AsyncMock(return_value="Summary of conversation...")
    return provider
