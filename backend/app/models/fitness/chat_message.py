"""
Chat and Session models for AI conversation tracking.

Schema:
- ChatMessage: Store chat messages for history
- UserSession: Store Claude Agent SDK session_id for conversation continuity
"""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import JSON, Column, DateTime, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID

from app.models import Base


class ChatMessage(Base):
    """
    Store chat messages for history.

    Tracks user and assistant messages in AI conversations.
    """
    __tablename__ = "chat_messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    role = Column(String(20), nullable=False)  # "user" or "assistant"
    content = Column(Text, nullable=False)
    tool_calls = Column(JSON, nullable=True)  # Store tool calls made by assistant
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<ChatMessage(id={self.id}, role='{self.role}')>"


class UserSession(Base):
    """
    Store Claude Agent SDK session_id for conversation continuity.

    Allows resuming conversations even after server restart.
    One session per user (module).
    """
    __tablename__ = "user_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    module = Column(String(50), nullable=False, default="fitness")  # "fitness", etc.
    session_id = Column(Text, nullable=False)  # Claude Code session ID (long string)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    # Unique constraint: one session per user per module
    __table_args__ = (
        UniqueConstraint('user_id', 'module', name='uq_user_session_module'),
    )

    def __repr__(self) -> str:
        return f"<UserSession(id={self.id}, user_id={self.user_id}, module='{self.module}')>"
