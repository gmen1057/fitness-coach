"""SSE streaming utilities for real-time AI responses"""
import json
from typing import Any, Optional
from dataclasses import dataclass
from enum import Enum


class SSEEventType(str, Enum):
    """Types of SSE events"""
    TEXT = "text"              # Text chunk from AI
    THINKING = "thinking"      # AI is processing (Extended Thinking)
    TOOL_START = "tool_start"  # Tool execution started
    TOOL_RESULT = "tool_result"  # Tool execution completed
    DONE = "done"              # Stream completed
    ERROR = "error"            # Error occurred


@dataclass
class SSEEvent:
    """Represents an SSE event"""
    event_type: SSEEventType
    data: Any
    id: Optional[str] = None

    def format(self) -> str:
        """Format as SSE string"""
        lines = []
        if self.id:
            lines.append(f"id: {self.id}")
        lines.append(f"event: {self.event_type.value}")

        if isinstance(self.data, dict):
            data_str = json.dumps(self.data, ensure_ascii=False)
        else:
            data_str = str(self.data)

        lines.append(f"data: {data_str}")
        lines.append("")  # Empty line to end event
        return "\n".join(lines) + "\n"


class SSEFormatter:
    """Utility class for formatting SSE events"""

    @staticmethod
    def text(content: str, event_id: Optional[str] = None) -> str:
        """Format a text chunk event"""
        return SSEEvent(
            event_type=SSEEventType.TEXT,
            data={"content": content},
            id=event_id
        ).format()

    @staticmethod
    def thinking(content: str = None) -> str:
        """Format a thinking event with optional content from Extended Thinking"""
        if content:
            data = {"content": content}
        else:
            data = {"status": "processing"}
        return SSEEvent(
            event_type=SSEEventType.THINKING,
            data=data
        ).format()

    @staticmethod
    def tool_start(tool_name: str, tool_input: dict[str, Any]) -> str:
        """Format a tool start event"""
        return SSEEvent(
            event_type=SSEEventType.TOOL_START,
            data={
                "tool": tool_name,
                "input": tool_input
            }
        ).format()

    @staticmethod
    def tool_result(tool_name: str, result: Any, success: bool = True) -> str:
        """Format a tool result event"""
        return SSEEvent(
            event_type=SSEEventType.TOOL_RESULT,
            data={
                "tool": tool_name,
                "result": result,
                "success": success
            }
        ).format()

    @staticmethod
    def done(usage: Optional[dict[str, int]] = None) -> str:
        """Format a done event"""
        data = {"status": "complete"}
        if usage:
            data["usage"] = usage
        return SSEEvent(
            event_type=SSEEventType.DONE,
            data=data
        ).format()

    @staticmethod
    def error(message: str, code: Optional[str] = None) -> str:
        """Format an error event"""
        data = {"message": message}
        if code:
            data["code"] = code
        return SSEEvent(
            event_type=SSEEventType.ERROR,
            data=data
        ).format()
