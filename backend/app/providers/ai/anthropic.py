"""
Anthropic Claude AI provider with Extended Thinking support.

Supports:
- Claude Sonnet 4.5, Opus 4.5
- Extended Thinking (budget_tokens)
- Tool/function calling
- Streaming responses
"""
import json
from typing import AsyncIterator

from anthropic import AsyncAnthropic

from ..protocols import AIProvider, Message, CompletionChunk, ToolCall


class AnthropicProvider(AIProvider):
    """
    Anthropic Claude provider with Extended Thinking support.

    Extended Thinking is enabled for Sonnet/Opus models, providing
    transparent reasoning in responses.
    """

    # Models that support extended thinking
    THINKING_MODELS = {"claude-sonnet-4", "claude-opus-4", "claude-sonnet-4.5", "claude-opus-4.5"}

    def __init__(
        self,
        api_key: str,
        model: str = "claude-sonnet-4-20250514",
        thinking_budget: int = 4000,
    ):
        """
        Initialize Anthropic provider.

        Args:
            api_key: Anthropic API key
            model: Model name (default: claude-sonnet-4)
            thinking_budget: Max tokens for extended thinking (default: 4000)
        """
        self._client = AsyncAnthropic(api_key=api_key)
        self._model = model
        self._thinking_budget = thinking_budget

    @property
    def model_name(self) -> str:
        return self._model

    @property
    def supports_tools(self) -> bool:
        return True

    @property
    def supports_thinking(self) -> bool:
        """Check if model supports extended thinking."""
        return any(m in self._model for m in self.THINKING_MODELS)

    async def chat(
        self,
        messages: list[Message],
        tools: list[dict] | None = None,
        system: str | None = None,
    ) -> str:
        """Non-streaming chat completion."""
        kwargs = self._build_request(messages, tools, system)
        response = await self._client.messages.create(**kwargs)

        # Extract text content
        for block in response.content:
            if hasattr(block, "text"):
                return block.text

        return ""

    async def chat_stream(
        self,
        messages: list[Message],
        tools: list[dict] | None = None,
        system: str | None = None,
    ) -> AsyncIterator[CompletionChunk]:
        """
        Streaming chat completion with thinking and tool support.

        Yields chunks of type:
        - "thinking": Extended thinking content
        - "text": Regular response text
        - "tool_use": Tool call started
        """
        kwargs = self._build_request(messages, tools, system)

        current_tool_id = None
        current_tool_name = None
        current_tool_args = ""

        async with self._client.messages.stream(**kwargs) as stream:
            async for event in stream:
                # Content block started
                if event.type == "content_block_start":
                    block = event.content_block

                    if hasattr(block, "type"):
                        if block.type == "thinking":
                            # Extended thinking block started
                            pass  # Content comes in deltas
                        elif block.type == "tool_use":
                            # Tool call started
                            current_tool_id = block.id
                            current_tool_name = block.name
                            current_tool_args = ""
                            yield CompletionChunk(
                                type="tool_use",
                                tool_call=ToolCall(
                                    id=block.id,
                                    name=block.name,
                                    arguments={},
                                )
                            )

                # Content block delta
                elif event.type == "content_block_delta":
                    delta = event.delta

                    if hasattr(delta, "thinking"):
                        # Thinking content
                        yield CompletionChunk(type="thinking", content=delta.thinking)
                    elif hasattr(delta, "text"):
                        # Regular text
                        yield CompletionChunk(type="text", content=delta.text)
                    elif hasattr(delta, "partial_json"):
                        # Tool arguments (accumulate)
                        current_tool_args += delta.partial_json

                # Content block stopped
                elif event.type == "content_block_stop":
                    # If we were accumulating tool args, parse them
                    if current_tool_id and current_tool_args:
                        try:
                            args = json.loads(current_tool_args)
                        except json.JSONDecodeError:
                            args = {}

                        yield CompletionChunk(
                            type="tool_use",
                            tool_call=ToolCall(
                                id=current_tool_id,
                                name=current_tool_name or "",
                                arguments=args,
                            )
                        )
                        current_tool_id = None
                        current_tool_name = None
                        current_tool_args = ""

                # Message complete
                elif event.type == "message_stop":
                    yield CompletionChunk(type="done")

    async def close(self) -> None:
        """Close the client."""
        await self._client.close()

    def _build_request(
        self,
        messages: list[Message],
        tools: list[dict] | None,
        system: str | None,
    ) -> dict:
        """Build Anthropic API request."""
        # Convert messages to Anthropic format
        anthropic_messages = []
        for msg in messages:
            if msg.role != "system":  # System is separate param
                # Handle structured content (tool_use, tool_result)
                if isinstance(msg.content, list):
                    anthropic_messages.append({
                        "role": msg.role,
                        "content": msg.content,
                    })
                else:
                    # Plain text content
                    anthropic_messages.append({
                        "role": msg.role,
                        "content": msg.content,
                    })

        kwargs = {
            "model": self._model,
            "max_tokens": 8000,
            "messages": anthropic_messages,
        }

        if system:
            kwargs["system"] = system

        if tools:
            kwargs["tools"] = self._convert_tools(tools)

        # Enable thinking for capable models
        if self.supports_thinking:
            kwargs["thinking"] = {
                "type": "enabled",
                "budget_tokens": self._thinking_budget,
            }

        return kwargs

    def _convert_tools(self, tools: list[dict]) -> list[dict]:
        """Convert universal tool format to Anthropic format."""
        return [
            {
                "name": t["name"],
                "description": t["description"],
                "input_schema": t["parameters"],
            }
            for t in tools
        ]
