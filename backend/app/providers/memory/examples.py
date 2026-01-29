"""
Example usage patterns for memory providers.

These examples demonstrate common patterns for integrating memory
into your fitness coach application.
"""
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from app.providers import get_ai_provider
from app.providers.memory import get_memory_provider, MemoryContext
from app.providers.protocols import Message


async def example_simple_memory(db: AsyncSession, user_id: UUID):
    """
    Basic memory usage with database storage.

    This is the default pattern - no extra dependencies needed.
    """
    # Create simple memory provider
    memory = get_memory_provider(db, user_id)

    # Add messages as conversation progresses
    await memory.add_message("user", "I want to start working out")
    await memory.add_message(
        "assistant",
        "Great! Let's create a beginner-friendly plan for you."
    )

    # Get context for AI agent
    context = await memory.get_context(limit=10)

    # Convert to AI provider message format
    messages = [
        Message(role=msg.role, content=msg.content)
        for msg in context.recent_messages
    ]

    print(f"Retrieved {len(messages)} messages from memory")
    return messages


async def example_langchain_summary(db: AsyncSession, user_id: UUID):
    """
    LangChain memory with AI-powered summarization.

    Requires: pip install fitness-coach[langchain]
    """
    # Get AI provider for summarization
    ai = get_ai_provider()

    # Create LangChain summary memory
    memory = get_memory_provider(
        db, user_id,
        memory_type="langchain_summary",
        ai_provider=ai
    )

    # Add conversation
    await memory.add_message("user", "What exercises target chest?")
    await memory.add_message(
        "assistant",
        "Great question! For chest, try: bench press, push-ups, dumbbell flyes..."
    )

    # Get context with AI-generated summary
    context = await memory.get_context(limit=10, include_summary=True)

    print(f"Summary: {context.summary}")
    print(f"Messages: {len(context.recent_messages)}")

    return context


async def example_window_memory(db: AsyncSession, user_id: UUID):
    """
    Sliding window memory - keeps only last N messages.

    Useful for long conversations to prevent context overflow.
    """
    ai = get_ai_provider()

    # Keep only last 20 messages
    memory = get_memory_provider(
        db, user_id,
        memory_type="langchain_window",
        ai_provider=ai,
        window_size=20
    )

    # Memory automatically manages window
    await memory.add_message("user", "Show workout plan")
    # ... many more messages ...

    # Always returns max 20 recent messages
    context = await memory.get_context()
    assert len(context.recent_messages) <= 20

    return context


async def example_chat_endpoint_integration(
    db: AsyncSession,
    user_id: UUID,
    user_message: str
):
    """
    Complete chat endpoint integration with memory.

    This shows how to integrate memory into a FastAPI chat endpoint.
    """
    # Initialize providers
    ai = get_ai_provider()
    memory = get_memory_provider(db, user_id)

    # Get conversation context
    context = await memory.get_context(limit=10)

    # Convert to AI provider format and add new message
    messages = [
        Message(role=msg.role, content=msg.content)
        for msg in context.recent_messages
    ]
    messages.append(Message(role="user", content=user_message))

    # Get AI response
    system_prompt = """You are a knowledgeable fitness coach.
    Help users with workout plans, exercise form, and nutrition advice."""

    response = await ai.chat(messages, system=system_prompt)

    # Save both messages to memory
    await memory.add_message("user", user_message)
    await memory.add_message("assistant", response)

    return {
        "response": response,
        "message_count": len(context.recent_messages) + 2
    }


async def example_with_system_prompt_summary(
    db: AsyncSession,
    user_id: UUID,
    user_message: str
):
    """
    Use conversation summary in system prompt for better context.

    This pattern is useful when you want the AI to be aware of
    the full conversation context without sending all messages.
    """
    ai = get_ai_provider()
    memory = get_memory_provider(
        db, user_id,
        memory_type="langchain_summary",
        ai_provider=ai
    )

    # Get context with summary
    context = await memory.get_context(limit=5, include_summary=True)

    # Build enhanced system prompt
    system_prompt = f"""You are a fitness coach assisting this user.

## Conversation History Summary
{context.summary}

## Instructions
Provide personalized advice based on the conversation history.
Reference specific details from previous discussions when relevant.
"""

    # Get recent messages
    messages = [
        Message(role=msg.role, content=msg.content)
        for msg in context.recent_messages
    ]
    messages.append(Message(role="user", content=user_message))

    # Chat with enhanced context
    response = await ai.chat(messages, system=system_prompt)

    # Save messages
    await memory.add_message("user", user_message)
    await memory.add_message("assistant", response)

    return response


async def example_pagination_and_history(db: AsyncSession, user_id: UUID):
    """
    Retrieve full conversation history with pagination.

    Useful for displaying chat history in UI or exporting conversations.
    """
    memory = get_memory_provider(db, user_id)

    # Get first page (most recent 50 messages)
    page1 = await memory.get_messages(limit=50, offset=0)
    print(f"Page 1: {len(page1)} messages")

    # Get second page
    page2 = await memory.get_messages(limit=50, offset=50)
    print(f"Page 2: {len(page2)} messages")

    # Get messages before specific date
    from datetime import datetime, timedelta
    yesterday = datetime.utcnow() - timedelta(days=1)
    old_messages = await memory.get_messages(limit=50, before=yesterday)
    print(f"Messages before yesterday: {len(old_messages)}")

    return page1


async def example_conversation_summarization(db: AsyncSession, user_id: UUID):
    """
    Generate summary of entire conversation.

    Useful for:
    - Dashboard "Recent Topics" widget
    - Session notes
    - Analytics
    """
    ai = get_ai_provider()
    memory = get_memory_provider(
        db, user_id,
        memory_type="langchain_summary",
        ai_provider=ai
    )

    # Generate full conversation summary
    summary = await memory.summarize()

    print(f"Conversation Summary:\n{summary}")

    # Use summary in dashboard
    return {
        "user_id": str(user_id),
        "summary": summary,
        "generated_at": "2024-01-29T10:00:00Z"
    }


async def example_clear_history(db: AsyncSession, user_id: UUID):
    """
    Clear conversation history.

    Use cases:
    - User requests data deletion (GDPR)
    - Start fresh conversation
    - Cleanup old data
    """
    memory = get_memory_provider(db, user_id)

    # Clear all messages
    deleted_count = await memory.clear()

    print(f"Deleted {deleted_count} messages")

    return {"deleted": deleted_count, "status": "success"}


async def example_memory_with_metadata(db: AsyncSession, user_id: UUID):
    """
    Store messages with metadata (tool calls, timestamps, etc.).

    Metadata is preserved for debugging and analytics.
    """
    memory = get_memory_provider(db, user_id)

    # Add message with tool call metadata
    await memory.add_message(
        "assistant",
        "I've retrieved your workout plan.",
        metadata={
            "tool_calls": [
                {
                    "tool": "get_workout_plan",
                    "args": {"user_id": str(user_id)},
                    "result": "success"
                }
            ]
        }
    )

    # Retrieve with metadata
    context = await memory.get_context(limit=1)
    msg = context.recent_messages[0]

    if msg.metadata and "tool_calls" in msg.metadata:
        print(f"Assistant used tools: {msg.metadata['tool_calls']}")

    return context


async def example_from_settings(db: AsyncSession, user_id: UUID):
    """
    Create memory provider from environment configuration.

    Reads FITNESS_MEMORY_TYPE from environment:
    - simple (default)
    - langchain_buffer
    - langchain_summary
    - langchain_window
    """
    from app.providers.memory import create_memory_from_settings

    ai = get_ai_provider()

    # Automatically selects memory type from settings
    memory = await create_memory_from_settings(
        db=db,
        user_id=user_id,
        ai_provider=ai  # Required for langchain types
    )

    # Use memory as normal
    await memory.add_message("user", "Hello")
    context = await memory.get_context()

    return context


# Error handling examples

async def example_error_handling(db: AsyncSession, user_id: UUID):
    """
    Proper error handling for memory providers.
    """
    from app.providers.memory import MemoryProviderError

    try:
        # Missing ai_provider for langchain type
        memory = get_memory_provider(
            db, user_id,
            memory_type="langchain_summary",
            ai_provider=None  # Error!
        )
    except MemoryProviderError as e:
        print(f"Configuration error: {e}")
        # Fallback to simple memory
        memory = get_memory_provider(db, user_id)

    try:
        # LangChain not installed
        memory = get_memory_provider(
            db, user_id,
            memory_type="langchain_summary",
            ai_provider=get_ai_provider()
        )
    except ImportError as e:
        print(f"Missing dependency: {e}")
        print("Install with: pip install fitness-coach[langchain]")
        # Fallback to simple memory
        memory = get_memory_provider(db, user_id)

    return memory
