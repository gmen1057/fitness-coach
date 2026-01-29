# Memory Provider System

Memory abstraction for conversation history with support for multiple strategies.

## Overview

The memory provider system offers a flexible interface for storing and retrieving conversation history:

- **Simple Memory** (default): Basic database storage, always available
- **LangChain Memory** (optional): AI-powered summarization and advanced strategies
- **Knowledge Graph Memory** (future): Entity relationships and user patterns

## Architecture

```
app/providers/memory/
├── protocols.py      # MemoryProvider protocol + data classes
├── simple.py         # SimpleMemory (database storage)
├── langchain.py      # LangChainMemory (AI summarization)
├── factory.py        # get_memory_provider() factory
└── __init__.py       # Public exports
```

## Quick Start

### Simple Memory (Default)

```python
from app.providers.memory import get_memory_provider

# Create memory provider
memory = get_memory_provider(db, user_id)

# Add messages
await memory.add_message("user", "Show me my workout plan")
await memory.add_message("assistant", "Here's your plan...")

# Get context for AI agent
context = await memory.get_context(limit=10)
print(context.recent_messages)  # List[MemoryMessage]

# Get raw history with pagination
messages = await memory.get_messages(limit=50, offset=0)

# Clear history
deleted = await memory.clear()
```

### LangChain Memory (Optional)

Requires: `pip install fitness-coach[langchain]`

```python
from app.providers import get_ai_provider
from app.providers.memory import get_memory_provider

ai = get_ai_provider()

# Buffer memory (keep last N messages)
memory = get_memory_provider(
    db, user_id,
    memory_type="langchain_buffer",
    ai_provider=ai
)

# Summary memory (AI-powered summarization)
memory = get_memory_provider(
    db, user_id,
    memory_type="langchain_summary",
    ai_provider=ai
)

# Get context with AI summary
context = await memory.get_context(limit=10, include_summary=True)
print(context.summary)  # AI-generated summary
print(context.recent_messages)

# Summarize entire conversation
full_summary = await memory.summarize()
```

### Window Memory

Keep only the last N messages (sliding window):

```python
memory = get_memory_provider(
    db, user_id,
    memory_type="langchain_window",
    ai_provider=ai,
    window_size=20  # Keep last 20 messages
)
```

## Memory Types

| Type | Description | Requires LangChain | AI Summarization |
|------|-------------|-------------------|------------------|
| `simple` | Basic DB storage | No | No |
| `langchain_buffer` | Keep all messages | Yes | No |
| `langchain_summary` | AI-powered summary | Yes | Yes |
| `langchain_window` | Sliding window | Yes | No |

## Data Classes

### MemoryMessage

```python
@dataclass
class MemoryMessage:
    role: str              # "user" | "assistant" | "system"
    content: str
    timestamp: datetime
    metadata: dict | None  # Tool calls, etc.
```

### MemoryContext

```python
@dataclass
class MemoryContext:
    recent_messages: list[MemoryMessage]
    summary: str | None           # AI-generated summary (if available)
    entities: list[Entity]        # Knowledge graph entities (future)
    metadata: dict                # Total messages, etc.
```

## Protocol Interface

All memory providers implement `MemoryProvider` protocol:

```python
@runtime_checkable
class MemoryProvider(Protocol):
    async def add_message(
        self,
        role: str,
        content: str,
        metadata: dict | None = None
    ) -> None: ...

    async def get_context(
        self,
        query: str | None = None,
        limit: int = 10,
        include_summary: bool = False
    ) -> MemoryContext: ...

    async def get_messages(
        self,
        limit: int = 50,
        offset: int = 0,
        before: datetime | None = None
    ) -> list[MemoryMessage]: ...

    async def summarize(self) -> str: ...

    async def clear(self) -> int: ...

    async def close(self) -> None: ...
```

## Configuration

### Environment Variables

```bash
# Memory type
FITNESS_MEMORY_TYPE=simple  # simple | langchain_buffer | langchain_summary | langchain_window

# Window size (for langchain_window)
FITNESS_MEMORY_WINDOW_SIZE=20
```

### Settings Integration

Add to `app/config.py`:

```python
class Settings(BaseSettings):
    # Memory configuration
    memory_type: str = "simple"
    memory_window_size: int = 10
```

### Factory from Settings

```python
from app.providers.memory import create_memory_from_settings

# Reads FITNESS_MEMORY_TYPE from environment
memory = await create_memory_from_settings(db, user_id, ai_provider)
```

## Integration Examples

### Chat API Integration

```python
from app.providers.memory import get_memory_provider

@router.post("/chat")
async def chat(
    request: ChatRequest,
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_user_id),
):
    # Get memory provider
    memory = get_memory_provider(db, user_id)

    # Get context for AI
    context = await memory.get_context(limit=10)

    # Convert to AI provider format
    messages = [
        Message(role=msg.role, content=msg.content)
        for msg in context.recent_messages
    ]

    # Add new user message
    messages.append(Message(role="user", content=request.message))

    # Save to memory
    await memory.add_message("user", request.message)

    # Get AI response
    ai = get_ai_provider()
    response = await ai.chat(messages, system="You are a fitness coach")

    # Save assistant response
    await memory.add_message("assistant", response)

    return {"response": response}
```

### With LangChain Summary

```python
from app.providers import get_ai_provider
from app.providers.memory import get_memory_provider

ai = get_ai_provider()
memory = get_memory_provider(
    db, user_id,
    memory_type="langchain_summary",
    ai_provider=ai
)

# Get context with summary
context = await memory.get_context(limit=10, include_summary=True)

# Build system prompt with summary
system_prompt = f"""You are a fitness coach.

## Conversation Summary
{context.summary}

## Current Context
User is asking about their workout plan.
"""

# Use in AI chat
messages = [Message(role=msg.role, content=msg.content)
            for msg in context.recent_messages]
response = await ai.chat(messages, system=system_prompt)
```

## Testing

```python
import pytest
from app.providers.memory import get_memory_provider, MemoryProviderError

@pytest.mark.asyncio
async def test_simple_memory(db, user_id):
    memory = get_memory_provider(db, user_id)

    # Add messages
    await memory.add_message("user", "Hello")
    await memory.add_message("assistant", "Hi there!")

    # Get context
    context = await memory.get_context(limit=10)
    assert len(context.recent_messages) == 2
    assert context.recent_messages[0].role == "user"

    # Clear
    deleted = await memory.clear()
    assert deleted == 2

@pytest.mark.asyncio
async def test_langchain_memory(db, user_id, ai_provider):
    memory = get_memory_provider(
        db, user_id,
        memory_type="langchain_summary",
        ai_provider=ai_provider
    )

    # Add conversation
    await memory.add_message("user", "I want to build muscle")
    await memory.add_message("assistant", "Great goal! Let's start with...")

    # Get summary
    summary = await memory.summarize()
    assert "muscle" in summary.lower()
```

## Future Extensions

### Knowledge Graph Memory

Track entities and relationships:

```python
from app.providers.memory.protocols import KnowledgeGraphMemory

# Future implementation
memory: KnowledgeGraphMemory = get_memory_provider(
    db, user_id,
    memory_type="knowledge_graph"
)

# Add entities
exercise = await memory.add_entity(
    entity_type="exercise",
    name="Bench Press",
    properties={"muscle_groups": ["chest", "triceps"]}
)

# Link entities
await memory.link_entities(
    entity1_id=exercise.id,
    entity2_id=user_goal.id,
    relationship="helps_achieve"
)

# Get related entities
related = await memory.get_related_entities(
    entity_id=exercise.id,
    relationship="helps_achieve"
)
```

### Semantic Search

Query-based context retrieval with embeddings:

```python
# Get context relevant to query
context = await memory.get_context(
    query="show me exercises for chest",
    limit=5
)
# Returns 5 most relevant messages about chest exercises
```

## Performance Considerations

- **Simple Memory**: Fast, minimal overhead, good for most use cases
- **LangChain Summary**: Adds ~1-2s for AI summarization, use sparingly
- **Window Memory**: O(1) memory usage, good for long conversations
- **Database**: Indexed by `user_id`, pagination for large histories

## Best Practices

1. **Start with simple memory** - works for 90% of use cases
2. **Use window memory for long chats** - prevents context overflow
3. **Enable summaries strategically** - useful for dashboard or analytics
4. **Clear old history periodically** - GDPR compliance, performance
5. **Test with real conversations** - ensure summaries are meaningful

## Error Handling

```python
from app.providers.memory import get_memory_provider, MemoryProviderError

try:
    memory = get_memory_provider(
        db, user_id,
        memory_type="langchain_summary",
        ai_provider=None  # Missing!
    )
except MemoryProviderError as e:
    print(f"Configuration error: {e}")

try:
    memory = get_memory_provider(
        db, user_id,
        memory_type="langchain_summary",
        ai_provider=ai
    )
except ImportError as e:
    print("LangChain not installed. Run: pip install fitness-coach[langchain]")
```

## Migration Guide

### From Simple Chat History

**Before:**
```python
# Direct database queries
messages = await db.execute(
    select(ChatMessage)
    .where(ChatMessage.user_id == user_id)
    .order_by(desc(ChatMessage.created_at))
    .limit(10)
)
```

**After:**
```python
# Using memory provider
memory = get_memory_provider(db, user_id)
context = await memory.get_context(limit=10)
messages = context.recent_messages
```

### Adding LangChain

1. Install: `pip install fitness-coach[langchain]`
2. Set env: `FITNESS_MEMORY_TYPE=langchain_summary`
3. Pass AI provider: `ai_provider=get_ai_provider()`
4. Enable summaries: `include_summary=True`

No code changes needed if using factory!

## License

MIT - See project LICENSE file.
