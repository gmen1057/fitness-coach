# Memory Provider Integration Guide

Guide for integrating the new memory provider system into the Fitness Coach application.

## Overview

The memory provider system has been added to `/app/providers/memory/` with three main components:

1. **SimpleMemory** - Default, database-backed memory (always available)
2. **LangChainMemory** - AI-powered summarization (optional dependency)
3. **Factory** - `get_memory_provider()` for easy instantiation

## Quick Start

### 1. Update chat.py to use memory providers

**Before:**
```python
# Old pattern - direct database queries
async def get_conversation_history(db, user_id, limit):
    query = select(ChatMessageModel).where(...)
    result = await db.execute(query)
    messages = result.scalars().all()
    return [{"role": msg.role, "content": msg.content} for msg in messages]
```

**After:**
```python
from app.providers.memory import get_memory_provider

async def get_conversation_history(db, user_id, limit):
    memory = get_memory_provider(db, user_id)
    context = await memory.get_context(limit=limit)
    return [{"role": msg.role, "content": msg.content}
            for msg in context.recent_messages]
```

### 2. Update chat endpoint

**File:** `app/api/fitness/chat.py`

```python
from app.providers.memory import get_memory_provider

@router.post("/chat")
async def chat_stream(
    request: Request,
    chat_request: ChatRequest,
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_user_id),
):
    # Get memory provider
    memory = get_memory_provider(db, user_id)

    # Get context
    context = await memory.get_context(limit=10)
    conversation_history = [
        {"role": msg.role, "content": msg.content}
        for msg in context.recent_messages
    ]

    # ... rest of endpoint logic ...

    # Save messages
    await memory.add_message("user", chat_request.message)
    # After getting response:
    await memory.add_message("assistant", full_response)
```

### 3. Add configuration settings

**File:** `app/config.py`

```python
class Settings(BaseSettings):
    # ... existing settings ...

    # Memory configuration
    memory_type: str = Field(
        default="simple",
        env="FITNESS_MEMORY_TYPE",
        description="Memory provider type: simple, langchain_buffer, langchain_summary, langchain_window"
    )
    memory_window_size: int = Field(
        default=10,
        env="FITNESS_MEMORY_WINDOW_SIZE",
        description="Window size for langchain_window memory"
    )
```

### 4. Optional: Use settings-based factory

```python
from app.providers.memory import create_memory_from_settings

memory = await create_memory_from_settings(
    db=db,
    user_id=user_id,
    ai_provider=get_ai_provider()  # Only needed for langchain types
)
```

## Environment Variables

Add to `.env`:

```bash
# Memory provider type
FITNESS_MEMORY_TYPE=simple  # or langchain_buffer, langchain_summary, langchain_window

# Window size (for langchain_window)
FITNESS_MEMORY_WINDOW_SIZE=20
```

## Installation

### Simple memory (default)
```bash
# No extra dependencies needed
pip install -e .
```

### LangChain memory
```bash
pip install -e .[langchain]
```

### All features
```bash
pip install -e .[all]
```

## Migration Steps

### Step 1: Update imports
```python
# Replace direct ChatMessage imports with memory providers
from app.providers.memory import get_memory_provider, MemoryContext
```

### Step 2: Replace direct queries
```python
# Before
messages = await db.execute(
    select(ChatMessage)
    .where(ChatMessage.user_id == user_id)
    .order_by(desc(ChatMessage.created_at))
    .limit(10)
)

# After
memory = get_memory_provider(db, user_id)
context = await memory.get_context(limit=10)
messages = context.recent_messages
```

### Step 3: Update message saving
```python
# Before
msg = ChatMessageModel(user_id=user_id, role="user", content="...")
db.add(msg)
await db.commit()

# After
await memory.add_message("user", "...")
# (commits automatically)
```

### Step 4: Test
```bash
pytest app/providers/memory/test_memory.py
```

## Usage Patterns

### Basic Chat

```python
from app.providers.memory import get_memory_provider
from app.providers import get_ai_provider, Message

async def handle_chat(db, user_id, user_message):
    # Get providers
    memory = get_memory_provider(db, user_id)
    ai = get_ai_provider()

    # Get context
    context = await memory.get_context(limit=10)
    messages = [Message(role=msg.role, content=msg.content)
                for msg in context.recent_messages]
    messages.append(Message(role="user", content=user_message))

    # Get AI response
    response = await ai.chat(messages, system="You are a fitness coach")

    # Save messages
    await memory.add_message("user", user_message)
    await memory.add_message("assistant", response)

    return response
```

### Chat with Summary

```python
async def handle_chat_with_summary(db, user_id, user_message):
    ai = get_ai_provider()

    # Use LangChain summary memory
    memory = get_memory_provider(
        db, user_id,
        memory_type="langchain_summary",
        ai_provider=ai
    )

    # Get context with summary
    context = await memory.get_context(limit=5, include_summary=True)

    # Enhanced system prompt
    system_prompt = f"""You are a fitness coach.

## Conversation Summary
{context.summary}

Provide personalized advice based on the conversation history."""

    # ... rest of chat logic ...
```

### Clear History Endpoint

```python
@router.delete("/chat/history")
async def clear_history(
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_user_id),
):
    memory = get_memory_provider(db, user_id)
    deleted = await memory.clear()
    return {"deleted": deleted}
```

## Testing

### Unit Tests

```python
import pytest
from app.providers.memory import get_memory_provider

@pytest.mark.asyncio
async def test_memory_basic(db, user_id):
    memory = get_memory_provider(db, user_id)

    await memory.add_message("user", "Hello")
    await memory.add_message("assistant", "Hi there")

    context = await memory.get_context(limit=10)
    assert len(context.recent_messages) == 2
```

### Integration Tests

```python
@pytest.mark.asyncio
async def test_chat_with_memory(client, db):
    # Send chat message
    response = await client.post(
        "/api/fitness/chat",
        json={"message": "Show my workout plan"}
    )

    # Verify message saved
    memory = get_memory_provider(db, test_user_id)
    context = await memory.get_context(limit=1)
    assert len(context.recent_messages) > 0
```

## Performance Considerations

### Simple Memory
- **Query time**: ~10ms for 10 messages
- **Best for**: Most use cases, production-ready
- **Pros**: Fast, reliable, no extra dependencies

### LangChain Summary Memory
- **Query time**: ~1-2s for summarization
- **Best for**: Long conversations, dashboard analytics
- **Pros**: AI-powered insights, better context compression
- **Cons**: Slower, requires AI provider

### LangChain Window Memory
- **Query time**: ~10ms
- **Best for**: Very long conversations (100+ messages)
- **Pros**: Constant memory usage, prevents context overflow
- **Cons**: Loses old messages

## Troubleshooting

### LangChain not installed

**Error:**
```
ImportError: LangChain not installed. Run: pip install fitness-coach[langchain]
```

**Solution:**
```bash
pip install fitness-coach[langchain]
# or
pip install langchain>=0.3.0 langchain-core>=0.3.0
```

### Missing AI provider for LangChain

**Error:**
```
MemoryProviderError: ai_provider required for LangChain memory types
```

**Solution:**
```python
from app.providers import get_ai_provider

memory = get_memory_provider(
    db, user_id,
    memory_type="langchain_summary",
    ai_provider=get_ai_provider()  # Add this!
)
```

### Slow performance with summaries

**Issue:** Summarization takes 1-2 seconds per request.

**Solution:**
- Only enable summaries when needed (not on every message)
- Cache summaries in database
- Use summary only for dashboard/analytics
- Consider using simple memory for real-time chat

## Next Steps

1. **Update chat.py** - Replace direct DB queries with memory providers
2. **Add settings** - Add memory configuration to `config.py`
3. **Test** - Run tests to ensure migration works
4. **Deploy** - Start with `simple` memory, add LangChain later if needed
5. **Monitor** - Track performance and adjust memory type as needed

## Future Enhancements

### Knowledge Graph Memory (Phase 2)

Track entities and relationships:
```python
# Future implementation
memory = get_memory_provider(
    db, user_id,
    memory_type="knowledge_graph"
)

# Track exercises, muscle groups, goals
await memory.add_entity("exercise", "squat", {"difficulty": "intermediate"})
await memory.link_entities("squat", "quads", "targets")
```

### Semantic Search (Phase 3)

Query-based context retrieval:
```python
# Get context relevant to query
context = await memory.get_context(
    query="chest exercises",
    limit=5
)
# Returns 5 most relevant messages about chest exercises
```

## Resources

- **Documentation**: `app/providers/memory/README.md`
- **Examples**: `app/providers/memory/examples.py`
- **Tests**: `app/providers/memory/test_memory.py`
- **Protocols**: `app/providers/memory/protocols.py`

## Support

For questions or issues:
1. Check `app/providers/memory/README.md`
2. Review `app/providers/memory/examples.py`
3. Run tests: `pytest app/providers/memory/`
4. Open issue on GitHub

---

**Status**: Ready for integration
**Version**: 1.0.0
**Last Updated**: 2026-01-29
