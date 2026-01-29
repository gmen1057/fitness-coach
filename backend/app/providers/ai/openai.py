"""
OpenAI GPT AI provider with function calling support.

Supports:
- GPT-4o, GPT-4 Turbo, o1, o3
- Function calling (tools)
- Streaming responses
"""
import json
from typing import AsyncIterator

from openai import AsyncOpenAI

from ..protocols import AIProvider, Message, CompletionChunk, ToolCall


class OpenAIProvider(AIProvider):
    """
    OpenAI GPT provider with function calling support.

    Note: o1/o3 models have internal reasoning but don't expose it
    through the API like Anthropic's Extended Thinking.
    """

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4o",
    ):
        """
        Initialize OpenAI provider.

        Args:
            api_key: OpenAI API key
            model: Model name (default: gpt-4o)
        """
        self._client = AsyncOpenAI(api_key=api_key)
        self._model = model

    @property
    def model_name(self) -> str:
        return self._model

    @property
    def supports_tools(self) -> bool:
        return True

    @property
    def supports_thinking(self) -> bool:
        # o1/o3 have reasoning but not exposed via API
        return False

    async def chat(
        self,
        messages: list[Message],
        tools: list[dict] | None = None,
        system: str | None = None,
    ) -> str:
        """Non-streaming chat completion."""
        kwargs = self._build_request(messages, tools, system)
        response = await self._client.chat.completions.create(**kwargs)
        return response.choices[0].message.content or ""

    async def chat_stream(
        self,
        messages: list[Message],
        tools: list[dict] | None = None,
        system: str | None = None,
    ) -> AsyncIterator[CompletionChunk]:
        """
        Streaming chat completion with tool support.

        Yields chunks of type:
        - "text": Regular response text
        - "tool_use": Tool call (accumulated)
        """
        kwargs = self._build_request(messages, tools, system)
        kwargs["stream"] = True

        # Track tool calls being built
        tool_calls_buffer: dict[int, dict] = {}

        stream = await self._client.chat.completions.create(**kwargs)

        async for chunk in stream:
            delta = chunk.choices[0].delta

            # Text content
            if delta.content:
                yield CompletionChunk(type="text", content=delta.content)

            # Tool calls (streamed incrementally)
            if delta.tool_calls:
                for tc in delta.tool_calls:
                    idx = tc.index

                    # Initialize buffer for this tool call
                    if idx not in tool_calls_buffer:
                        tool_calls_buffer[idx] = {
                            "id": tc.id or "",
                            "name": "",
                            "arguments": "",
                        }

                    # Accumulate data
                    if tc.id:
                        tool_calls_buffer[idx]["id"] = tc.id
                    if tc.function:
                        if tc.function.name:
                            tool_calls_buffer[idx]["name"] = tc.function.name
                        if tc.function.arguments:
                            tool_calls_buffer[idx]["arguments"] += tc.function.arguments

            # Check for finish reason
            if chunk.choices[0].finish_reason:
                # Emit accumulated tool calls
                for tc_data in tool_calls_buffer.values():
                    try:
                        args = json.loads(tc_data["arguments"]) if tc_data["arguments"] else {}
                    except json.JSONDecodeError:
                        args = {}

                    yield CompletionChunk(
                        type="tool_use",
                        tool_call=ToolCall(
                            id=tc_data["id"],
                            name=tc_data["name"],
                            arguments=args,
                        )
                    )

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
        """Build OpenAI API request."""
        openai_messages = []

        # Add system message first
        if system:
            openai_messages.append({"role": "system", "content": system})

        # Add conversation messages
        for msg in messages:
            # Handle structured content (tool_use, tool_result from Anthropic format)
            if isinstance(msg.content, list):
                for block in msg.content:
                    if block.get("type") == "tool_use":
                        # Convert Anthropic tool_use to OpenAI format
                        openai_messages.append({
                            "role": "assistant",
                            "tool_calls": [{
                                "id": block["id"],
                                "type": "function",
                                "function": {
                                    "name": block["name"],
                                    "arguments": json.dumps(block["input"])
                                }
                            }]
                        })
                    elif block.get("type") == "tool_result":
                        # Convert Anthropic tool_result to OpenAI format
                        openai_messages.append({
                            "role": "tool",
                            "tool_call_id": block["tool_use_id"],
                            "content": block["content"]
                        })
            else:
                openai_messages.append({
                    "role": msg.role,
                    "content": msg.content,
                })

        kwargs = {
            "model": self._model,
            "messages": openai_messages,
        }

        if tools:
            kwargs["tools"] = self._convert_tools(tools)

        return kwargs

    def _convert_tools(self, tools: list[dict]) -> list[dict]:
        """Convert universal tool format to OpenAI function format."""
        return [
            {
                "type": "function",
                "function": {
                    "name": t["name"],
                    "description": t["description"],
                    "parameters": t["parameters"],
                }
            }
            for t in tools
        ]
