"""
Fitness Chat API with SSE Streaming.

AI-powered fitness assistant using Claude (or other providers) with tool use.
Supports streaming responses via Server-Sent Events (SSE).
"""
import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy import delete, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sse_starlette.sse import EventSourceResponse

from app.api.deps import get_user_id
from app.config import get_settings
from app.db import get_db
from app.models.fitness import ChatMessage as ChatMessageModel

settings = get_settings()
limiter = Limiter(key_func=get_remote_address)
router = APIRouter()
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------

class ChatMessageSchema(BaseModel):
    """Single chat message."""
    id: UUID
    role: str  # "user" or "assistant"
    content: str
    created_at: datetime
    tool_calls: list[dict[str, Any]] | None = None

    class Config:
        from_attributes = True


class ChatRequest(BaseModel):
    """Request to send a chat message."""
    message: str = Field(..., min_length=1, max_length=5000)
    conversation_id: UUID | None = Field(None, description="Conversation thread ID")


class ChatHistoryResponse(BaseModel):
    """Chat history response."""
    messages: list[ChatMessageSchema]
    total: int
    has_more: bool


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

async def get_conversation_history(
    db: AsyncSession,
    user_id: UUID,
    limit: int = 10
) -> list[dict[str, Any]]:
    """
    Get recent conversation history for context.

    Returns messages in Claude's message format.

    Args:
        db: Database session
        user_id: User ID
        limit: Maximum number of messages to retrieve

    Returns:
        List of messages in format: [{"role": "user", "content": "..."}]
    """
    query = (
        select(ChatMessageModel)
        .where(ChatMessageModel.user_id == user_id)
        .order_by(desc(ChatMessageModel.created_at))
        .limit(limit)
    )

    result = await db.execute(query)
    messages = result.scalars().all()

    # Reverse to get chronological order
    messages = list(reversed(messages))

    # Convert to Claude message format (skip empty assistant messages)
    conversation = []
    for msg in messages:
        # Skip empty assistant messages (incomplete responses)
        if msg.role == "assistant" and not msg.content:
            continue
        conversation.append({
            "role": msg.role,
            "content": msg.content
        })

    return conversation


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/chat")
@limiter.limit(settings.rate_limit_chat)
async def chat_stream(
    request: Request,
    chat_request: ChatRequest,
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_user_id),
):
    """
    Send a message and receive a streaming AI response.

    Returns Server-Sent Events (SSE) stream with response chunks.

    **Event types:**
    - `text`: Regular text chunk from AI
    - `tool_start`: AI is calling a tool
    - `tool_result`: Tool execution result
    - `thinking`: AI is processing (Extended Thinking in Claude)
    - `done`: Stream complete with usage stats
    - `error`: Error occurred

    **Rate limit:** Configurable via `rate_limit_chat` setting.

    The AI agent can use tools to:
    - Get workout plans and current workout
    - Complete or skip workout days
    - Get workout statistics
    - Create or edit workout plans
    """
    # Import agent here to allow provider selection at runtime
    from app.services.fitness_agent import get_fitness_agent

    # Get recent conversation history for context
    conversation_history = await get_conversation_history(db, user_id, limit=10)

    # Create agent with db and user_id
    agent = get_fitness_agent(db, user_id)

    async def event_generator():
        """Generate SSE events from AI agent."""
        user_message_id = uuid4()
        assistant_message_id = uuid4()
        full_response = ""

        try:
            # Save user message first
            user_msg = ChatMessageModel(
                id=user_message_id,
                user_id=user_id,
                role="user",
                content=chat_request.message,
                created_at=datetime.utcnow()
            )
            db.add(user_msg)

            # Create placeholder assistant message BEFORE streaming
            # This ensures it's saved even if stream is interrupted
            assistant_msg = ChatMessageModel(
                id=assistant_message_id,
                user_id=user_id,
                role="assistant",
                content="",  # Will be updated during/after streaming
                created_at=datetime.utcnow()
            )
            db.add(assistant_msg)
            await db.commit()

            # Stream response from agent
            chat_generator = agent.chat_stream(
                message=chat_request.message,
                conversation_history=conversation_history
            )

            async for sse_event in chat_generator:
                # Parse SSE event to accumulate full response
                if "event: text" in sse_event:
                    try:
                        data_line = [l for l in sse_event.split("\n") if l.startswith("data:")][0]
                        data = json.loads(data_line[6:])
                        if "content" in data:
                            full_response += data["content"]
                    except (json.JSONDecodeError, IndexError):
                        pass

                # Parse SSE string into dict for sse_starlette
                event_dict = {}
                for line in sse_event.strip().split("\n"):
                    if line.startswith("event: "):
                        event_dict["event"] = line[7:]
                    elif line.startswith("data: "):
                        event_dict["data"] = line[6:]
                    elif line.startswith("id: "):
                        event_dict["id"] = line[4:]

                if event_dict:
                    yield event_dict

            # Update assistant message with final content
            if full_response:
                assistant_msg.content = full_response
                await db.commit()
            else:
                # No response generated - remove placeholder
                await db.delete(assistant_msg)
                await db.commit()

        except Exception as e:
            logger.error(f"Chat error: {e}", exc_info=True)
            # Save partial response if we have any
            if full_response:
                try:
                    assistant_msg.content = full_response + "\n\n[Ответ был прерван]"
                    await db.commit()
                except Exception:
                    pass
            yield {
                "event": "error",
                "data": json.dumps({"error": str(e)})
            }

    return EventSourceResponse(
        event_generator(),
        media_type="text/event-stream"
    )


@router.get("/chat/history", response_model=ChatHistoryResponse)
async def get_chat_history(
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_user_id),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    before: datetime | None = Query(None, description="Get messages before this timestamp"),
):
    """
    Get chat history for the user.

    Returns messages in reverse chronological order (newest first).

    Args:
        limit: Maximum number of messages to return (1-200)
        offset: Number of messages to skip
        before: Get messages before this timestamp

    Returns:
        Chat history with pagination info
    """
    # Build query
    query = select(ChatMessageModel).where(ChatMessageModel.user_id == user_id)

    if before:
        query = query.where(ChatMessageModel.created_at < before)

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    count_result = await db.execute(count_query)
    total = count_result.scalar() or 0

    # Apply ordering and pagination
    query = query.order_by(desc(ChatMessageModel.created_at)).offset(offset).limit(limit + 1)

    result = await db.execute(query)
    messages = result.scalars().all()

    # Check if there are more
    has_more = len(messages) > limit
    if has_more:
        messages = messages[:limit]

    return ChatHistoryResponse(
        messages=[
            ChatMessageSchema(
                id=msg.id,
                role=msg.role,
                content=msg.content,
                created_at=msg.created_at,
                tool_calls=msg.tool_calls
            )
            for msg in messages
            # Skip empty assistant messages (incomplete responses)
            if not (msg.role == "assistant" and not msg.content)
        ],
        total=total,
        has_more=has_more
    )


@router.delete("/chat/history")
async def clear_chat_history(
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_user_id),
):
    """
    Clear chat history for the user.

    This permanently deletes all chat messages.

    Returns:
        Number of messages deleted
    """
    stmt = delete(ChatMessageModel).where(ChatMessageModel.user_id == user_id)
    result = await db.execute(stmt)
    await db.commit()

    return {
        "message": "Chat history cleared",
        "deleted": result.rowcount
    }
